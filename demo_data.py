# -*- coding: utf-8 -*-

"""
Données de démonstration pour le module Planificateur CNC Maugars

Ce fichier contient des données de test pour illustrer le fonctionnement du module.
"""

# MACHINES CNC
machines_data = [
    {
        'name': 'Machine 1',
        'type_machine': 'CNC',
        'cap_outil': 40,
        'has_rotary': True,
        'state': 'available'
    },
    {
        'name': 'Machine 2',
        'type_machine': 'CNC',
        'cap_outil': 40,
        'has_rotary': False,
        'state': 'available'
    }
]

# OPÉRATIONS
operations_data = [
    {
        'name': 'OP10',
        'description': 'Perçage',
        'temps_standard_min': 15.0,
        'nb_outils': 5
    },
    {
        'name': 'OP20',
        'description': 'Fraisage',
        'temps_standard_min': 25.0,
        'nb_outils': 8
    },
    {
        'name': 'OP30',
        'description': 'Alésage',
        'temps_standard_min': 12.0,
        'nb_outils': 3
    }
]

# TYPES DE PIÈCES
piece_types_data = [
    {
        'name': 'PIECE_A',
        'palette_type': 'S',
        'operation_01': 'OP10',
        'operation_02': 'OP20',
        'nb_outils_total': 13  # 5 + 8
    },
    {
        'name': 'PIECE_B',
        'palette_type': 'B',
        'operation_01': 'OP10',
        'operation_02': 'OP30',
        'nb_outils_total': 8  # 5 + 3
    },
    {
        'name': 'PIECE_C',
        'palette_type': 'S',
        'operation_01': 'OP20',
        'operation_02': None,
        'nb_outils_total': 8  # 8 seulement
    }
]

# ORDRES DE FABRICATION (Exemples)
of_data = [
    {
        'name': 'OF001',
        'piece_type': 'PIECE_A',
        'quantite': 50,
        'date_planifiee_livraison': '2025-11-15 14:00:00',
        'priority': '2',
        'duree_chargement_machine_min': 5.0,
        'duree_usinage_min': 15.0,
        'duree_rotation_table_min': 2.0,
        'nb_pieces_par_palettes': 2,
        'qty_montage_maxi': 4,
        'qty_piece_montage': 2
    },
    {
        'name': 'OF002',
        'piece_type': 'PIECE_B',
        'quantite': 30,
        'date_planifiee_livraison': '2025-11-12 10:00:00',
        'priority': '3',
        'duree_chargement_machine_min': 5.0,
        'duree_usinage_min': 20.0,
        'duree_rotation_table_min': 2.0,
        'nb_pieces_par_palettes': 1,
        'qty_montage_maxi': 2,
        'qty_piece_montage': 1
    },
    {
        'name': 'OF003',
        'piece_type': 'PIECE_C',
        'quantite': 100,
        'date_planifiee_livraison': '2025-11-20 16:00:00',
        'priority': '1',
        'duree_chargement_machine_min': 5.0,
        'duree_usinage_min': 10.0,
        'duree_rotation_table_min': 0.0,
        'nb_pieces_par_palettes': 4,
        'qty_montage_maxi': 6,
        'qty_piece_montage': 4
    },
    {
        'name': 'OF004',
        'piece_type': 'PIECE_A',
        'quantite': 25,
        'date_planifiee_livraison': '2025-11-10 09:00:00',
        'priority': '3',
        'duree_chargement_machine_min': 5.0,
        'duree_usinage_min': 15.0,
        'duree_rotation_table_min': 2.0,
        'nb_pieces_par_palettes': 2,
        'qty_montage_maxi': 4,
        'qty_piece_montage': 2
    }
]

# SCÉNARIO DE PLANIFICATION EXEMPLE
scenario_data = {
    'name': 'Planning Semaine 46',
    'date_debut_horizon': '2025-11-10 08:00:00',
    'date_fin_horizon': '2025-11-17 18:00:00',
    'objectif_principal': 'minimiser_retard',
    'temps_setup_bloc': 30.0,
    'machine_1': 'Machine 1',
    'machine_2': 'Machine 2'
}

# ATTENDUS APRÈS OPTIMISATION
"""
Avec les données ci-dessus et l'objectif "minimiser_retard", 
l'algorithme devrait :

1. Trier les OF par date de livraison :
   - OF004 (10 nov) - PIECE_A - 13 outils
   - OF002 (12 nov) - PIECE_B - 8 outils
   - OF001 (15 nov) - PIECE_A - 13 outils
   - OF003 (20 nov) - PIECE_C - 8 outils

2. Créer les blocs (capacité 40 outils) :
   
   Bloc 1:
   - OF004 (13 outils) + OF002 (8 outils) + OF001 (13 outils) = 34 outils ✓
   
   Bloc 2:
   - OF003 (8 outils) = 8 outils ✓

3. Affecter aux machines :
   - Bloc 1 → Machine 1 (charge: setup 30 min + durées OF)
   - Bloc 2 → Machine 2 (charge: setup 30 min + durées OF)

4. Générer le planning avec dates précises pour chaque OF

RÉSULTAT ATTENDU :
- 4 OF optimisés
- 2 blocs de production
- Durée totale (makespan) : environ 2-3 heures
- Tous les OF dans les délais ou retard minimal
"""

# INSTRUCTIONS D'UTILISATION
"""
Pour tester le module avec ces données :

1. Installer le module dans Odoo
2. Créer manuellement les machines (Machine 1 et Machine 2)
3. Créer les opérations (OP10, OP20, OP30)
4. Créer les types de pièces (PIECE_A, PIECE_B, PIECE_C)
5. Créer les OF (OF001, OF002, OF003, OF004)
6. Créer un nouveau planificateur avec les paramètres du scenario_data
7. Ajouter les OF comme candidats
8. Cliquer sur "Optimiser"
9. Observer les blocs créés
10. Cliquer sur "Générer Planning"
11. Consulter la timeline
12. Exporter en Excel

POINTS DE VALIDATION :
✓ Les contraintes sont respectées (capacité outils ≤ 40)
✓ Les OF sont triés par date de livraison
✓ Les blocs sont optimisés
✓ Les machines sont équilibrées
✓ Le planning est cohérent
"""
