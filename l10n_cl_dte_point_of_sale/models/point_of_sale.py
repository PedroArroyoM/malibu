# -*- coding: utf-8 -*-
import collections
import logging
import re
from datetime import datetime
from html import unescape

import pytz
import urllib3

from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)

try:
    from io import BytesIO
except:
    _logger.warning("no se ha cargado io")
try:
    from suds.client import Client
except:
    pass
try:
    import xmltodict
except ImportError:
    _logger.info('Cannot import xmltodict library')
try:
    import dicttoxml

    dicttoxml.set_debug(False)
except ImportError:
    _logger.info('Cannot import dicttoxml library')
try:
    import pdf417gen
except ImportError:
    _logger.info('Cannot import pdf417gen library')
try:
    import base64
except ImportError:
    _logger.info('Cannot import base64 library')

try:
    import cchardet
except ImportError:
    _logger.info('Cannot import cchardet library')

urllib3.disable_warnings()
pool = urllib3.PoolManager(cert_reqs='CERT_NONE')

# timbre patrón. Permite parsear y formar el
# ordered-dict patrón corespondiente al documento
timbre = """<TED version="1.0"><DD><RE>99999999-9</RE><TD>11</TD><F>1</F>\
<FE>2000-01-01</FE><RR>99999999-9</RR><RSR>\
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX</RSR><MNT>10000</MNT><IT1>IIIIIII\
</IT1><CAF version="1.0"><DA><RE>99999999-9</RE><RS>YYYYYYYYYYYYYYY</RS>\
<TD>10</TD><RNG><D>1</D><H>1000</H></RNG><FA>2000-01-01</FA><RSAPK><M>\
DJKFFDJKJKDJFKDJFKDJFKDJKDnbUNTAi2IaDdtAndm2p5udoqFiw==</M><E>Aw==</E></RSAPK>\
<IDK>300</IDK></DA><FRMA algoritmo="SHA1withRSA">\
J1u5/1VbPF6ASXkKoMOF0Bb9EYGVzQ1AMawDNOy0xSuAMpkyQe3yoGFthdKVK4JaypQ/F8\
afeqWjiRVMvV4+s4Q==</FRMA></CAF><TSTED>2014-04-24T12:02:20</TSTED></DD>\
<FRMT algoritmo="SHA1withRSA">jiuOQHXXcuwdpj8c510EZrCCw+pfTVGTT7obWm/\
fHlAa7j08Xff95Yb2zg31sJt6lMjSKdOK+PQp25clZuECig==</FRMT></TED>"""
result = xmltodict.parse(timbre)

server_url = {'SIITEST': 'https://maullin.sii.cl/DTEWS/', 'SII': 'https://palena.sii.cl/DTEWS/'}

connection_status = {
    '0': 'Upload OK',
    '1': 'El Sender no tiene permiso para enviar',
    '2': 'Error en tamaño del archivo (muy grande o muy chico)',
    '3': 'Archivo cortado (tamaño <> al parámetro size)',
    '5': 'No está autenticado',
    '6': 'Empresa no autorizada a enviar archivos',
    '7': 'Esquema Invalido',
    '8': 'Firma del Documento',
    '9': 'Sistema Bloqueado',
    'Otro': 'Error Interno.',
}


class posorderline(models.Model):
    _inherit = 'pos.order.line'

    pos_order_line_id = fields.Integer(
        string="POS Line ID",
        readonly=True,
    )

    """@api.depends('price_unit', 'tax_ids', 'qty', 'discount', 'product_id')
    def _compute_amount_line_all(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id
            tax_ids_after_fiscal_position = fpos.map_tax(line.tax_ids, line.product_id, line.order_id.partner_id) if fpos else line.tax_ids
            taxes = tax_ids_after_fiscal_position.compute_all(line.price_unit, 
			line.order_id.pricelist_id.currency_id, 
			line.qty, 
			product=line.product_id, 
			partner=line.order_id.partner_id)
            line.update({
                'price_subtotal_incl': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })"""


