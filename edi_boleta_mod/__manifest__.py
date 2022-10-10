# -*- coding: utf-8 -*-
{
    "name": """Chile - Electronic Receipt mod""",
    'version': '14.0.1.0.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'Tierra Nube',
    'website': 'http://www.tierranube.cl',
    'depends': ['l10n_cl_edi_boletas'],
    'data': [
        'template/dte_template.xml',
        'template/dd_template.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}