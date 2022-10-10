# -*- coding: utf-8 -*-
{
    "name": """Secuencia por CAF\
    """,
    'version': '0.1',
    'category': 'Sales Management',
    'sequence': 12,
    'author': 'Tierranube(Francisco Trejo)',
    'website': 'https://www.tierranube.cl',
    'license': 'AGPL-3',
    'summary': '',
    'description': """
Chile: API and GUI to access Electronic Invoicing webservices for Point of Sale.
""",
    'depends': [
        'point_of_sale',
        'l10n_cl_dte_point_of_sale',
        'sale',
        'account',
        'l10n_cl',
        'l10n_cl_edi',
        'l10n_cl_edi_boletas'
    ],
    'external_dependencies': {
        'python': [
        ]
    },
    'data': [
        'views/caf.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
