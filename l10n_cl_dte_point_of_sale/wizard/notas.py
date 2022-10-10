# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError
import time
import logging
_logger = logging.getLogger(__name__)


class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _name = "pos.order.refund"
    _description=""
    tipo_nota = fields.Many2one(
            'l10n_latam.document.type',
            string="Tipo De nota",
            required=True,
            domain=[('internal_type','in',['debit_note','credit_note'])],
        )
    filter_refund = fields.Selection(
            [
                ('1','Anula Documento de Referencia'),
                ('2','Corrige texto Documento Referencia'),
                ('3','Corrige montos'),
            ],
            default='1',
            string='Refund Method',
            required=True, help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled',
        )
    motivo = fields.Char("Motivo")
    date_order = fields.Date(string="Fecha de Documento")

    #@api.multi
    def confirm(self):
        """Create a copy of order  for refund order"""
        clone_list = self.env['pos.order']
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for order in self.env['pos.order'].browse(active_ids):
            if not order.document_class_id or not order.sii_document_number:
                raise UserError("Por esta área solamente se puede crear Nota de Crédito a Boletas validamente emitidas, si es un pedido simple, debe presionar en retornar simple")
            current_session = self.env['pos.session'].search(
                    [
                        ('state', '!=', 'closed'),
                        ('user_id', '=', self.env.uid),
                    ],
                    limit=1
                )
            if not current_session:
                raise UserError(_('To return product(s), you need to open a session that will be used to register the refund.'))
            jdc_ob = self.env['l10n_latam.document.type']

            query = """select b.id, c.id from l10n_cl_journal_sequence_rel a 
                        join ir_sequence b on a.sequence_id = b.id 
                        join l10n_latam_document_type c on b.l10n_latam_document_type_id = c.id where c.code = '%s' limit 1 """ %(self.tipo_nota.code)

            self._cr.execute(query)

            sequence_id = self._cr.fetchall()

            if not sequence_id:
                raise UserError("Por favor defina Secuencia de Notas de Crédito en algun diario de ventas")
            clone_id = order.copy({
                'name': order.name + ' REFUND', # not used, name forced by create
                'session_id': current_session.id,
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
                'sequence_id': sequence_id[0][0],
                'document_class_id': sequence_id[0][1],
                'sii_document_number': 0,
                'signature': False,
                'referencias': [[5,],[0,0, {
                    'origen': int(order.sii_document_number),
                    'sii_referencia_TpoDocRef': order.document_class_id.id,
                    'sii_referencia_CodRef': self.filter_refund,
                    'motivo': self.motivo,
                    'fecha_documento': self.date_order
                }]],
                'lines': False,
                'amount_tax': -order.amount_tax,
                'amount_total': -order.amount_total,
                'amount_paid': 0,
            })
            clone_list += clone_id
            for line in order.lines:
                line.copy({
                        'qty': -line.qty,
                        'order_id': clone_id.id,
                        'price_subtotal': -line.price_subtotal,
                        'price_subtotal_incl': -line.price_subtotal_incl,
                    })
        abs = {
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': clone_list.ids[0],
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        return abs
