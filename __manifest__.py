# -*- coding: utf-8 -*-
{
    'name': 'Planificateur CNC Maugars - Complet v2.0',
    'version': '2.0.0',
    'category': 'Manufacturing',
    'summary': 'Planification CNC complète avec Algorithme Génétique et Gantt',
    'description': '''
Planificateur CNC Complet v2.0
===============================

Module COMPLET avec:
-------------------
* 🧬 Algorithme Génétique intégré
* 📊 Diagramme de Gantt interactif (Plotly)
* 📈 Graphiques de convergence
* 📋 Rapports statistiques détaillés
* 📑 Export Excel complet
* ⚙️ 12 modèles de données
* 🎯 Multi-objectif (makespan, retards, équilibrage)
* 🔧 Configuration complète

Modèles:
--------
* Planificateur CNC (scénarios)
* Ordres de Fabrication (OF)
* Blocs de Production
* Machines CNC
* Types de Pièces
* Opérations de Fabrication
* Outils de Coupe
* Palettes
* Montages
* Opérateurs
* Planning Timeline
* Pièces Individuelles

Fonctionnalités:
---------------
* Création et gestion des OF
* Optimisation par AG avec paramètres configurables
* Respect de toutes les contraintes (outils, machines, séquences)
* Visualisation interactive du planning
* Analyse de performance
* Export multi-formats

Développé par CESI LINEACT - Projet OPTIMAN
    ''',
    'author': 'Bouaziz Nourddine - CESI LINEACT',
    'website': 'https://www.cesi.fr',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mrp'],
    'external_dependencies': {
        'python': ['plotly', 'pandas', 'numpy', 'openpyxl'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/demo_data.xml',
        'views/menu_views.xml',
        'views/planificateur_views.xml',
        'views/ordre_fabrication_views.xml',
        'views/bloc_production_views.xml',
        'views/machine_cnc_views.xml',
        'views/piece_type_views.xml',
        'views/operation_fabrication_views.xml',
        'views/outil_fabrication_views.xml',
        'views/palette_views.xml',
        'views/montage_views.xml',
        'views/operateur_views.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
