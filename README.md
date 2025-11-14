# Planificateur CNC Maugars

## Description

Module Odoo de planification et d'ordonnancement pour machines CNC, développé selon les spécifications du rapport d'ordonnancement Maugars v1.0.

## Auteur
- **Bouaziz Nourddine** - Ingénieur Recherche & Innovation, CESI
- Date : 23 octobre 2025

## Fonctionnalités principales

### 1. Gestion des Ordres de Fabrication (OF)
- Création et suivi des OF
- Gestion des types de pièces, opérations et gammes de fabrication
- Suivi des quantités (prévues, chargées, terminées)
- Priorités et dates de livraison

### 2. Optimisation intelligente (fonction `action_optimiser`)

La fonction `action_optimiser` est le cœur du système. Elle implémente un algorithme sophistiqué qui :

#### Étape 1 : Validation des contraintes
Vérifie que tous les OF respectent les contraintes critiques :
- ✓ Disponibilité des outils
- ✓ Type et capacité des palettes
- ✓ Capacité des montages
- ✓ Cohérence des quantités
- ✓ Séquence des opérations

#### Étape 2 : Tri et priorisation
Trie les OF selon l'objectif principal choisi :
- **Minimiser les retards** : Tri par date de livraison (EDD)
- **Maximiser la production** : Tri par quantité décroissante
- **Minimiser le makespan** : Tri par durée croissante (SPT)
- **Minimiser les setups** : Regroupement par type de pièce
- **Équilibrer la charge** : Répartition équilibrée entre machines

#### Étape 3 : Création des blocs de production
Algorithme de création des blocs respectant la contrainte principale :
```
Pour chaque OF trié :
    Si (outils_bloc_courant + outils_OF) ≤ capacité_magasin :
        Ajouter OF au bloc courant
    Sinon :
        Sauvegarder bloc courant
        Créer nouveau bloc avec cet OF
```

**Contrainte clé** : Σ(outils OF) ≤ capacité magasin machine

#### Étape 4 : Affectation des machines
Répartit les blocs entre les deux machines en équilibrant la charge.

### 3. Planification temporelle
- Génération du planning détaillé avec dates de début/fin
- Prise en compte des temps de setup (30 min par défaut)
- Visualisation Timeline
- Calcul des retards par rapport aux dates de livraison

### 4. Export et reporting
- Export Excel complet du planning
- Feuille Timeline : détail de chaque opération
- Feuille Blocs : synthèse des blocs de production
- Statistiques : nombre d'OF, durée totale (makespan), taux d'utilisation

## Contraintes respectées

Le module implémente toutes les contraintes identifiées dans le rapport (Section 3) :

### Contraintes machines et outils
1. Capacité d'outils du bloc ≤ capacité magasin
2. Disponibilité des outils (neufs à chaque bloc)
3. Temps de setup obligatoire au début de chaque bloc

### Contraintes de production
4. Séquence d'opérations (OP1 puis OP2)
5. Non-préemption des opérations
6. Capacité montage respectée

### Contraintes temporelles
7. Objectif de date de livraison
8. Durées des opérations prises en compte

### Contraintes humaines
9. Disponibilité opérateurs
10. Horaires de travail

### Contraintes d'affectation
11. Unicité machine par OF
12. Affectation palette unique
13. Cohérence des états

## Installation

1. Copier le dossier `planificateur_cnc` dans le répertoire des addons Odoo
2. Mettre à jour la liste des applications
3. Installer le module "Planificateur CNC Maugars"

## Utilisation

### 1. Configuration initiale

#### a) Créer les machines
Menu : Configuration → Machines CNC
- Créer Machine 1 et Machine 2
- Définir la capacité du magasin d'outils (ex: 40 outils)

#### b) Créer les types de pièces
Menu : Configuration → Types de Pièces
- Définir les opérations (OP1, OP2)
- Spécifier le type de palette (S ou B)
- Associer un montage
- Nombre d'outils total

