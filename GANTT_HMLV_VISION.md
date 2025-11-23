# 📊 Gantt Optimisé pour le Single Piece Flow - HMLV

## 🎯 Vision: De la Logique "Moléculaire" à "Atomique"

### Contexte Théorique

L'évolution vers des systèmes **High-Mix Low-Volume (HMLV)** impose une rupture épistémologique fondamentale dans l'ordonnancement de production:

**Logique Moléculaire (Traditionnelle)**:
- L'OF (Ordre de Fabrication) = unité atomique indivisible
- Regroupement de $Q$ pièces identiques
- Amortissement des coûts de setup
- Stabilité opérationnelle

**Logique Atomique (Lean/HMLV)**:
- La pièce individuelle = unité atomique
- Single Piece Flow (flux pièce à pièce)
- Flexibilité maximale
- Minimisation du WIP

---

## 🔧 Fonctionnalités Implémentées

### 1. Ordonnancement Pièce par Pièce ✅

**Architecture actuelle** (dans `genetic_algorithm_scheduler.py`):

```python
# Format des tâches: (of_id, piece_idx, op_code)
def _create_task_list(self) -> List[Tuple[int, int, str]]:
    tasks = []
    for of_id, data in self.of_data.items():
        quantite = data['quantite']
        for piece_idx in range(quantite):  # ← Granularité pièce!
            if 'OP1' in data['ops']:
                tasks.append((of_id, piece_idx, 'OP1'))
            if 'OP2' in data['ops']:
                tasks.append((of_id, piece_idx, 'OP2'))
    return tasks
```

**Impact**:
- Un OF de 100 pièces × 2 opérations = **200 tâches individuelles**
- Intercalation possible entre OF
- Respect de la précédence OP1→OP2 **par pièce**

---

## 📈 Améliorations Prévues pour le Gantt

### 2. Visualisation Enrichie (À implémenter)

#### A. Codage Couleur par OF

```python
def _generate_of_colors(self) -> dict:
    """
    Palette de couleurs distinctes pour chaque OF
    Permet de visualiser l'intercalation visuellement
    """
    of_ids = set(item.get('of_id') for item in self.gantt_data 
                 if item.get('type') != 'setup')
    
    # Palettes HSL pour différenciation optimale
    colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6', ...]
    
    of_colors = {}
    for idx, of_id in enumerate(sorted(of_ids)):
        of_colors[of_id] = colors[idx % len(colors)]
    
    return of_colors
```

**Résultat visuel**:
```
Machine M1:  [██ OF-001] [█ OF-003] [██ OF-001] [█ OF-002] ...
             Rouge      Bleu      Rouge      Vert
             ↑ Intercalation visible!
```

#### B. Différenciation OP1 / OP2

- **OP1**: Couleur claire du OF
- **OP2**: Couleur assombrie (-30%) du même OF

```python
def _darken_color(hex_color: str, factor=0.7) -> str:
    # RGB manipulation
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}'
```

#### C. Format de Tâche Enrichi

```
"OF-00185-P42 OP1"
    ↑      ↑   ↑
    |      |   Opération
    |      Pièce #42
    Ordre de Fabrication
```

---

### 3. Indicateurs HMLV/Lean (À implémenter)

#### A. Taux d'Intercalation

$$\text{Taux Intercalation} = \frac{\text{Nb transitions entre OF différents}}{\text{Nb total transitions}} \times 100$$

```python
def _calculate_interleaving_rate(self) -> float:
    transitions = 0
    different_of_transitions = 0
    
    for i in range(len(production_tasks) - 1):
        curr_of = production_tasks[i].get('of_id')
        next_of = production_tasks[i+1].get('of_id')
        if curr_of != next_of:
            different_of_transitions += 1
        transitions += 1
    
    return (different_of_transitions / transitions * 100) if transitions > 0 else 0
```

**Interprétation**:
- **0%**: Aucune intercalation (ordonnancement par OF complet)
- **50%**: Intercalation modérée
- **90%+**: Forte intercalation (true piece flow)

#### B. Index de Fragmentation

$$\text{Fragmentation} = \frac{\sum \text{Nb blocs par OF}}{\text{Nb OF total}}$$

```python
def _calculate_fragmentation_index(self) -> float:
    of_blocks = {}
    current_of = None
    
    for task in production_tasks:
        of_id = task.get('of_id')
        if of_id != current_of:
            of_blocks[of_id] = of_blocks.get(of_id, 0) + 1
            current_of = of_id
    
    return sum(of_blocks.values()) / len(of_blocks) if of_blocks else 1
```

**Interprétation**:
- **1.0**: Chaque OF produit en un seul bloc (batch tradicional)
- **2-3**: Fragmentation modérée
- **>5**: Forte fragmentation (HMLV)

#### C. WIP Moyen (Work In Progress)

```python
def _calculate_avg_wip(self) -> float:
    """
    Nombre moyen de pièces en cours de fabrication simultanément
    Indicateur clé du Lean Manufacturing
    """
    time_points = []
    for task in production_tasks:
        time_points.append((task['start'], +1))  # Début pièce
        time_points.append((task['end'], -1))     # Fin pièce
    
    time_points.sort()
    wip_values = []
    current_wip = 0
    
    for time, delta in time_points:
        current_wip += delta
        wip_values.append(current_wip)
    
    return sum(wip_values) / len(wip_values)
```

**Objectif Lean**: Minimiser le WIP → closer to Single Piece Flow

