from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _default_country(self):
        try:
            return self.env.user.company_id.country_id or False
        except:
            return False

    country_id = fields.Many2one(
        "res.country",
        default=_default_country)
    state_id = fields.Many2one(
        "res.country.state", 'Ubication',
        domain="[('country_id', '=', country_id), ('type', '=', 'normal'), ('id', '!=', id)]", readonly=True)
    real_city = fields.Char('City')

    @api.onchange('city_id', 'city', 'state_id')
    def _change_city_province(self):
        this = self.sudo()
        if this.country_id != this.env.ref('base.cl'):
            return
        if this.city_id.state_id.parent_id:
            this.state_id = this.city_id.state_id.parent_id
        if this.state_id == this.env.ref('base.state_cl_13'):
            this.real_city = 'Santiago'
        else:
            this.real_city = this.city = this.city_id.name
            this.city = this.city_id.name