#### c) Créer les opérations
Menu : Configuration → Opérations
- Code opération (OP10, OP20, etc.)
- Temps standard
- Outils nécessaires

### 2. Créer des Ordres de Fabrication

Menu : Planification → Ordres de Fabrication → Créer

Renseigner :
- Numéro OF
- Type de pièce
- Quantité
- Date de livraison souhaitée
- Priorité

Confirmer l'OF pour le rendre disponible pour planification.

### 3. Utiliser le Planificateur CNC

Menu : Planification → Planificateur CNC → Créer

#### Étape 1 : Configuration du scénario
- Nom du scénario
- Horizon de planification (date début et fin)
- Sélectionner Machine 1 et Machine 2
- Choisir l'objectif principal (ex: Minimiser les retards)
- Définir le temps de setup (par défaut 30 min)

#### Étape 2 : Sélectionner les OF candidats
- Onglet "OF Candidats"
- Ajouter les OF à planifier
- Cliquer sur "Sélectionner OF" si nécessaire

#### Étape 3 : Optimiser
- Cliquer sur le bouton "Optimiser"
- L'algorithme crée les blocs de production optimaux
- Consulter l'onglet "OF Sélectionnés" pour voir le résultat
- Consulter l'onglet "Blocs de Production" pour voir les blocs créés

#### Étape 4 : Générer le planning
- Cliquer sur "Générer Planning"
- Le système calcule les dates de début et fin pour chaque OF
- Consulter l'onglet "Timeline" pour voir le planning détaillé

#### Étape 5 : Exporter
- Cliquer sur "Exporter Excel"
- Télécharger le fichier Excel complet
- Onglet "Export Excel" pour récupérer le fichier

## Modèles de données

### Entités principales

1. **planificateur.cnc** : Scénario de planification
2. **ordre.fabrication** : Ordre de fabrication
3. **bloc.production** : Bloc de production (regroupement d'OF)
4. **piece.type** : Type de pièce
5. **operation.fabrication** : Opération d'usinage
6. **outil.fabrication** : Outil de coupe
7. **palette.fabrication** : Support de pièces
8. **montage.piece** : Système de fixation
9. **machine.cnc** : Machine CNC
10. **operateur.production** : Opérateur
11. **piece.fabrication** : Pièce individuelle
12. **planning.timeline** : Entrée de planning

## Architecture technique

### Algorithme d'optimisation

La fonction `action_optimiser()` dans le modèle `planificateur.cnc` implémente :

```python
def action_optimiser(self):
    # 1. Validation des contraintes
    self._valider_contraintes_of()
    
    # 2. Tri et priorisation
    of_tries = self._trier_of_par_priorite()
    
    # 3. Création des blocs
    blocs_optimises = self._creer_blocs_production(of_tries)
    
    # 4. Affectation machines
    self._affecter_machines_aux_blocs(blocs_optimises)
    
    # 5. Enregistrement
    self.of_selectionne_ids = of_tries
    self.state = 'optimized'
```

### Contraintes validées automatiquement

Le module utilise des contraintes Odoo (`@api.constrains`) pour valider :
- Capacité outils par bloc
- Cohérence des quantités
- Capacité montage
- Dates d'horizon

## Support et contact

Pour toute question ou suggestion d'amélioration :
- Email : nourddine.bouaziz@cesi.fr
- Organisation : CESI

## Licence

Ce module est développé dans le cadre d'un projet de recherche CESI.

## Historique des versions

### Version 1.0 (2025-10-23)
- Implémentation complète du rapport d'ordonnancement Maugars
- Fonction d'optimisation avec création de blocs
- Respect de toutes les contraintes identifiées
- Export Excel
- Documentation complète

## Références

- Rapport d'ordonnancement Maugars v1.0 (23 octobre 2025)
- Documentation Odoo 17
- Théorie de l'ordonnancement et flow-shop scheduling
