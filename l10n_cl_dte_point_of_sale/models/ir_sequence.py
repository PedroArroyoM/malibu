# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class IRSequence(models.Model):
    _inherit = 'ir.sequence'

    caf_file = fields.Many2one('l10n_cl.dte.caf')

    @api.onchange('caf_file')
    def set_number_next_actual(self):
        if self.caf_file:
            self.number_next_actual = self.caf_file.start_nb

    def get_caf_file(self, folio=None):
        if not self.caf_file:
            raise Warning('Debe asignar un CAF a la secuencia %s' % self.name)
        if folio and (folio < self.caf_file.start_nb or folio > self.caf_file.final_nb):
            raise Warning('El folio %d se encuentra fuera del rango del CAF (%d-%d)' % (folio,
                                                                                        self.caf_file.start_nb,
                                                                                        self.caf_file.final_nb))
        if self.caf_file.status != 'in_use':
            raise Warning('El CAF se encuentra en el estado %s' % self.caf_file.state)
        return self.caf_file._decode_caf()

    @api.onchange('dte_caf_ids')
    def verificar_pos(self):
        if self.is_dte and self.l10n_latam_document_type_id.code in [39, 41]:
            context = dict(self._context or {})
            id = context.get('default_sequence_id') #Al parecer se complica el contexto y se pierde la referencia id
            query = [
                ('state', 'not in', ['closed']),
                '|',
                ('config_id.secuencia_boleta', '=', id),
                ('config_id.secuencia_boleta_exenta', '=', id),
                ]
            if self.env['pos.session'].search(query):
                raise UserError("No puede Editar CAF de Una sesión de Punto de Ventas abierto. Cierre y contabiliza el punto de ventas primero")