# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class Partner(models.Model):
    _inherit = "res.partner"

    #sync = fields.Boolean(
    #    string="syncred",
    #    default=False,
    #)

    @api.model
    def create_from_ui(self, partner):
        if partner.get('country_id'):
            partner['country_id'] = int(partner.get('country_id'))

        if partner.get('state_id'):
            partner['state_id'] = int(partner.get('state_id'))

        if partner.get('l10n_cl_sii_taxpayer_type'):
            partner['l10n_cl_sii_taxpayer_type'] = str(partner.get('l10n_cl_sii_taxpayer_type'))


        return super().create_from_ui(partner)

    def write(self, values):


        return super().write(values)