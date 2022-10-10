import base64
import collections
import hashlib
import logging
import re
import textwrap
import urllib3
import codecs
import json
from odoo.addons.l10n_cl_edi.models.l10n_cl_edi_util import  l10n_cl_edi_retry

from odoo import _, models, fields

urllib3.disable_warnings()
pool = urllib3.PoolManager(cert_reqs='CERT_NONE')


_logger = logging.getLogger(__name__)

SERVER_URL = {
    'SIITEST': 'https://maullin.sii.cl/DTEWS/',
    'SII': 'https://palena.sii.cl/DTEWS/',
}

CLAIM_URL = {
    'SIITEST': 'https://ws2.sii.cl/WSREGISTRORECLAMODTECERT/registroreclamodteservice',
    'SII': 'https://ws1.sii.cl/WSREGISTRORECLAMODTE/registroreclamodteservice',
}

API_URL = {
    'SIITEST': 'https://apicert.sii.cl/recursos/v1/',
    'SII': 'https://api.sii.cl/recursos/v1/'
}

API_URL_ENVIO = {
    'SIITEST': 'https://pangal.sii.cl/recursos/v1/',
    'SII': 'https://rahue.sii.cl/recursos/v1/'
}

class L10nClEdiUtilMixin(models.AbstractModel):
    _inherit = 'l10n_cl.edi.util'

    def estado_envio(estado,estadistica=False):
        if estado in ["REC"]:
            if estadistica:
                return 'Aceptado'
            return 'Enviado'
        if estado in ["EPR","LOK","EOK"]:
            return "Aceptado"
        elif estado in ["RCT","RCH","LRH","RFR","LRH",
                        "RSC","LNC","FNA","LRF","LRS","106","LRC",
                        "RDC","RCR","RCO","LRP","RCS"]:
            return "Rechazado"
        return "NoEnviado"


    @l10n_cl_edi_retry(logger=_logger)
    def _get_seed_ws(self, mode):
        if 'api_boleta' in self.env.context:
            url = API_URL[mode] + 'boleta.electronica.semilla'
            req = pool.request('GET',url,headers={'Accept': "application/xml"})
            return req.data.decode('UTF-8')
        else:
            return super(L10nClEdiUtilMixin, self)._get_seed_ws(mode)

    @l10n_cl_edi_retry(logger=_logger)
    def _get_token_ws(self, mode, signed_token):
        if 'api_boleta' in self.env.context:
            url = API_URL[mode] + 'boleta.electronica.token'
            req = pool.request('POST',url,body=signed_token,headers={
                'Accept': "application/xml",
                "Content-Type": "application/xml"})
            return req.data.decode('UTF-8')
        else:
            return super(L10nClEdiUtilMixin, self)._get_token_ws(mode, signed_token)

    @l10n_cl_edi_retry(logger=_logger)
    def _get_send_status_ws(self, mode, company_vat, track_id, token):
        if 'api_boleta' in self.env.context:
            rut  = self.company_id.vat
            url = '{0}boleta.electronica.envio/{1}-{2}-{3}'.format(
                API_URL[mode],
                rut[:-2],
                rut[-1],
                track_id
            )
            headers = {
                'Accept': 'application/json',
                'Cookie': 'TOKEN={}'.format(self.token),
            }
            try:
                response = pool.request(
                    'GET',
                    url,
                    headers=headers
                )
                self.sii_message = str(response.data)
                if response.status == 404:
                    return {
                        'status': 'NoEnviado',
                        'detalles': '',
                        'detalle_rep_rech': '',
                        'xml_resp': response.data,
                    }
                resp = json.loads(response.data.decode('ISO-8859-1'))
                return {
                    'status': self.estado_envio(resp.get('estado'),resp.get('estadistica')),
                    'detalles': resp.get('estadistica'),
                    'detalle_rep_rech': resp.get('detalle_rep_rech'),
                    'xml_resp': response.data.decode('ISO-8859-1'),
                }
            except Exception as e:
                return {
                    'status': 'NoEnviado',
                    'xml_resp': str(e),
                }



        else:
            return super(L10nClEdiUtilMixin, self)._get_send_status_ws(mode, company_vat, track_id, token)


    def _send_xml_to_sii(self, mode, company_website, company_vat, file_name, xml_message, digital_signature,
                         post='/cgi_dte/UPL/DTEUpload', api=False):
        """
        The header used here is explicitly stated as is, in SII documentation. See
        http://www.sii.cl/factura_electronica/factura_mercado/envio.pdf
        it says: as mentioned previously, the client program must include in the request header the following.....
        """
        token = self._get_token(mode, digital_signature)
        if token is None:
            self._report_connection_err(_('No response trying to get a token'))
            return False
        url = SERVER_URL[mode].replace('/DTEWS/', '')
        if api:
            url = API_URL_ENVIO[mode]

        headers = {
            'Accept': 'image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, application/vnd.ms-powerpoint, \
    application/ms-excel, application/msword, */*',
            'Accept-Language': 'es-cl',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; Windows NT 5.0; YComp 5.0.2.4)',
            'Referer': '{}'.format(company_website),
            'Connection': 'Keep-Alive',
            'Cache-Control': 'no-cache',
            'Cookie': 'TOKEN={}'.format(token),
        }
        if api:
            headers['Accept'] = 'application/json'
        params = collections.OrderedDict({
            'rutSender': digital_signature.subject_serial_number[:8],
            'dvSender': digital_signature.subject_serial_number[-1],
            'rutCompany': self._l10n_cl_format_vat(company_vat)[:8],
            'dvCompany': self._l10n_cl_format_vat(company_vat)[-1],
            'archivo': (file_name, xml_message, 'text/xml'),
        })
        urllib3.filepost.writer = codecs.lookup('ISO-8859-1')[3]
        multi = urllib3.filepost.encode_multipart_formdata(params)
        headers.update({'Content-Length': '{}'.format(len(multi[0]))})
        try:
            response = pool.request_encode_body('POST', url + post, params, headers)
            _logger.info('Response {0}'.format(response))
        except Exception as error:
            self._report_connection_err(_('Sending DTE to SII failed due to:') + '<br /> %s' % error)
            digital_signature.last_token = False
            return False
        return response.data
        # we tried to use requests. The problem is that we need the Content-Lenght and seems that requests
        # had the ability to send this provided the file is in binary mode, but did not work.
        # response = requests.post(url + post, headers=headers, files=params)
        # if response.status_code != 200:
        #     response.raise_for_status()
        # else:
        #     return response.text
