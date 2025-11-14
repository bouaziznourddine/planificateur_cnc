# -*- coding: utf-8 -*-
{
    'name': 'Planificateur CNC Maugars',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Système d\'ordonnancement et de planification pour machines CNC',
    'description': """
        Module de planification avancée pour l'ordonnancement de production CNC
        ========================================================================
        
        Fonctionnalités principales :
        - Gestion des ordres de fabrication (OF)
        - Optimisation des blocs de production
        - Gestion des contraintes machines et outils
        - Planification avec visualisation Timeline et Gantt
        - Export Excel des plannings
        
        Basé sur les spécifications du rapport d'ordonnancement Maugars v1.0
    """,
    'author': 'CESI - Bouaziz Nourddine',
    'website': 'http://www.cesi.fr',
    'depends': ['base', 'web', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'views/piece_type_views.xml',
        'views/operation_views.xml',
        'views/outil_views.xml',
        'views/palette_views.xml',
        'views/montage_views.xml',
        'views/machine_views.xml',
        'views/operateur_views.xml',
        'views/of_views.xml',
        'views/piece_views.xml',
        'views/planificateur_cnc_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
