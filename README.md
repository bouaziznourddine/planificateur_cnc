# Planificateur CNC Complet v2.0

Module Odoo COMPLET généré automatiquement le 14/11/2025 à 15:05

## Contenu du Module

### 12 Modèles Complets
1. **Planificateur CNC** - Scénarios de planification avec AG intégré
2. **Ordres de Fabrication** - Gestion complète des OF
3. **Blocs de Production** - Regroupement optimal des OF
4. **Machines CNC** - Configuration des machines
5. **Types de Pièces** - Catalogue de pièces
6. **Opérations** - Opérations d'usinage
7. **Outils** - Outils de coupe
8. **Palettes** - Supports de fixation
9. **Montages** - Systèmes de fixation
10. **Opérateurs** - Gestion des opérateurs
11. **Pièces** - Pièces individuelles
12. **Timeline** - Planning détaillé

### Fonctionnalités
- ✅ Algorithme génétique d'optimisation
- ✅ Diagrammes de Gantt interactifs
- ✅ Graphiques de convergence
- ✅ Rapports statistiques
- ✅ Export Excel
- ✅ Multi-objectif
- ✅ Configuration complète

## Installation RAPIDE

### 1. Installer dépendances
```bash
pip install plotly pandas numpy openpyxl
```

### 2. Copier les fichiers AG
```bash
cp /chemin/vers/genetic_algorithm_scheduler.py planificateur_cnc_complete/
cp /chemin/vers/gantt_chart_generator.py planificateur_cnc_complete/
```

### 3. Installer dans Odoo
```bash
sudo cp -r planificateur_cnc_complete /opt/odoo/addons/
sudo chown -R odoo:odoo /opt/odoo/addons/planificateur_cnc_complete
sudo systemctl restart odoo
```

### 4. Activer le module
- Apps → Update Apps List
- Rechercher "Planificateur CNC"
- Cliquer sur Install

## Utilisation

### Créer un Planificateur
1. Planification → Planificateurs → Créer
2. Définir les dates et machines
3. Ajouter des OF candidats
4. Configurer les paramètres AG
5. Cliquer sur "Optimiser"

### Consulter les Résultats
- Onglet "Gantt" : Visualisation interactive
- Onglet "Convergence" : Évolution de l'AG
- Onglet "Statistiques" : Rapport détaillé

## Configuration

### Données de Démo
Le module inclut des données de démo pour tester rapidement.

### Paramètres AG Recommandés
- Population: 100
- Générations: 200
- Croisement: 0.8
- Mutation: 0.2

## Support

Pour toute question:
- Email: nourddine.bouaziz@cesi.fr
- Documentation complète disponible

## Développé par

CESI LINEACT - Projet OPTIMAN
Auteur: Bouaziz Nourddine
Version: 2.0.0
