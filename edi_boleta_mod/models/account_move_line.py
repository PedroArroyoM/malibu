from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    dte_product_string = fields.Char('producto a mostrar')
