from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    city_id = fields.Many2one("res.city", related='partner_id.city_id', string='Comuna')
    country_id = fields.Many2one("res.country", related='partner_id.country_id', string='Country',
                                 default=lambda self: self.env.ref('base.cl'))
    state_id = fields.Many2one("res.country.state", related='partner_id.state_id', string='Ubication',
        domain="[('country_id', '=', country_id), ('type', '=', 'normal'), ('id', '!=', id)]")
    real_city = fields.Char(related='partner_id.real_city', string='City')

    @api.onchange('city_id', 'city', 'state_id')
    def _change_city_province(self):
        this = self.sudo()
        if this.country_id != this.env.ref('base.cl'):
            return
        this.partner_id.city_id = this.city_id
        if this.city_id.state_id.parent_id:
            this.state_id = this.city_id.state_id.parent_id
            this.partner_id.state_id = this.city_id.state_id.parent_id
        if this.state_id == this.env.ref('base.state_cl_13'):
            this.real_city = 'Santiago'
            this.partner_id.real_city = 'Santiago'
        else:
            this.real_city = this.city_id.name
            this.city = this.city_id.name
            this.partner_id.real_city = this.city_id.name
            this.partner_id.city = this.city_id.name

    def _inverse_street(self):
        this = self.sudo()
        for company in this:
            company.partner_id.street = company.street

    def _inverse_street2(self):
        this = self.sudo()
        for company in this:
            company.partner_id.street2 = company.street2

    def _inverse_zip(self):
        this = self.sudo()
        for company in this:
            company.partner_id.zip = company.zip

    def _inverse_city(self):
        this = self.sudo()
        for company in this:
            company.partner_id.city = company.city

    def _inverse_state(self):
        this = self.sudo()
        for company in this:
            company.partner_id.state_id = company.state_id

    def _inverse_country(self):
        this = self.sudo()
        for company in this:
            company.partner_id.country_id = company.country_id

    def _compute_address(self):
        this = self.sudo()
        for company in this.filtered(lambda company: company.partner_id):
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.browse(address_data['contact']).sudo()
                company.update(company._get_company_address_update(partner))