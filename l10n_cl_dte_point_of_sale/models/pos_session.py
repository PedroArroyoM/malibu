# -*- coding: utf-8 -*-
import base64

import xmltodict
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging
import json
from lxml import etree

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    secuencia_boleta = fields.Many2one(
            'ir.sequence',
            string='Documents Type',
        )
    secuencia_boleta_exenta = fields.Many2one(
            'ir.sequence',
            string='Documents Type',
        )
    start_number = fields.Integer(
            string='Folio Inicio',
        )
    start_number_exentas = fields.Integer(
            string='Folio Inicio Exentas',
        )
    numero_ordenes = fields.Integer(
            string="Número de órdenes",
            default=0,
        )
    numero_ordenes_exentas = fields.Integer(
            string="Número de órdenes exentas",
            default=0,
        )
    caf_files = fields.Char(
            invisible=True,
        )
    caf_files_exentas = fields.Char(
            invisible=True,
        )

    @api.model
    def create(self, values):
        pos_config = values.get('config_id') or self.env.context.get('default_config_id')
        config_id = self.env['pos.config'].browse(pos_config)
        if not config_id:
            raise UserError(_("You should assign a Point of Sale to your session."))
        if config_id.restore_mode:
            return super(PosSession, self).create(values)
        if config_id.secuencia_boleta:
            sequence = config_id.secuencia_boleta
            start_number = sequence.number_next_actual + 1
            start_number = start_number if sequence.number_next_actual == start_number else sequence.number_next_actual
            values.update({
                'start_number': start_number,
                'secuencia_boleta': config_id.secuencia_boleta.id,
                'caf_files': self.get_caf_string(sequence),
            })
        if config_id.secuencia_boleta_exenta:
            sequence = config_id.secuencia_boleta_exenta
            start_number = sequence.number_next_actual + 1
            start_number = start_number if sequence.number_next_actual == start_number else sequence.number_next_actual
            values.update({
                'start_number_exentas': start_number,
                'secuencia_boleta_exenta': config_id.secuencia_boleta_exenta.id,
                'caf_files_exentas': self.get_caf_string(sequence),
            })
        return super(PosSession, self).create(values)

    @api.model
    def get_caf_string(self,sequence=None):
        if not sequence:
            sequence = self.journal_document_class_id.sequence_id
            if not sequence:
                return
        #if not self.env.user.company_id._get_digital_signature(self.env.user):
        #    raise UserError(_("No Tiene permisos para usar esta secuencia de folios"))
        folio = sequence.number_next_actual
        caffile = sequence.get_caf_file()
        if not caffile:
            return
        #post = base64.b64decode(caffile).decode('ISO-8859-1')
        #return etree.fromstring(post.encode('utf-8'))
        post = etree.tostring(caffile,encoding='utf8', method='xml')
        post = xmltodict.parse(post.replace(
            b'<?xml version="1.0"?>',b'',1))
        #folio_inicial = post['AUTORIZACION']['CAF']['DA']['RNG']['D']
        #folio_final = post['AUTORIZACION']['CAF']['DA']['RNG']['H']
        result = caffile.xpath('//AUTORIZACION/CAF/DA')[0]
        folio_inicial = int(result.xpath('RNG/D')[0].text)
        folio_final = int(result.xpath('RNG/H')[0].text)


        if folio in range(int(folio_inicial),(int(folio_final) + 1)):
            post = json.dumps([post],ensure_ascii=False)
            return post.replace("'","")

        if folio > int(folio_final):
            msg = '''El folio de este documento: {} está fuera de rango \
    del CAF vigente (desde {} hasta {}). Solicite un nuevo CAF en el sitio \
    www.sii.cl'''.format(folio,folio_inicial,folio_final)
            caffile.status = 'spent'
            raise UserError(_(msg))

    def action_pos_session_closing_control(self):
        super(PosSession, self).action_pos_session_closing_control()
        # Actualizo los folios del punto de venta.
        # Boletas
        if self.numero_ordenes:
            self.sudo().config_id.secuencia_boleta.number_next_actual += 1
        # Boletas exentas
        if self.numero_ordenes_exentas:
            self.sudo().config_id.secuencia_boleta_exenta.number_next_actual += 1
