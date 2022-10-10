from operator import itemgetter

from itertools import groupby

import base64
import logging
import pytz
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import _, api, fields, models, _lt
from odoo.exceptions import UserError
from odoo.tools import float_repr, html_escape, DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)


class L10nClDailySalesBook(models.Model):
    _inherit = 'l10n_cl.daily.sales.book'

    pos_order_ids = fields.One2many('pos.order', 'daily_sales_book_id')

    @api.model
    def _create_report(self, date):
        report = self.search([('company_id', '=', self.env.company.id), ('date', '=', date)])
        move_ids = self.env['account.move'].search([
            ('l10n_latam_document_type_id.code', 'in', ['39', '41']),
            ('invoice_date', '>=', date),
            ('invoice_date', '<=', date),
            ('company_id', '=', self.env.company.id),
            ('l10n_cl_dte_status', 'in', ['accepted', 'objected'])
        ]).ids

        # Al comparar date con datetime falla por la zona horaria, se compara datetime con datetime.
        desde = fields.Datetime.from_string(fields.Date.to_string(date))
        tz = pytz.timezone('America/Santiago')
        tz_current = tz.localize(desde).astimezone(pytz.utc)
        desde = fields.Datetime.from_string(tz_current.strftime(DTF))
        hasta = desde + relativedelta(days=1)

        pos_order_ids = self.env['pos.order'].search([
            ('document_class_id.code', 'in', ['39', '41']),
            ('date_order', '>=', desde),
            ('date_order', '<', hasta),
            ('company_id', '=', self.env.company.id),
            ('sii_result', 'in', ['Aceptado'])
        ]).ids
        if not report:
            report = self.create({'date': date, 'move_ids': [(6, 0, move_ids)],
                                  'pos_order_ids': [(6, 0, pos_order_ids)]})
        elif report.l10n_cl_dte_status == 'ask_for_status':
            _logger.info(_('Sales Book for day %s has not been created due to the current status is %s.') % (
                date, report.l10n_cl_dte_status))
            return report
        else:  # increase the sequence if the book already exists
            report.write({'move_ids': [(6, 0, move_ids)], 'pos_order_ids': [(6, 0, pos_order_ids)]})
            report.send_sequence += 1
        items = report._get_summary()
        if not items:  # The sales reporting should have at least one summary
            items.append({
                'document_type': '39',
                'subtotal_amount_taxable': 0,
                'subtotal_amount_exempt': 0,
                'total_amount': 0,
                'total_documents': 0,
                'documents_canceled': 0,
                'documents_used': 0,
                'used_ranges': [],
                'cancelled_ranges': [],
            })

        doc_id = 'CF_' + report.date.strftime('%Y-%m-%d')
        digital_signature = report.company_id._get_digital_signature(user_id=self.env.user.id)
        xml_book = self.env.ref('l10n_cl_edi_boletas.dss_template')._render({
            'object': report,
            'rut_sends': digital_signature.subject_serial_number,
            'id': doc_id,
            'format_vat': self.env['l10n_cl.edi.util']._l10n_cl_format_vat,
            'timestamp': self.env['l10n_cl.edi.util']._get_cl_current_strftime(),
            'items': items,
        })
        envio_dte = self.env['l10n_cl.edi.util']._sign_full_xml(xml_book.decode('utf-8'), digital_signature, doc_id, 'consu')
        attachment = self.env['ir.attachment'].create({
            'name': '%s.xml' % doc_id,
            'res_id': report.id,
            'res_model': report._name,
            'datas': base64.b64encode(envio_dte.encode('ISO-8859-1')),
            'type': 'binary',
        })
        report.write({
            'l10n_cl_dte_status': 'not_sent',
            'l10n_cl_sii_send_file': attachment.id,
        })
        report.message_post(body=_('Daily Sales Book (%s) has been created') % doc_id, attachment_ids=[attachment.id])
        return report

    def _get_summary(self):
        summary = []
        documents = sorted(self.move_ids.mapped('l10n_latam_document_type_id.code')) + \
                    sorted(self.pos_order_ids.mapped('document_class_id.code'))

        if documents:
            for document_type in list(set(documents)):
                values = {'document_type': document_type}
                # Get amounts
                move_ids = self.move_ids.filtered(lambda x: x.l10n_latam_document_type_id.code == document_type)
                vat_taxes = move_ids.line_ids.filtered(lambda x: x.tax_line_id.l10n_cl_sii_code == 14)
                lines_with_taxes = move_ids.invoice_line_ids.filtered(lambda x: x.tax_ids)
                lines_without_taxes = move_ids.invoice_line_ids.filtered(lambda x: not x.tax_ids)

                pos_order_ids = self.pos_order_ids.filtered(lambda x: x.document_class_id.code == document_type)
                vat_taxes_pos = pos_order_ids.get_amount_tax_l10n_cl_sii_code(14)
                lines_with_taxes_pos = pos_order_ids.lines.filtered(lambda x: x.tax_ids)
                lines_without_taxes_pos = pos_order_ids.lines.filtered(lambda x: not x.tax_ids)

                values.update({
                    'vat_amount': float_repr(sum(vat_taxes.mapped('price_subtotal')) + vat_taxes_pos, 0),
                    # Sum of the subtotal amount affected by tax
                    'subtotal_amount_taxable': float_repr(sum(lines_with_taxes.mapped('price_subtotal')) +
                                                          sum(lines_with_taxes_pos.mapped('price_subtotal')), 0),
                    # Sum of the subtotal amount not affected by tax
                    'subtotal_amount_exempt': float_repr(sum(lines_without_taxes.mapped('price_subtotal')) +
                                                         sum(lines_without_taxes_pos.mapped('price_subtotal')), 0),
                    'vat_percent': '19.00' if (lines_with_taxes or lines_with_taxes_pos) else False,
                    'total_amount': float_repr(sum(move_ids.mapped('amount_total')) +
                                               sum(pos_order_ids.mapped('amount_total')), 0),
                })
                # Get ranges
                #values['vat_amount'] = float_repr(int(values['subtotal_amount_taxable'])*(19/100), 0)
                values['total_amount'] = float_repr(
                    int(values['vat_amount']) + int(values['subtotal_amount_taxable']) + int(
                        values['subtotal_amount_exempt']), 0)


                move_map = move_ids.mapped('l10n_latam_document_number')
                pos_order_map = pos_order_ids.mapped('sii_document_number')
                if move_map and pos_order_map:
                    mapeo = move_map + pos_order_map
                elif move_map:
                    mapeo = move_map
                elif pos_order_map:
                    mapeo = pos_order_map
                else:
                    mapeo = []
                document_numbers = sorted(set([int(doc_number) for doc_number in mapeo]))
                values.update({
                    'total_documents': len(document_numbers),
                    'documents_canceled': 0,
                    'documents_used': len(document_numbers),
                    'used_ranges': self._get_ranges(document_numbers),
                    'cancelled_ranges': [],
                })
                summary.append(values)
        return summary

    @api.model
    def _cron_run_sii_sales_book_report_process(self):
        for company in self.env['res.company'].search([('partner_id.country_id.code', '=', 'CL')]):
            shared_certificates = company.sudo().l10n_cl_certificate_ids.filtered(
                lambda x: x._is_valid_certificate() and not x.user_id and x.company_id.id == company.id)
            if not shared_certificates:
                continue
            self_skip = self.with_company(company=company.id).with_context(cron_skip_connection_errs=True)
            books = self_skip._create_month_calendar_report()
            self.env.cr.commit()
            books._l10n_cl_send_books_to_sii()
            self_skip._send_pending_sales_book_report_to_sii()