class posorder(models.Model):
    _name = 'pos.order'
    _description = ""
    _inherit = ['pos.order', 'l10n_cl.edi.util', 'mail.thread']

    def _get_available_sequence(self):
        ids = ['39', '41']
        if self.sequence_id and self.sequence_id.code == 61:
            ids = ['61']
        return [('document_class_id.code', 'in', ids)]

    def _get_barcode_img(self):
        for r in self:
            r.sii_barcode_img = base64.b64encode(b"")
            if r.signature:
                barcodefile = BytesIO()
                image = self.pdf417bc(r.signature)
                image.save(barcodefile, 'PNG')
                data = barcodefile.getvalue()
                r.sii_barcode_img = base64.b64encode(data)

    signature = fields.Char(
        string="Signature",
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Sequencia de Boleta',
        states={'draft': [('readonly', False)]},
        domain=lambda self: self._get_available_sequence(),
    )
    document_class_id = fields.Many2one(
        'l10n_latam.document.type',
        string='Document Type',
        copy=False,
    )
    sii_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True,
        help='Batch number for processing multiple invoices together',
    )
    sii_barcode = fields.Char(
        copy=False,
        string='SII Barcode',
        readonly=True,
        help='SII Barcode Name',
    )
    sii_barcode_img = fields.Binary(
        copy=False,
        string=_('SII Barcode Image'),
        help='SII Barcode Image in PDF417 format',
        compute='_get_barcode_img',
    )
    # sii_xml_request = fields.Many2one(
    #    'sii.xml.envio',
    #    string='SII XML Request',
    #    copy=False,
    # )
    sii_result = fields.Selection(
        [
            ('', 'n/a'),
            ('NoEnviado', 'No Enviado'),
            ('EnCola', 'En cola de envío'),
            ('Enviado', 'Enviado'),
            ('Aceptado', 'Aceptado'),
            ('Rechazado', 'Rechazado'),
            ('Reparo', 'Reparo'),
            ('Proceso', 'Proceso'),
            ('Reenviar', 'Reenviar'),
            ('Anulado', 'Anulado')
        ],
        string='Resultado',
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        help="SII request result",
        default='',
    )
    canceled = fields.Boolean(
        string="Canceled?",
    )
    responsable_envio = fields.Many2one(
        'res.users',
    )
    sii_document_number = fields.Integer(
        string="Folio de documento",
        # copy=False,
    )
    exento = fields.Integer(
        string="Base exento",
        # copy=False,
    )
    referencias = fields.One2many(
        'pos.order.referencias',
        'order_id',
        string="References",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    sii_xml_dte = fields.Text(
        string='SII XML DTE',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    l10n_cl_sii_send_file = fields.Many2one('ir.attachment', string='SII Send file', copy=False)
    sii_message = fields.Text(
        string='SII Message',
        copy=False,
    )
    l10_cl_ticket = fields.Boolean(string='Ticket Format', default=False, readonly=True,
                                   states={'draft': [('readonly', False)]}, )
    error = fields.Char("error al procesar en consumo de folio")
    daily_sales_book_id = fields.Many2one('l10n_cl.daily.sales.book')

    """@api.model
    def _amount_line_tax(self, line, fiscal_position_id):
        taxes = line.tax_ids.filtered(lambda t: t.company_id.id == line.order_id.company_id.id)
        if fiscal_position_id:
            taxes = fiscal_position_id.map_tax(taxes, line.product_id, line.order_id.partner_id)
        cur = line.order_id.pricelist_id.currency_id
        taxes = taxes.compute_all(line.price_unit, cur, line.qty, product=line.product_id, partner=line.order_id.partner_id or False, discount=line.discount)['taxes']
        return sum(tax.get('amount', 0.0) for tax in taxes)"""

    def get_amount_tax_l10n_cl_sii_code(self, sii_code):
        amount = 0.0
        for order in self:
            for line in order.lines:
                if line.tax_ids_after_fiscal_position:
                    for tax in line.tax_ids_after_fiscal_position:
                        if tax.l10n_cl_sii_code and tax.l10n_cl_sii_code == sii_code:
                            amount += abs(round(line.price_subtotal * line.qty * tax.amount / 100, 2))
        return amount

    def create_template_envio(self, RutEmisor, RutReceptor, FchResol, NroResol,
                              TmstFirmaEnv, EnvioDTE, subject_serial_number, SubTotDTE):
        xml = '''\n<SetDTE ID="SetDoc">
<Caratula version="1.0">
<RutEmisor>{0}</RutEmisor>
<RutEnvia>{1}</RutEnvia>
<RutReceptor>{2}</RutReceptor>
<FchResol>{3}</FchResol>
<NroResol>{4}</NroResol>
<TmstFirmaEnv>{5}</TmstFirmaEnv>
{6}</Caratula>{7}
</SetDTE>
'''.format(RutEmisor, subject_serial_number, RutReceptor,
           FchResol, NroResol, TmstFirmaEnv, SubTotDTE, EnvioDTE)
        return xml

    def time_stamp(self, formato='%Y-%m-%dT%H:%M:%S'):
        tz = pytz.timezone('America/Santiago')
        return datetime.now(tz).strftime(formato)

    def create_template_doc(self, doc):
        xml = '''<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
{}
</DTE>'''.format(doc)
        return xml

    def create_template_env(self, doc):
        xml = '''<EnvioDTE xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioDTE_v10.xsd" \
version="1.0">
{}
</EnvioDTE>'''.format(doc)
        return xml

    def create_template_env_boleta(self, doc):
        xml = '''\n<EnvioBOLETA xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioBOLETA_v11.xsd" \
version="1.0">
{}
</EnvioBOLETA>'''.format(doc)
        return xml

    def get_resolution_data(self, comp_id):
        resolution_data = {
            'l10n_cl_dte_resolution_number': comp_id.l10n_cl_dte_resolution_number,
            'l10n_cl_dte_resolution_date': comp_id.l10n_cl_dte_resolution_date}
        return resolution_data

    def crear_intercambio(self):
        rut = self.format_vat(self.partner_id.commercial_partner_id.vat)
        envios, filename = self._crear_envio(RUTRecep=rut)
        return envios[list(envios.keys())[0]].encode('ISO-8859-1')

    def _create_attachment(self, ):
        url_path = '/download/xml/boleta/%s' % (self.id)
        filename = ('%s%s.xml' % (self.document_class_id.doc_code_prefix, self.sii_document_number)).replace(' ', '_')
        att = self.env['ir.attachment'].search(
            [
                ('name', '=', filename),
                ('res_id', '=', self.id),
                ('res_model', '=', 'pos.order')
            ],
            limit=1,
        )
        if att:
            return att
        xml_intercambio = self.crear_intercambio()
        data = base64.b64encode(xml_intercambio)
        values = dict(
            name=filename,
            datas_fname=filename,
            url=url_path,
            res_model='pos.order',
            res_id=self.id,
            type='binary',
            datas=data,
        )
        att = self.env['ir.attachment'].sudo().create(values)
        return att

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(posorder, self)._order_fields(ui_order)
        order_fields['sii_barcode'] = ui_order.get('sii_barcode', False)
        order_fields['sii_barcode_img'] = ui_order.get('sii_barcode_img', False)
        sequence = ui_order.get('sequence_id', False)
        if sequence:
            sequence = self.env['ir.sequence'].browse(sequence['id'])
            doc_cls_id = sequence.l10n_latam_document_type_id
            order_fields['sequence_id'] = sequence['id'] if sequence else False
            order_fields['document_class_id'] = doc_cls_id.id

        order_fields['sii_document_number'] = ui_order.get('sii_document_number', False)
        order_fields['l10_cl_ticket'] = ui_order.get('l10_cl_ticket', False)

        return order_fields

    def get_folio(self):
        return int(self.sii_document_number)

    def format_vat(self, value):
        if not value or value == '' or value == 0:
            value = "CL666666666"
        rut = value[:10] + '-' + value[10:]
        rut = rut.replace('CL0', '').replace('CL', '')
        return rut

    def pdf417bc(self, ted):
        bc = pdf417gen.encode(
            ted,
            security_level=5,
            columns=13,
        )
        image = pdf417gen.render_image(
            bc,
            padding=15,
            scale=1,
        )
        return image

    def _acortar_str(self, texto, size=1):
        c = 0
        cadena = ""
        while c < size and c < len(texto):
            cadena += texto[c]
            c += 1
        return cadena

    @api.model
    def _process_order(self, order, draft, existing_order):
        lines = []
        order_cp = order['data']
        for l in order_cp['lines']:
            l[2]['pos_order_line_id'] = int(l[2]['id'])
            lines.append(l)
        order_cp['lines'] = lines
        order_id = super(posorder, self)._process_order(order, draft, existing_order)
        order_id = self.browse(order_id)
        order_id.sequence_number = order_cp['sequence_number']  # FIX odoo bug
        if order_cp.get('orden_numero', False) and order_cp.get('sequence_id', False):
            order_id.sequence_id = order_cp['sequence_id'].get('id', False)
            order_id.document_class_id = order_id.sequence_id.l10n_latam_document_type_id.id


            if order_id.sequence_id and int(order_id.document_class_id.code) == 39 and order_cp[
                'orden_numero'] > order_id.session_id.numero_ordenes:
                order_id.session_id.numero_ordenes = order_cp['orden_numero']
            elif order_id.sequence_id and int(order_id.document_class_id.code) == 41 and order_cp[
                'orden_numero'] > order_id.session_id.numero_ordenes_exentas:
                order_id.session_id.numero_ordenes_exentas = order_cp['orden_numero']
            #order_id.sii_document_number = order_cp['sii_document_number']
            #order_id.sii_barcode_img = order_cp['barcode']
            #order_id.signature = order_cp['signature']
            order_id.sequence_id.with_user(SUPERUSER_ID).number_next_actual = order_cp[
                'sii_document_number']  # consumo Folio

            # Si ya timbró, devuelvo la orden, sino timbro.
            #if order_id.sii_result and order_id.l10n_cl_sii_send_file:
            #    return order_id.id
            #else:
            #    sign = self.env.user.company_id._get_digital_signature(self.env.user.id)
            #    if (order_id.session_id.caf_files or order_id.session_id.caf_files_exentas) and sign:
            #        order_id.signature = order_cp['signature']
                    #order_id._timbrar()

            if (order_id.sequence_id and int(order_id.document_class_id.code) == 39) or (
                    order_id.sequence_id and int(
                    order_id.document_class_id.code) == 41):
                order_id.to_invoice = True
                # if order_id.state == 'paid':
                if not order_id.partner_id:
                    order_id.partner_id = self.env.ref('l10n_cl.par_cfa')
                order_id._generate_pos_order_invoice()

        return order_id.id

    def _prepare_invoice_vals(self):
        result = super(posorder, self)._prepare_invoice_vals()
        if (self.sequence_id and int(self.document_class_id.code) == 39) or (self.sequence_id and int(
                self.document_class_id.code) == 41):


            result.update({
                'l10n_latam_document_type_id': self.document_class_id.id,
                'l10n_latam_document_number': self.sii_document_number,
            })
            return result
        else:
            return result
    # @api.multi
    def do_validate(self):
        ids = []
        for order in self:
            if order.session_id.config_id.restore_mode:
                continue
            order.sii_result = 'NoEnviado'
            if not order.to_invoice or order.is_invoiced:
                order.do_dte_send_order()
            if order.document_class_id.code in ['61']:
                ids.append(order.id)

    # @api.multi
    def do_dte_send_order(self):
        ids = []
        for order in self:
            if not order.account_move:
                if order.sii_result not in [False, '', 'NoEnviado', 'Rechazado']:
                    raise UserError(
                        "El documento %s ya ha sido enviado o está en cola de envío" % order.sii_document_number)
                if order.document_class_id.code in ['61']:
                    ids.append(order.id)
        self.do_dte_send()

    def _giros_emisor(self):
        giros_emisor = []
        for turn in self.company_id.company_activities_ids:
            giros_emisor.extend([{'Acteco': turn.code}])
        return giros_emisor

    def _id_doc(self, taxInclude=False, MntExe=0):
        util_model = self.env['cl.utils']
        fields_model = self.env['ir.fields.converter']
        from_zone = pytz.UTC
        to_zone = pytz.timezone('America/Santiago')
        date_order = util_model._change_time_zone(datetime.strptime(self.date_order.strftime(DTF), DTF), from_zone,
                                                  to_zone).strftime(DTF)
        IdDoc = collections.OrderedDict()
        IdDoc['TipoDTE'] = int(self.document_class_id.code)
        IdDoc['Folio'] = self.get_folio()
        IdDoc['FchEmis'] = date_order[:10]
        if self.document_class_id.es_boleta():
            IdDoc['IndServicio'] = 3  # @TODO agregar las otras opciones a la fichade producto servicio
        else:
            IdDoc['TpoImpresion'] = "T"
            IdDoc['MntBruto'] = 1
            IdDoc['FmaPago'] = 1
        # if self.tipo_servicio:
        #    Encabezado['IdDoc']['IndServicio'] = 1,2,3,4
        # todo: forma de pago y fecha de vencimiento - opcional
        if not taxInclude and self.document_class_id.es_boleta():
            IdDoc['IndMntNeto'] = 2
        # if self.document_class_id.es_boleta():
        # Servicios periódicos
        #    IdDoc['PeriodoDesde'] =
        #    IdDoc['PeriodoHasta'] =
        return IdDoc

    def _emisor(self):
        Emisor = collections.OrderedDict()
        Emisor['RUTEmisor'] = self.company_id.vat
        if self.document_class_id.es_boleta():
            Emisor['RznSocEmisor'] = self.company_id.partner_id.name
            Emisor['GiroEmisor'] = self._acortar_str(self.company_id.l10n_cl_activity_description, 80)
        else:
            Emisor['RznSoc'] = self.company_id.partner_id.name
            Emisor['GiroEmis'] = self._acortar_str(self.company_id.l10n_cl_activity_description, 80)
            Emisor['Telefono'] = self.company_id.phone or ''
            Emisor['CorreoEmisor'] = self.company_id.dte_email_id.name_get()[0][1]
            Emisor['item'] = self._giros_emisor()
        # if self.sale_journal.sucursal_id:
        #    Emisor['Sucursal'] = self.sale_journal.sucursal_id.name
        #    Emisor['CdgSIISucur'] = self.sale_journal.sucursal_id.code
        Emisor['DirOrigen'] = self.company_id.street + ' ' + (self.company_id.street2 or '')
        Emisor['CmnaOrigen'] = self.company_id.city or ''
        Emisor['CiudadOrigen'] = self.company_id.city or ''
        return Emisor

    def _receptor(self):
        Receptor = collections.OrderedDict()
        # Receptor['CdgIntRecep']
        Receptor['RUTRecep'] = self.format_vat(self.partner_id.vat)
        Receptor['RznSocRecep'] = self._acortar_str(self.partner_id.name or "Usuario Anonimo", 100)
        if self.partner_id.phone:
            Receptor['Contacto'] = self.partner_id.phone
        if self.partner_id.l10n_cl_dte_email and not self.document_class_id.es_boleta():
            Receptor['CorreoRecep'] = self.partner_id.l10n_cl_dte_email
        if self.partner_id.street:
            Receptor['DirRecep'] = self.partner_id.street + ' ' + (self.partner_id.street2 or '')
        if self.partner_id.city_id:
            Receptor['CmnaRecep'] = self.partner_id.city_id.name
        if self.partner_id.city:
            Receptor['CiudadRecep'] = self.partner_id.city
        return Receptor

    def _totales(self, MntExe=0, no_product=False, taxInclude=False):
        currency = self.pricelist_id.currency_id
        Totales = collections.OrderedDict()
        amount_total = currency.round(self.amount_total)
        if amount_total < 0:
            amount_total *= -1
        if no_product:
            amount_total = 0
        else:
            if self.document_class_id.code in ['34', '41'] and self.amount_tax > 0:
                raise UserError("NO pueden ir productos afectos en documentos exentos")
            amount_untaxed = self.amount_total - self.amount_tax
            if amount_untaxed < 0:
                amount_untaxed *= -1
            if MntExe < 0:
                MntExe *= -1
            if self.amount_tax == 0 and self.document_class_id.code in ['39']:
                raise UserError("Debe ir al menos un Producto Afecto. registro id %s" % self.id)
            Neto = amount_untaxed - MntExe
            IVA = False
            # if Neto > 0 and not self.document_class_id.es_boleta():
            for l in self.lines:
                for t in l.tax_ids:
                    if t.l10n_cl_sii_code in [14, 15]:
                        IVA = True
                        IVAAmount = round(t.amount, 2)
                if IVA:
                    Totales['MntNeto'] = currency.round(Neto)
            if MntExe > 0:
                Totales['MntExe'] = currency.round(MntExe)
            if IVA:  # and not self.document_class_id.es_boleta():
                Totales['TasaIVA'] = IVAAmount
                iva = currency.round(self.amount_tax)
                if iva < 0:
                    iva *= -1
                Totales['IVA'] = iva
            # if IVA and IVA.tax_id.code in [15]:
            #    Totales['ImptoReten'] = collections.OrderedDict()
            #    Totales['ImptoReten']['TpoImp'] = IVA.tax_id.code
            #    Totales['ImptoReten']['TasaImp'] = round(IVA.tax_id.amount,2)
            #    Totales['ImptoReten']['MontoImp'] = int(round(IVA.amount))
        Totales['MntTotal'] = amount_total

        # Totales['MontoNF']
        # Totales['TotalPeriodo']
        # Totales['SaldoAnterior']
        # Totales['VlrPagar']
        return Totales

    def _encabezado(self, MntExe=0, no_product=False, taxInclude=False):
        Encabezado = collections.OrderedDict()
        Encabezado['IdDoc'] = self._id_doc(taxInclude, MntExe)
        Encabezado['Emisor'] = self._emisor()
        Encabezado['Receptor'] = self._receptor()
        Encabezado['Totales'] = self._totales(MntExe, no_product, taxInclude)
        return Encabezado

    def _get_caf_file(self):
        folio = self.get_folio()
        return self.sequence_id.get_caf_file(int(folio))

    def _check_foreign_partner(self):
        return (
                self.partner_id.l10n_cl_sii_taxpayer_type == '4' and
                self.partner_id.country_id != self.env.ref('base.cl')
        )

    def _get_barcode_xml(self):
        """
        This method create the "stamp" (timbre). Is the auto-contained information inside the pdf417 barcode, which
        consists of a reduced xml version of the invoice, containing: issuer, recipient, folio and the first line
        of the invoice, etc.
        :return: xml that goes embedded inside the pdf417 code
        """
        dd = self.env.ref('l10n_cl_dte_point_of_sale.dd_template')._render({
            'move': self,
            'is_doc_type_export': self.sequence_id.l10n_latam_document_type_id._is_doc_type_export,
            'format_vat': self.env['l10n_cl.edi.util']._l10n_cl_format_vat,
            'format_length': self.env['l10n_cl.edi.util']._format_length,
            'time_stamp': self.env['l10n_cl.edi.util']._get_cl_current_strftime(),
            'caf': self._get_caf_file()
        })
        dd = re.sub(rb'&amp;', b'&', dd)

        caf_file = self.sequence_id.get_caf_file(int(self.sii_document_number))
        private_key = caf_file.xpath('//AUTORIZACION/RSASK')[0].text.replace('\t', '')
        frmt = self.env['l10n_cl.edi.util']._sign_message(dd, private_key)
        ted = self.env.ref('l10n_cl_edi.ted_template')._render({
            'dd': dd,
            'frmt': frmt,
            'stamp': self.env['l10n_cl.edi.util']._get_cl_current_strftime()
        })
        ted = re.sub(r'\n\s*$', '', unescape(ted.decode('utf-8')), flags=re.MULTILINE)
        self.sii_barcode = ted
        return ted

    # @api.multi
    def get_barcode(self, no_product=False):
        ted = self._get_barcode_xml()

        """if self.signature and ted != self.signature:
            _logger.warning(ted)
            _logger.warning(self.signature)
            _logger.warning("¡La firma del pos es distinta a la del Backend!")"""
        self.sii_barcode = ted
        # ted  += '<TmstFirma>{}</TmstFirma>'.format(timestamp)
        return ted
        # return self.sii_barcode

    def _invoice_lines(self):
        currency = self.pricelist_id.currency_id
        line_number = 1
        invoice_lines = []
        no_product = False
        MntExe = 0
        for line in self.lines:
            if line.product_id.default_code == 'NO_PRODUCT':
                no_product = True
            lines = collections.OrderedDict()
            lines['NroLinDet'] = line_number
            if line.product_id.default_code and not no_product:
                lines['CdgItem'] = collections.OrderedDict()
                lines['CdgItem']['TpoCodigo'] = 'INT1'
                lines['CdgItem']['VlrCodigo'] = line.product_id.default_code
            taxInclude = True
            for t in line.tax_ids:
                if t.amount == 0:  # or t.code in [0]:#@TODO mejor manera de identificar exento de afecto
                    lines['IndExe'] = 1
                    MntExe += currency.round(line.price_subtotal_incl)
                else:
                    taxInclude = t.price_include
            # if line.product_id.type == 'events':
            #   lines['ItemEspectaculo'] =
            #            if self._es_boleta():
            #                lines['RUTMandante']
            lines['NmbItem'] = self._acortar_str(line.product_id.name, 80)  #
            lines['DscItem'] = self._acortar_str(line.name, 1000)  # descripción más extenza
            if line.product_id.default_code:
                lines['NmbItem'] = self._acortar_str(
                    line.product_id.name.replace('[' + line.product_id.default_code + '] ', ''), 80)
            # lines['InfoTicket']
            qty = round(line.qty, 4)
            if qty < 0:
                qty *= -1
            if not no_product:
                lines['QtyItem'] = qty
            if qty == 0 and not no_product:
                lines['QtyItem'] = 1
                # raise UserError("NO puede ser menor que 0")
            if not no_product:
                lines['UnmdItem'] = line.product_id.uom_id.name[:4]
                lines['PrcItem'] = round(line.price_unit, 4)
            if line.discount > 0:
                lines['DescuentoPct'] = line.discount
                lines['DescuentoMonto'] = currency.round((((line.discount / 100) * lines['PrcItem']) * qty))
            if not no_product and not taxInclude:
                price = currency.round(line.price_subtotal)
            elif not no_product:
                price = currency.round(line.price_subtotal_incl)
            if price < 0:
                price *= -1
            lines['MontoItem'] = price
            if no_product:
                lines['MontoItem'] = 0
            line_number += 1
            if lines.get('PrcItem', 1) == 0:
                del (lines['PrcItem'])
            invoice_lines.extend([{'Detalle': lines}])
        return {
            'invoice_lines': invoice_lines,
            'MntExe': MntExe,
            'no_product': no_product,
            'tax_include': taxInclude,
        }

    def _valida_referencia(self, ref):
        if ref.origen in [False, '', 0]:
            raise UserError("Debe incluir Folio de Referencia válido")

    def _dte(self):
        dte = collections.OrderedDict()
        invoice_lines = self._invoice_lines()
        dte['Encabezado'] = self._encabezado(invoice_lines['MntExe'], invoice_lines['no_product'],
                                             invoice_lines['tax_include'])
        lin_ref = 1
        ref_lines = []
        for ref in self.referencias:
            ref_line = {}
            ref_line = collections.OrderedDict()
            ref_line['NroLinRef'] = lin_ref
            self._valida_referencia(ref)
            if not self.document_class_id.es_boleta():
                if ref.sii_referencia_TpoDocRef:
                    ref_line['TpoDocRef'] = ref.sii_referencia_TpoDocRef.code
                    ref_line['FolioRef'] = ref.origen
                ref_line['FchRef'] = ref.fecha_documento or datetime.strftime(datetime.now(), '%Y-%m-%d')
            if ref.sii_referencia_CodRef not in ['', None, False]:
                ref_line['CodRef'] = ref.sii_referencia_CodRef
            ref_line['RazonRef'] = ref.motivo
            if self.document_class_id.es_boleta():
                ref_line['CodVndor'] = self.user_id.id
                ref_line['CodCaja'] = self.location_id.name
            ref_lines.extend([{'Referencia': ref_line}])
            lin_ref += 1
        dte['item'] = invoice_lines['invoice_lines']
        dte['reflines'] = ref_lines
        dte['TEDd'] = self.get_barcode(invoice_lines['no_product'])
        return dte

    def _dte_to_xml(self, dte):
        ted = dte['Documento ID']['TEDd']
        dte['Documento ID']['TEDd'] = ''
        xml = dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).decode() \
            .replace('<item>', '').replace('</item>', '') \
            .replace('<reflines>', '').replace('</reflines>', '') \
            .replace('<TEDd>', '').replace('</TEDd>', '') \
            .replace('</Documento_ID>', '\n' + ted + '\n</Documento_ID>')
        return xml

    def convert_encoding(self, data, new_coding='UTF-8'):
        if type(data) == str:
            return bytes(data, new_coding)
        encoding = cchardet.detect(data)['encoding']
        if new_coding.upper() != encoding.upper():
            data = data.decode(encoding, data).encode(new_coding)
        return data

    def _l10n_cl_get_withholdings(self):
        """
        This method calculates the section of withholding taxes, or 'other' taxes for Chilean electronic invoices.
        These taxes are not VAT taxes in general; they are special taxes (for example, alcohol or sugar-added beverages,
        withholdings for meat processing, fuel, etc.
        The taxes codes used are included here:
        [15, 17, 18, 19, 24, 25, 26, 27, 271]
        http://www.sii.cl/declaraciones_juradas/ddjj_3327_3328/cod_otros_imp_retenc.pdf
        The need of the tax is not just the amount, but the code of the tax, the percentage amount and the amount
        :return:
        """
        self.ensure_one()
        withholdings = []
        for tax in self.lines.tax_ids.filtered(
                lambda x: x.tax_group_id.id in [self.env.ref('l10n_cl.tax_group_ila').id,
                                                self.env.ref('l10n_cl.tax_group_retenciones').id]):
            lines_with_tax = self.lines.filtered(lambda x: tax.id in x.tax_ids.mapped('id'))
            withholdings.append({
                'tax_code': tax.l10n_cl_sii_code,
                'tax_percent': tax.amount,
                'tax_amount': self.currency_id.round(sum(lines_with_tax.mapped('price_subtotal')))
            })
        return withholdings

    def _l10n_cl_get_amounts(self):
        """
        This method is used for calculation of amount and taxes needed in Chilean localization electronic documents.
        """
        self.ensure_one()
        vat_taxes = self.lines.filtered('tax_ids')
        """vat_taxes = tax_lines.filtered(
            lambda x: x.tax_ids.tax_group_id.id == self.env.ref('l10n_cl.tax_group_iva_19').id)"""
        move_line = self.env['pos.order.line']
        for line in self.lines:
            if any(tax and tax.tax_group_id for tax in line.tax_ids):
                move_line |= line
        vat_amount = self.currency_id.round(self.amount_total) - self.currency_id.round(
            sum(vat_taxes.mapped('price_subtotal')))
        return {
            'vat_amount': vat_amount,  # self.currency_id.round(sum(vat_taxes.mapped('price_subtotal'))),
            'vat_percent': (
                '%.2f' % (vat_taxes[0].tax_ids.mapped('amount')[0])
                if vat_taxes and not self.sequence_id.l10n_latam_document_type_id._is_doc_type_exempt() else False
            ),
            'total_amount': self.currency_id.round(self.amount_total),
        }

    def _timbrar(self, n_atencion=None):
        folio = self.get_folio()
        doc_id_number = "T{}F{}".format(self.document_class_id.code, folio)
        dte_template = self.env.ref('l10n_cl_dte_point_of_sale.dte_template')._render({
            'move': self,
            'is_doc_type_export': self.sequence_id.l10n_latam_document_type_id._is_doc_type_export,
            'is_doc_type_voucher': self.sequence_id.l10n_latam_document_type_id._is_doc_type_voucher,
            'format_vat': self.env['l10n_cl.edi.util']._l10n_cl_format_vat,
            'get_time_stamp': self.env['l10n_cl.edi.util']._get_cl_current_strftime(),
            'format_length': self.env['l10n_cl.edi.util']._format_length,
            'doc_id': doc_id_number,
            'caf': self._get_caf_file(),
            'n_atencion': n_atencion,
            'amounts': self._l10n_cl_get_amounts(),
            'withholdings': self._l10n_cl_get_withholdings(),
            'dte': self._get_barcode_xml(),
        })

        dte = re.sub(r'&', '&amp;', unescape(dte_template.decode('utf-8')))

        signature_d = self.company_id._get_digital_signature(self.user_id.id)

        einvoice = self.env['l10n_cl.edi.util']._sign_full_xml(dte, signature_d, doc_id_number, 'doc',
                                                               self.document_class_id.code)

        self.sii_xml_dte = einvoice
        # xml_dte = dte_signed[(self.document_class_id.code,self.company_id,'env_boleta')]
        attachment = self._l10n_cl_edi_create_attachment(einvoice, doc_id_number)
        # self.sii_xml_dte = xml_dte
        self.l10n_cl_sii_send_file = attachment.id
        self.with_context(no_new_invoice=True).message_post(
            body=_('DTE has been created'),
            attachment_ids=attachment.ids)

    def _l10n_cl_edi_retrieve_attachment(self, file_name):
        if not file_name:
            return []
        domain = [
            ('res_id', '=', self.id),
            ('res_model', '=', self._name),
            ('name', '=', file_name)]
        return self.env['ir.attachment'].search(domain, limit=1)

    def _l10n_cl_edi_create_attachment(self, dte_signed, file_name):
        attachment = self._l10n_cl_edi_retrieve_attachment(file_name)
        attachment.unlink()
        file_name += '.xml'
        return self.env['ir.attachment'].create({
            'name': 'SII_{}'.format(file_name),
            'res_id': self.id,
            'res_model': 'pos.order',
            'datas': base64.b64encode(dte_signed.encode('ISO-8859-1')),
            'type': 'binary',
        })

    def _crear_envio(self, n_atencion=None, RUTRecep="60803000-K"):
        DTEs = {}
        clases = {}
        company_id = False
        es_boleta = False
        for inv in self.with_context(lang='es_CL'):
            if inv.sii_result in ['Rechazado']:
                inv._timbrar()
            if inv.document_class_id.es_boleta():
                es_boleta = True
            # @TODO Mejarorar esto en lo posible
            if not inv.document_class_id.code in clases:
                clases[inv.document_class_id.code] = []
            clases[inv.document_class_id.code].extend([{
                'id': inv.id,
                'envio': inv.sii_xml_dte,
                'sii_document_number': inv.sii_document_number
            }])
            DTEs.update(clases)
            if not company_id:
                company_id = inv.company_id
            elif company_id.id != inv.company_id.id:
                raise UserError("Está combinando compañías, no está permitido hacer eso en un envío")
            company_id = inv.company_id

        file_name = {}
        dtes = {}
        SubTotDTE = {}
        documentos = {}
        resol_data = self.get_resolution_data(company_id)
        signature_id = company_id._get_digital_signature(self.env.user.id)
        RUTEmisor = company_id.vat

        for id_class_doc, classes in clases.items():
            NroDte = 0
            documentos[id_class_doc] = ''
            for documento in classes:
                documentos[id_class_doc] += '\n' + documento['envio']
                NroDte += 1
                if not file_name.get(str(id_class_doc)):
                    file_name[str(id_class_doc)] = ''
                file_name[str(id_class_doc)] += 'F' + str(int(documento['sii_document_number'])) + 'T' + str(
                    id_class_doc) + '.xml'
            SubTotDTE[id_class_doc] = '<SubTotDTE>\n<TpoDTE>' + str(id_class_doc) + '</TpoDTE>\n<NroDTE>' + str(
                NroDte) + '</NroDTE>\n</SubTotDTE>\n'
        envs = {}
        for id_class_doc, documento in documentos.items():
            dtes = self.create_template_envio(
                RUTEmisor,
                RUTRecep,
                resol_data['l10n_cl_dte_resolution_date'],
                resol_data['l10n_cl_dte_resolution_number'],
                self.time_stamp(),
                documento.replace('<?xml version="1.0" encoding="ISO-8859-1" ?>', ''),
                signature_id.subject_serial_number,
                SubTotDTE[id_class_doc])
            env = 'env'
            if es_boleta:
                envio_dte = self.create_template_env_boleta(dtes)
                env = 'env_boleta'
            else:
                envio_dte = self.create_template_env(dtes)

            dte = unescape(envio_dte).replace(r'&', '&amp;')
            digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
            signed_dte = self.with_user(1)._sign_full_xml(
                dte,
                digital_signature,
                file_name[str(id_class_doc)],
                'bol',
                self.sequence_id.l10n_latam_document_type_id._is_doc_type_voucher()
            )

            envs[(id_class_doc, company_id, env)] = signed_dte
        return envs, file_name

    # @api.multi
    def do_dte_send(self, n_atencion=None):
        envs, file_name = self._crear_envio(n_atencion=n_atencion)
        to_return = False
        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        for id_class_doc, env in envs.items():
            # response = self.with_context(api_boleta=True)._send_xml_to_sii(
            #     self.company_id.l10n_cl_dte_service_provider,
            #     self.company_id.website,
            #     self.company_id.vat,
            #     file_name[str(id_class_doc[0])],
            #     env,
            #     digital_signature,
            #     post="boleta.electronica.envio",
            #     api=True
            # )
            response = self._send_xml_to_sii_rest(
                mode=self.company_id.l10n_cl_dte_service_provider,
                company_vat=self.company_id.vat,
                file_name=file_name[str(id_class_doc[0])],
                xml_message=env,
                digital_signature=digital_signature)
            self.sii_message = response
            if response:
                # try:
                #     response = json.loads(response)
                # except Exception as e:
                #     _logger.exception("Respuesta sii no es json " + str(e))
                if 'estado' in response and response.get('estado') == 'REC':
                    self.sii_result = 'Aceptado'
                else:
                    self.sii_result = 'NoEnviado'
                    digital_signature.last_token = False
            return response

        # @api.multi

    def get_sii_status(self):

        response = self.sii_message
        if response:
            try:
                # response = json.loads(response)
                response = eval(response)
            except Exception as err:
                raise UserError('No es posible evaluar respuesta del SII')

            if 'trackid' in response:
                trackid = response.get('trackid')

                digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
                response = self._get_send_status(
                    self.company_id.l10n_cl_dte_service_provider,
                    trackid,
                    self._l10n_cl_format_vat(self.company_id.vat),
                    digital_signature)
                if not response:
                    self.l10n_cl_dte_status = 'ask_for_status'
                    digital_signature.last_token = False
                    return None

    @api.onchange('sii_message')
    def get_sii_result(self):
        for r in self:
            if r.sii_message:
                r.sii_result = self.env['account.move'].process_response_xml(xmltodict.parse(r.sii_message))
                continue
            if r.sii_xml_request.state == 'NoEnviado':
                r.sii_result = 'EnCola'
                continue
            r.sii_result = r.sii_xml_request.state

    def _get_dte_status(self):

        digital_signature = self.company_id._get_digital_signature(user_id=self.env.user.id)
        response = self.with_context(boleta=True)._get_send_status(
            self.company_id.l10n_cl_dte_service_provider,
            self.l10n_cl_sii_send_ident,
            self._l10n_cl_format_vat(self.company_id.vat),
            digital_signature)
        if not response:
            self.l10n_cl_dte_status = 'ask_for_status'
            digital_signature.last_token = False
            return None

    # @api.multi
    def ask_for_dte_status(self):
        for r in self:
            if not r.l10n_cl_sii_send_ident:
                raise UserError('No se ha enviado aún el documento, aún está en cola de envío interna en odoo')
            if r.sii_xml_request.state not in ['Aceptado', 'Rechazado']:
                r.sii_xml_request.get_send_status(r.env.user)
        try:
            self._get_dte_status()
        except Exception as e:
            _logger.warning("Error al obtener DTE Status: %s" % str(e))
        self.get_sii_result()

    def send_exchange(self):
        att = self._create_attachment()
        body = 'XML de Intercambio DTE: %s%s' % (self.document_class_id.doc_code_prefix, self.sii_document_number)
        subject = 'XML de Intercambio DTE: %s%s' % (self.document_class_id.doc_code_prefix, self.sii_document_number)
        dte_email_id = self.company_id.dte_email_id or self.env.user.company_id.dte_email_id
        dte_receptors = self.partner_id.commercial_partner_id.child_ids + self.partner_id.commercial_partner_id
        email_to = ''
        for l10n_cl_dte_email in dte_receptors:
            if not l10n_cl_dte_email.send_dte:
                continue
            email_to += l10n_cl_dte_email.name + ','
        values = {
            'res_id': self.id,
            'email_from': dte_email_id.name_get()[0][1],
            'email_to': email_to[:-1],
            'auto_delete': False,
            'model': 'pos.order',
            'body': body,
            'subject': subject,
            'attachment_ids': [[6, 0, att.ids]],
        }
        send_mail = self.env['mail.mail'].sudo().create(values)
        send_mail.send()

    def _create_account_move_line(self, session=None, move=None):
        def _flatten_tax_and_children(taxes, group_done=None):
            children = self.env['account.tax']
            if group_done is None:
                group_done = set()
            for tax in taxes.filtered(lambda t: t.amount_type == 'group'):
                if tax.id not in group_done:
                    group_done.add(tax.id)
                    children |= _flatten_tax_and_children(tax.children_tax_ids, group_done)
            return taxes + children

        # Tricky, via the workflow, we only have one id in the ids variable
        """Create a account move line of order grouped by products or not."""
        IrProperty = self.env['ir.property']
        ResPartner = self.env['res.partner']

        if session and not all(session.id == order.session_id.id for order in self):
            raise UserError(_('Selected orders do not have the same session!'))

        grouped_data = {}
        have_to_group_by = session and session.config_id.group_by or False
        rounding_method = session and session.config_id.company_id.tax_calculation_rounding_method

        def add_anglosaxon_lines(grouped_data):
            Product = self.env['product.product']
            Analytic = self.env['account.analytic.account']
            for product_key in list(grouped_data.keys()):
                if product_key[0] == "product":
                    line = grouped_data[product_key][0]
                    product = Product.browse(line['product_id'])
                    # In the SO part, the entries will be inverted by function compute_invoice_totals
                    price_unit = self._get_pos_anglo_saxon_price_unit(product, line['partner_id'], line['quantity'])
                    account_analytic = Analytic.browse(line.get('analytic_account_id'))
                    res = Product._anglo_saxon_sale_move_lines(
                        line['name'], product, product.uom_id, line['quantity'], price_unit,
                        fiscal_position=order.fiscal_position_id,
                        account_analytic=account_analytic)
                    if res:
                        line1, line2 = res
                        line1 = Product._convert_prepared_anglosaxon_line(line1, line['partner_id'])
                        insert_data('counter_part', {
                            'name': line1['name'],
                            'account_id': line1['account_id'],
                            'credit': line1['credit'] or 0.0,
                            'debit': line1['debit'] or 0.0,
                            'partner_id': line1['partner_id']

                        })

                        line2 = Product._convert_prepared_anglosaxon_line(line2, line['partner_id'])
                        insert_data('counter_part', {
                            'name': line2['name'],
                            'account_id': line2['account_id'],
                            'credit': line2['credit'] or 0.0,
                            'debit': line2['debit'] or 0.0,
                            'partner_id': line2['partner_id']
                        })

        document_class_id = False
        for order in self.filtered(lambda o: not o.account_move or o.state == 'paid'):
            if order.document_class_id:
                document_class_id = order.document_class_id

            current_company = order.sale_journal.company_id
            account_def = IrProperty.get(
                'property_account_receivable_id', 'res.partner')
            order_account = order.partner_id.property_account_receivable_id.id or account_def and account_def.id
            partner_id = ResPartner._find_accounting_partner(order.partner_id).id or False
            if move is None:
                # Create an entry for the sale
                journal_id = self.env['ir.config_parameter'].sudo().get_param(
                    'pos.closing.journal_id_%s' % current_company.id, default=order.sale_journal.id)
                move = self._create_account_move(
                    order.session_id.start_at, order.name, int(journal_id), order.company_id.id)

            def insert_data(data_type, values):
                # if have_to_group_by:
                values.update({
                    'move_id': move.id,
                })

                key = self._get_account_move_line_group_data_type_key(data_type, values,
                                                                      {'rounding_method': rounding_method})
                if not key:
                    return

                grouped_data.setdefault(key, [])

                if have_to_group_by:
                    if not grouped_data[key]:
                        grouped_data[key].append(values)
                    else:
                        current_value = grouped_data[key][0]
                        current_value['quantity'] = current_value.get('quantity', 0.0) + values.get('quantity', 0.0)
                        current_value['credit'] = current_value.get('credit', 0.0) + values.get('credit', 0.0)
                        current_value['debit'] = current_value.get('debit', 0.0) + values.get('debit', 0.0)
                        if 'currency_id' in values:
                            current_value['amount_currency'] = current_value.get('amount_currency', 0.0) + values.get(
                                'amount_currency', 0.0)
                        if key[0] == 'tax' and rounding_method == 'round_globally':
                            if current_value['debit'] - current_value['credit'] > 0:
                                current_value['debit'] = current_value['debit'] - current_value['credit']
                                current_value['credit'] = 0
                            else:
                                current_value['credit'] = current_value['credit'] - current_value['debit']
                                current_value['debit'] = 0

                else:
                    grouped_data[key].append(values)

            # because of the weird way the pos order is written, we need to make sure there is at least one line,
            # because just after the 'for' loop there are references to 'line' and 'income_account' variables (that
            # are set inside the for loop)
            # TOFIX: a deep refactoring of this method (and class!) is needed
            # in order to get rid of this stupid hack
            assert order.lines, _('The POS order must have lines when calling this method')
            # Create an move for each order line
            cur = order.pricelist_id.currency_id
            cur_company = order.company_id.currency_id
            amount_cur_company = 0.0
            date_order = order.date_order.date() if order.date_order else fields.Date.today()
            taxes = {}
            Afecto = 0
            Exento = 0
            Taxes = 0
            for line in order.lines:
                if cur != cur_company:
                    amount_subtotal = cur._convert(line.price_subtotal, cur_company, order.company_id, date_order)
                else:
                    amount_subtotal = line.price_subtotal

                # Search for the income account
                if line.product_id.property_account_income_id.id:
                    income_account = line.product_id.property_account_income_id.id
                elif line.product_id.categ_id.property_account_income_categ_id.id:
                    income_account = line.product_id.categ_id.property_account_income_categ_id.id
                else:
                    raise UserError(_('Please define income '
                                      'account for this product: "%s" (id:%d).')
                                    % (line.product_id.name, line.product_id.id))

                name = line.product_id.name
                if line.notice:
                    # add discount reason in move
                    name = name + ' (' + line.notice + ')'

                # Create a move for the line for the order line
                # Just like for invoices, a group of taxes must be present on this base line
                # As well as its children
                base_line_tax_ids = _flatten_tax_and_children(line.tax_ids_after_fiscal_position).filtered(
                    lambda tax: tax.type_tax_use in ['sale', 'none'])
                data = {
                    'name': name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': income_account,
                    'analytic_account_id': self._prepare_analytic_account(line),
                    'credit': ((amount_subtotal > 0) and amount_subtotal) or 0.0,
                    'debit': ((amount_subtotal < 0) and -amount_subtotal) or 0.0,
                    'tax_ids': [(6, 0, base_line_tax_ids.ids)],
                    'partner_id': partner_id
                }

                if cur != cur_company:
                    data['currency_id'] = cur.id
                    data['amount_currency'] = -abs(line.price_subtotal) if data.get('credit') else abs(
                        line.price_subtotal)
                    amount_cur_company += data['credit'] - data['debit']
                insert_data('product', data)

                # Create the tax lines
                line_taxes = line.tax_ids_after_fiscal_position.filtered(
                    lambda t: t.company_id.id == current_company.id)
                line_amount = line.price_unit * (100.0 - line.discount) / 100.0
                line_amount *= line.qty
                line_amount = int(round(line_amount))
                if not line_taxes:
                    Exento += line_amount
                    continue
                for t in line_taxes:
                    taxes.setdefault(t, 0)
                    taxes[t] = line_amount
                    if t.amount > 0:
                        Afecto += amount_subtotal
                    else:
                        Exento += amount_subtotal
                pending_line = line
                for t, value in taxes.items():
                    tax = t.compute_all(value, cur, 1)['taxes'][0]
                    if cur != cur_company:
                        round_tax = False if rounding_method == 'round_globally' else True
                        amount_tax = cur._convert(tax['amount'], cur_company, order.company_id, date_order,
                                                  round=round_tax)
                        # amount_tax = cur.with_context(date=date_order).compute(tax['amount'], cur_company, round=round_tax)
                    else:
                        amount_tax = tax['amount']
                    '''@redondear según moneda base '''
                    amount_tax = int(round(amount_tax))
                    data = {
                        'name': _('Tax') + ' ' + tax['name'],
                        'product_id': line.product_id.id,
                        'quantity': line.qty,
                        'account_id': tax['account_id'] or income_account,
                        'credit': ((amount_tax > 0) and amount_tax) or 0.0,
                        'debit': ((amount_tax < 0) and -amount_tax) or 0.0,
                        'tax_ids': tax['id'],
                        'partner_id': partner_id,
                        'order_id': order.id
                    }
                    if cur != cur_company:
                        data['currency_id'] = cur.id
                        data['amount_currency'] = -abs(tax['amount']) if data.get('credit') else abs(tax['amount'])
                        amount_cur_company += data['credit'] - data['debit']
                    insert_data('tax', data)
                    if t.amount > 0:
                        t_amount = amount_tax
                        Taxes += t_amount
            dif = (order.amount_total - (Exento + Afecto + Taxes))
            if dif != 0:
                insert_data('product', {
                    'name': "DIF %s" % name,
                    'quantity': 1 if dif > 0 else -1,
                    'product_id': pending_line.product_id.id,
                    'account_id': income_account,
                    'analytic_account_id': self._prepare_analytic_account(line),
                    'credit': ((dif > 0) and dif) or 0.0,
                    'debit': ((dif < 0) and -dif) or 0.0,
                    'tax_ids': [(6, 0, pending_line.tax_ids_after_fiscal_position.ids)],
                    'partner_id': partner_id
                })
            # @TODO testear si esto ya repara los problemas de redondeo original de odoo
            # round tax lines per order
            '''if rounding_method == 'round_globally':
                for group_key, group_value in grouped_data.items():
                    if group_key[0] == 'tax':
                        for line in group_value:
                            line['credit'] = cur_company.round(line['credit'])
                            line['debit'] = cur_company.round(line['debit'])
                            if line.get('currency_id'):
                                line['amount_currency'] = cur.round(line.get('amount_currency', 0.0))
            '''
            # counterpart
            if cur != cur_company:
                # 'amount_cur_company' contains the sum of the AML converted in the company
                # currency. This makes the logic consistent with 'compute_invoice_totals' from
                # 'account.invoice'. It ensures that the counterpart line is the same amount than
                # the sum of the product and taxes lines.
                amount_total = amount_cur_company
            else:
                amount_total = order.amount_total
            data = {
                'name': _("Trade Receivables"),  # order.name,
                'account_id': order_account,
                'credit': ((amount_total < 0) and -amount_total) or 0.0,
                'debit': ((amount_total > 0) and amount_total) or 0.0,
                'partner_id': partner_id
            }
            if cur != cur_company:
                data['currency_id'] = cur.id
                data['amount_currency'] = -abs(order.amount_total) if data.get('credit') else abs(order.amount_total)
            insert_data('counter_part', data)

            # order.write({'state': 'done', 'account_move': move.id})
        if self and order.company_id.anglo_saxon_accounting:
            add_anglosaxon_lines(grouped_data)

        all_lines = []
        for group_key, group_data in grouped_data.items():
            for value in group_data:
                all_lines.append((0, 0, value), )
        if move:  # In case no order was changed
            move.sudo().write({
                'lines': all_lines,
                'document_class_id': (document_class_id.id if document_class_id else False),
            })
            move.sudo().post()
        return True

    # @api.multi
    def action_pos_order_paid(self):
        if self._is_pos_order_paid():
            if self.sequence_id and self.document_class_id and not self.sii_message:
                if (not self.sii_document_number or self.sii_document_number == 0) and not self.signature:
                    self.sii_document_number = self.sequence_id.next_by_id()
                if not self.l10n_cl_sii_send_file:
                    self._timbrar()
                if not self.sii_message or not self.sii_result == 'Aceptado':
                    self.do_validate()
        return super(posorder, self).action_pos_order_paid()

    """@api.depends('lines.price_subtotal_incl', 'lines.discount')
    def _compute_amount_all(self):
        for order in self:
            order.amount_paid = order.amount_return = order.amount_tax = 0.0
            currency = order.pricelist_id.currency_id
            order.amount_paid = sum(payment.amount for payment in order.statement_ids)
            order.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in order.statement_ids)
            order.amount_tax = currency.round(
                sum(self._amount_line_tax(line, order.fiscal_position_id) for line in order.lines))
            amount_total = currency.round(sum(line.price_subtotal_incl for line in order.lines))
            order.amount_total = amount_total
    """
    # @api.multi
    def exento(self):
        exento = 0
        for l in self.lines:
            if l.tax_ids_after_fiscal_position.amount == 0:
                exento += l.price_subtotal
        return exento if exento > 0 else (exento * -1)

    # @api.multi
    def print_nc(self):
        """ Print NC
        """
        return self.env.ref('l10n_cl_dte_point_of_sale.action_report_pos_boleta_ticket').report_action(self)

    # @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        report_string = "%s %s" % (self.document_class_id.name, self.sii_document_number)
        return report_string

    # @api.multi
    def get_invoice(self):
        return self.invoice_id


class Referencias(models.Model):
    _name = 'pos.order.referencias'
    _description = ""

    origen = fields.Char(
        string="Origin",
    )
    sii_referencia_TpoDocRef = fields.Many2one(
        'l10n_latam.document.type',
        string="SII Reference Document Type",
    )
    sii_referencia_CodRef = fields.Selection(
        [
            ('1', 'Anula Documento de Referencia'),
            ('2', 'Corrige texto Documento Referencia'),
            ('3', 'Corrige montos')
        ],
        string="SII Reference Code",
    )
    motivo = fields.Char(
        string="Motivo",
    )
    order_id = fields.Many2one(
        'pos.order',
        ondelete='cascade',
        index=True,
        copy=False,
        string="Documento",
    )
    fecha_documento = fields.Date(
        string="Fecha Documento",
        required=True,
    )
