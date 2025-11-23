# 🔄 Modification: Ordonnancement au Niveau des Pièces

## 📋 Résumé
L'algorithme génétique ordonnance maintenant **les pièces individuelles** au lieu des Ordres de Fabrication complets.

## 🎯 Motivation
**Avant**: Un OF de 100 pièces = 1 tâche unique (toutes les pièces doivent être produites ensemble)
- ❌ Manque de flexibilité
- ❌ Impossible d'intercaler différents OF
- ❌ Mauvaise optimisation pour petites séries urgentes

**Après**: Un OF de 100 pièces = 100 tâches individuelles (au niveau pièce)
- ✅ Meilleure granularité d'ordonnancement  
- ✅ Intercalation possible entre OF
- ✅ Priorités respectées au niveau pièce
- ✅ Production optimisée pour séries urgentes

## 🔧 Modifications Techniques

### 1. Format des Tâches
- **Avant**: `(of_id, op_code)` - Tâche au niveau OF
- **Après**: `(of_id, piece_idx, op_code)` - Tâche au niveau pièce

### 2. Fichiers Modifiés

#### `genetic_algorithm_scheduler.py`
- **Classe `Individual`**: Signature mise à jour pour 3-tuple
- **`_create_task_list()`**: Génère une tâche par pièce (boucle sur `quantite`)
- **`_create_blocks()`**: Gère le nouveau format de tâche
- **`_evaluate_fitness()`**: 
  - Calcule la durée d'UNE pièce (`duration / quantite`)
  - Contrainte de précédence OP1→OP2 par pièce (clé: `(of_id, piece_idx)`)
- **`create_gantt_chart_data()`**: 
  - Format de tâche Gantt: `"OF-00001-P5 OP1"` (pièce 5)
  - Ajout `piece_idx` dans les données

#### `planificateur.py`
- **`_apply_solution()`**:
  - Extrait `(of_id, piece_idx, op_code)` des tâches
  - Calcule durée pièce unitaire pour les blocs
  - Parse l'op_code depuis le nom de tâche Gantt
- **`write()`**: Utilise `.get('machine_balance', 0)` pour éviter KeyError

## 📊 Impact sur les Résultats

### Granularité
- **Avant**: 220 OF avec 2 opérations = ~440 tâches
- **Après**: 220 OF × quantité moyenne (50 pièces) × 2 ops = **~22,000 tâches**

### Performance
- ⚠️ Espace de recherche beaucoup plus grand
- ⚠️ Temps d'optimisation potentiellement augmenté
- ✅ Qualité de la solution améliorée

### Visualisation Gantt
- Chaque barre représente maintenant UNE pièce
- Format: `OF-00185-P42 OP1` = OF-00185, Pièce 42, Opération 1
- Facilite le suivi pièce par pièce

## 🚀 Utilisation

### Lancer l'Optimisation
1. Ouvrir le planificateur
2. Cliquer **Valider**
3. Cliquer **🧬 Optimiser**
4. Attendre (temps augmenté pour grandes séries)

### Voir le Gantt
- Les tâches sont affichées pièce par pièce
- Couleur verte = OP1, bleue = OP2
- Possibilité d'intercalation visible

## ⚙️ Paramètres Recommandés

Pour **220 OF** avec quantités variables (5-300 pièces):
```python
population_size = 150      # Augmenté (était 100)
generations = 300          # Augmenté (était 200)
mutation_rate = 0.2        # Inchangé
crossover_rate = 0.8       # Inchangé
```

Pour de **très grandes instances** (>500 OF):
```python
population_size = 200
generations = 500
# OU utiliser heuristique constructive
```

## 📝 Exemple

### Ancien comportement:
```
Bloc 1 Machine M1:
  - OF-00001 (50 pcs) OP1    [████████████████]
  - OF-00001 (50 pcs) OP2    [████████████████]
  - OF-00002 (20 pcs) OP1    [██████]
```

### Nouveau comportement:
```
Bloc 1 Machine M1:
  - OF-00001-P1 OP1   [██]
  - OF-00002-P1 OP1   [█]    ← Intercalation!
  - OF-00001-P2 OP1   [██]
  - OF-00001-P1 OP2   [██]   ← OP2 après OP1 de la même pièce
  - OF-00002-P1 OP2   [█]
  - OF-00001-P3 OP1   [██]
  ...
```

## ✅ Tests Recommandés

1. ✅ Petit jeu de données (5 OF, 10 pièces chacun)
2. ✅ Moyen (50 OF, 20-100 pièces)
3. ✅ Grand (220 OF, 5-300 pièces) ← Dataset actuel
4. ⚠️ Très grand (>500 OF) - À éviter sans optimisations supplémentaires

## 📌 Notes Importantes

- La contrainte de précédence OP1→OP2 est maintenue **PAR PIÈCE**
- Plusieurs pièces du même OF peuvent être en cours simultanément
- Le temps de setup reste au niveau BLOC (pas par pièce)
- Compatible avec les contraintes d'outils et montages

---
**Date**: 2025-11-23  
**Auteur**: Bouaziz Nourddine - CESI LINEACT  
**Projet**: OPTIMAN - Planificateur CNC
