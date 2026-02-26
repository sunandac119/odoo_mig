{
    'name': 'POS Manager Validation Logger',
    'version': '14.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Log manager password validation actions in POS',
    'author': 'Custom',
    'depends': ['point_of_sale', 'pos_manager_validation_mac5'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'qweb': [],
    'assets': {
        'point_of_sale.assets': [
            'pos_manager_validation_logger/static/src/js/log_manager_action.js',
        ],
    },
    'installable': True,
    'application': False,
}
