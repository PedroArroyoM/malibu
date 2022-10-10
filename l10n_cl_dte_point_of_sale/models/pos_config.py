# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = "pos.config"

    @api.depends('secuencia_boleta', 'secuencia_boleta_exenta', 'next_number', 'next_number_exenta')
    def get_left_numbers(self):
        for rec in self:
            if rec.secuencia_boleta and rec.secuencia_boleta.caf_file:
                rec.left_number = rec.secuencia_boleta.caf_file.final_nb - rec.next_number - 1
            else:
                rec.left_number = 0
            if rec.secuencia_boleta_exenta and rec.secuencia_boleta_exenta.caf_file:
                rec.left_number_exenta = rec.secuencia_boleta_exenta.caf_file.final_nb - rec.next_number_exenta - 1
            else:
                rec.left_number_exenta = 0

    secuencia_boleta = fields.Many2one(
            'ir.sequence',
            string='Secuencia Boleta',
        )
    secuencia_boleta_exenta = fields.Many2one(
            'ir.sequence',
            string='Secuencia Boleta Exenta',
        )
    ticket = fields.Boolean(
            string="¿Facturas en Formato Ticket?",
            default=False,
        )
    next_number = fields.Integer(
            related="secuencia_boleta.number_next_actual",
            string="Next Number",
        )
    next_number_exenta = fields.Integer(
            related="secuencia_boleta_exenta.number_next_actual",
            string="Next Number Exenta",
        )
    left_number = fields.Integer(
            compute="get_left_numbers",
            string="Folios restantes Boletas",
        )
    left_number_exenta = fields.Integer(
            compute="get_left_numbers",
            string="Folios restantes Boletas Exentas",
        )
    marcar = fields.Selection(
        [
            ('boleta', 'Boletas'),
            ('factura', 'Facturas'),
            ('boleta_exenta', 'Boletas Exentas'),
        ],
        string="Marcar por defecto",
    )
    restore_mode = fields.Boolean(
        string="Restore Mode",
        default=False,
    )
    opciones_impresion = fields.Selection(
        [
            ('cliente', 'Solo Copia Cliente'),
            ('cedible', 'Solo Cedible'),
            ('cliente_cedible', 'Cliente y Cedible'),
        ],
        string="Opciones de Impresión",
        default="cliente",
    )

    @api.onchange('secuencia_boleta', secuencia_boleta_exenta)
    def _onchange_secuencia_boleta(self):
        if self.secuencia_boleta:
            self.secuencia_boleta.caf_file.usage = 'pos'
        if self.secuencia_boleta_exenta:
            self.secuencia_boleta_exenta.caf_file.usage = 'pos'
    #@api.one
    @api.constrains('marcar', 'secuencia_boleta', 'secuencia_boleta_exenta', 'iface_invoicing')
    def _check_document_type(self):
        if self.marcar == 'boleta' and not self.secuencia_boleta:
            raise ValidationError("Al marcar por defecto Boletas, "
                                  "debe seleccionar la Secuencia de Boletas, "
                                  "por favor verifique su configuracion")
        elif self.marcar == 'boleta_exenta' and not self.secuencia_boleta_exenta:
            raise ValidationError("Al marcar por defecto Boletas Exentas, "
                                  "debe seleccionar la Secuencia de Boletas Exentas, "
                                  "por favor verifique su configuracion")
        elif self.marcar == 'factura' and not self.iface_invoicing:
            raise ValidationError("Al marcar por defecto Facturas, "
                                  "debe activar el check de Facturacion, "
                                  "por favor verifique su configuracion")
