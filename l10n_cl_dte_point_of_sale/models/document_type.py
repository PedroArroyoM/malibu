# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from lxml import etree
from lxml.etree import Element, SubElement
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
import pytz
import collections
import logging

_logger = logging.getLogger(__name__)


class L10nLatamDocumentType(models.Model):

    _inherit = 'l10n_latam.document.type'


    def es_boleta(self):
        if int(self.code) in [35, 38, 39, 41, 70, 71]:
            return True
        return False