---

### 4. Titre Enrichi du Gantt

```
┌────────────────────────────────────────────────────────────┐
│  Planning de Production CNC - Single Piece Flow            │
│  Taux intercalation: 67.3% | Fragmentation: 2.4 |          │
│  WIP moyen: 12.5 pièces | Makespan: 3456 min (57.6h)       │
└────────────────────────────────────────────────────────────┘
```

---

### 5. Légende OF Dynamique

**Affichage en bas du Gantt**:

```
Légende OF (top 5):
█ OF-00185 (42 pcs)  █ OF-00023 (38 pcs)  █ OF-00156 (35 pcs)
Rouge                Bleu                 Vert
```

---

### 6. Hover Enrichi

```html
<b>OF-00185-P42 OP1</b>
Machine: Machine CNC 1
Début: 23/11/2025 14:30
Fin: 23/11/2025 14:48
Durée: 18 min (0.30 h)

<b>Type: Production</b>
OF: OF-00185
Pièce: #42
Operation: OP1 (Surfaçage)

Contexte:
- Pièce 42/100 de cet OF
- Suivie par: OF-00023-P15 OP1 (intercalation)
```

---

## 📊 Statistiques Complètes

### Rapport Texte (Onglet "Statistiques")

```
================================================================
RAPPORT STATISTIQUE - SINGLE PIECE FLOW
================================================================

MÉTRIQUES HMLV/LEAN:
----------------------------------------------------------------
Taux d'intercalation:     67.3%    ⭐ (haute flexibilité)
Index de fragmentation:   2.4      ⭐ (production mixée)
WIP moyen:                12.5 pcs ⚠️  (réduire si possible)
Temps écoulement pièce:   45.2 min (objectif: minimiser)

PERFORMANCES:
----------------------------------------------------------------
Makespan:                 3456 min (57.6 heures)
Retard total:             0 min
Taux utilisation:         85.3%

MACHINES:
----------------------------------------------------------------
Machine CNC 1:            1850 min, 245 tâches (pièces)
Machine CNC 2:            1606 min, 198 tâches (pièces)

ORDRES DE FABRICATION:
----------------------------------------------------------------
Total OF planifiés:       220 OF
Total pièces:             11,450 pièces
Total setups:             48 changements de série

TRANSITIONS:
----------------------------------------------------------------
Transitions intra-OF:     1,245 (même OF, pièces consécutives)
Transitions inter-OF:     3,567 (changement d'OF)
Ratio inter/intra:        2.86  ⭐ (bonne intercalation)

================================================================
```

---

## 🚀 Mode d'Utilisation

### Paramètres Optimisés pour HMLV

```python
# Dans le planificateur Odoo:
ga_population_size = 150    # Population AG
ga_generations = 300        # Générations
objectif_principal = 'minimize_makespan'

# Pour favoriser l'intercalation:
# → L'AG découvrira naturellement l'intercalation optimale
# → Pas de paramètre spécifique nécessaire
```

### Interprétation des Résultats

**Scénario 1: Faible Intercalation (Taux < 20%)**
- Production quasi batch (traditionnelle)
- OFs produits en séquence complète
- Acceptable pour grandes séries

**Scénario 2: Intercalation Modérée (20-60%)**
- Équilibre batch/flow
- Bonne pour contexte mixte

**Scénario 3: Forte Intercalation (> 60%)**
- True Single Piece Flow
- Optimal pour HMLV
- Maximum de flexibilité

---

## 📝 Prochaines Étapes d'Implémentation

### Phase 1: Métrique de Base ✅
- [x] Ordonnancement pièce par pièce
- [x] Format tâches `(of_id, piece_idx, op_code)`
- [x] Gantt affichant "OF-XXX-PYY OPZ"

### Phase 2: Visualisation Enrichie (En cours)
- [ ] Couleurs par OF
- [ ] Différenciation OP1/OP2
- [ ] Titre avec indicateurs HMLV
- [ ] Légende OF dynamique
- [ ] Hover enrichi

### Phase 3: Analytiques Avancés
- [ ] Calcul automatique des indicateurs HMLV
- [ ] Affichage dans onglet Statistiques
- [ ] Export Excel avec métriques HMLV
- [ ] Graphiques de distribution (WIP, transitions)

### Phase 4: Optimisation Ciblée HMLV
- [ ] Fonction objectif multi-critères
- [ ] Pénalité pour WIP élevé
- [ ] Bonus pour intercalation équilibrée
- [ ] Contraintes de taille de lot min/max par OF

---

## 🎓 Fondements Académiques

### Références

1. **Single Piece Flow**:
   - Womack & Jones (1996): *Lean Thinking*
   - Principe de minimisation du WIP

2. **HMLV Scheduling**:
   - ElMaraghy et al. (2013): *Flexible and reconfigurable manufacturing*
   - Multi-critères pour environnements dynamiques

3. **Lot Splitting**:
   - Potts & Van Wassenhove (1992): *Lot sizing and scheduling*
   - Division optimale des lots pour minimiser makespan

4. **Transition batch → piece**:
   - Rother & Shook (1999): *Learning to See*
   - Value Stream Mapping pour identifier flux

---

**Auteur**: Bouaziz Nourddine - CESI LINEACT  
**Projet**: OPTIMAN - Planificateur CNC  
**Date**: Novembre 2025  
**Version**: 2.1 - Single Piece Flow Enhanced
