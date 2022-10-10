from odoo import fields, models, api
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_origin_sale(self):
        if self.payment_reference:
            pos = self.env['pos.order'].search([('name', '=', self.payment_reference)])
            if pos:
                return True
        else:
            return False

    def _compute_name(self):
        for rec in self:
            if rec.l10n_latam_document_type_id.code == '39':
                if not rec.name or rec.name and rec.state == 'draft' and not rec.posted_before:
                    rec.name = '/'
                else:
                    if not rec.get_origin_sale() and rec.name == '/':

                        """caf_ids = rec.env['ir.sequence'].search([
                            ('l10n_latam_document_type_id', '=', rec.l10n_latam_document_type_id.id),
                            ('company_id', '=', rec.env.company.id),
                            ('caf_file', '!=', False)
                        ]).mapped('caf_file')
                        _logger.info('########################1' + str(caf_ids.mapped('display_name')))"""
                        # tomamos el ultimo caf que tenga el tipo de documento y la empresa
                        caf_disponibles = rec.env['l10n_cl.dte.caf'].search([
                            ('l10n_latam_document_type_id', '=', rec.l10n_latam_document_type_id.id),
                            ('usage', '=', 'sale'),
                            ('status', '=', 'in_use'),
                            ('company_id', '=', rec.env.company.id)
                        ], order='create_date ASC', limit=1)
                        _logger.info('########################2' + str(caf_disponibles.mapped('display_name')))
                        if not caf_disponibles:
                            raise UserError('No se encontro Caf valido')
                        inicio = caf_disponibles.start_nb
                        fin = caf_disponibles.final_nb
                        doc_code_prefix = rec.l10n_latam_document_type_id.doc_code_prefix
                        if len(str(inicio)) < 6:
                            len_relleno = 6 - len(str(inicio))
                            i = 0
                            relleno = ''
                            while i < len_relleno:
                                relleno += "0"
                                i += 1
                            name_inicial = doc_code_prefix + ' ' + relleno + str(inicio)
                        else:
                            name_inicial = doc_code_prefix + ' ' + str(inicio)

                        if len(str(fin)) <= 6:
                            len_relleno = 6 - len(str(fin))
                            i = 0
                            relleno = ''
                            while i < len_relleno:
                                relleno += "0"
                                i += 1
                            name_final = doc_code_prefix + ' ' + relleno + str(fin)
                        else:
                            name_final = doc_code_prefix + ' ' + str(fin)

                        _logger.info('Numero inicial y final de caf a usar' + name_inicial + name_final)
                        _logger.info(
                            'Numero inicial y final de caf a usar en busqueda' + str(name_inicial.split(" ", 1)[-1]) + str(
                                name_final.split(" ", 1)[-1]))
                        ultima_invoice = rec.env['account.move'].search(
                            [
                                ('move_type', '=', 'out_invoice'),
                                ('state', '=', 'posted'),
                                ('company_id', '=', rec.env.company.id),
                                ('sequence_number', '>=', int(name_inicial.split(" ", 1)[-1])),
                                ('sequence_number', '<=', int(name_final.split(" ", 1)[-1])),
                                ('l10n_latam_document_type_id.code', '=', rec.l10n_latam_document_type_id.code)
                            ], order='sequence_number DESC', limit=1).mapped('sequence_number')
                        _logger.info('Facturas encontradas ultima sequencia' + str(ultima_invoice))
                        if ultima_invoice:
                            name_new = ultima_invoice[0]
                            _logger.info('Ultimo Numero' + str(name_new))
                            name_new = int(name_new) + 1
                            _logger.info('Nuevo Numero' + str(name_new))
                            if len(str(name_new)) <= 6:
                                len_relleno = 6 - len(str(name_new))
                                i = 0
                                relleno = ''
                                while i < len_relleno:
                                    relleno += "0"
                                    i += 1
                                name = doc_code_prefix + ' ' + relleno + str(name_new)
                            else:
                                name = doc_code_prefix + ' ' + str(name_new)
                            _logger.info('Numero de Factura asignar' + str(name) + ' , ' + str(name_new))

                            rec.name = name
                            rec.sequence_number = name.split(" ", 1)[-1]

                        else:
                            _logger.info('Factura a inicializar' + str(rec.name))
                            """ultima_invoice = rec.env['account.move'].search(
                                [
                                    ('move_type', '=', 'out_invoice'),
                                    ('state', '=', 'posted'),
                                    ('company_id', '=', rec.env.company.id),
                                    ('l10n_latam_document_type_id.code', '=', rec.l10n_latam_document_type_id.code)
                                ], order='sequence_number DESC', limit=1).mapped('sequence_number')
                            _logger.info('Facturas encontradas ultima sequencia' + str(ultima_invoice))"""
                            rec.name = name_inicial
                            rec.sequence_number = inicio
                    else:
                        super(AccountMove, self)._compute_name()
            else:
                # _logger.info('Factura a continuar' + str(rec.name))
                super(AccountMove, self)._compute_name()

    # def _compute_l10n_latam_document_number(self):
    #     recs_with_name = self.filtered(lambda x: x.name != '/')
    #     for rec in recs_with_name:
    #         name = rec.name
    #         doc_code_prefix = rec.l10n_latam_document_type_id.doc_code_prefix
    #         if rec.l10n_latam_document_type_id.code == '39' and name == '/' or name == 'draft' or name=='Borrador':
    #             _logger.info(name)
    #             caf_ids = self.env['ir.sequence'].search([
    #                 ('l10n_latam_document_type_id', '=', rec.l10n_latam_document_type_id.id),
    #                 ('company_id', '=', self.env.company.id)
    #             ]).mapped('caf_file')
    #             caf_disponibles = self.env['l10n_cl.dte.caf'].search([
    #                 ('l10n_latam_document_type_id', '=', rec.l10n_latam_document_type_id.id),
    #                 ('id', 'not in', caf_ids.ids),
    #                 ('company_id', '=', self.env.company.id)
    #             ], order='create_date ASC', limit=1)
    #             if not caf_disponibles:
    #                 raise UserError('No tiene disponible caf configure uno para Boletas')
    #             if len(caf_disponibles) == 1:
    #                 # rec.l10n_latam_document_number = caf_disponibles.start_nb
    #                 if doc_code_prefix and name:
    #                     name = name.split(" ", 1)[-1]
    #                     # name = self._get_last_sequence()
    #                     name_prev = name.split(" ", 1)[-1]
    #                     if int(caf_disponibles.start_nb) <= int(name_prev) <= int(caf_disponibles.final_nb):
    #                         rec.l10n_latam_document_number = name_prev
    #                     else:
    #                         rec.l10n_latam_document_number = caf_disponibles.start_nb
    #             else:
    #                 raise UserError('Tiene mas de un caf disponible y no se cual usar')
    #         else:
    #             # doc_code_prefix = rec.l10n_latam_document_type_id.doc_code_prefix
    #             if doc_code_prefix and name:
    #                 name = name.split(" ", 1)[-1]
    #             rec.l10n_latam_document_number = name
    #     remaining = self - recs_with_name
    #     remaining.l10n_latam_document_number = False
