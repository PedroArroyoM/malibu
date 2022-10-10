from odoo import fields, models, api
from odoo.exceptions import UserError


class L10n_clDteCaf(models.Model):
    _inherit = 'l10n_cl.dte.caf'

    usage = fields.Selection(
        [
            ('sale', 'Ventas'),
            ('pos', 'Pos'),
            ('other', 'Otro'),
        ], default='other', string='Uso', required=True)

    status = fields.Selection(selection_add=[('out_use', 'Fuera de uso')])

    # funcion que cambia el status de un caf a fuera de uso
    def action_out_use(self):
        self.status = 'out_use'

    # funcion que valida que solo exista un caf para ventas disponible por compañia
    @api.constrains('usage', 'status', 'company_id', 'l10n_latam_document_type_id')
    def _check_caf_usage(self):
        caf_disponibles = self.env['l10n_cl.dte.caf'].search([
            ('usage', '=', 'sale'),
            ('l10n_latam_document_type_id', '=', self.l10n_latam_document_type_id.id),
            ('status', '=', 'in_use'),
            ('company_id', '=', self.company_id.id)
        ])
        if len(caf_disponibles) > 1:
            raise UserError('Solo puede existir un caf para ventas disponible por compañia y tipo de documento')
