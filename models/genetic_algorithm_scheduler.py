# -*- coding: utf-8 -*-
"""
Algorithme Génétique pour l'ordonnancement de machines CNC - Version Multi-Opérations
Module Planificateur CNC - Maugars
Auteur: Bouaziz Nourddine - CESI LINEACT
Date: Novembre 2025
"""

import random
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Tuple, Dict
import logging

_logger = logging.getLogger(__name__)


class Individual:
    """
    Représentation d'un individu (solution).
    Séquence = Liste d'identifiants de Tâches PIÈCES (OF_ID, PIECE_IDX, OP_CODE)
    """

    def __init__(self, sequence: List[Tuple[int, int, str]], machine_assignments: List[int],
                 block_structure: List[List[Tuple[int, int, str]]]):
        # [(of_id, piece_idx, 'OP1'), (of_id, piece_idx, 'OP2'), ...]
        self.sequence = sequence
        self.machine_assignments = machine_assignments
        self.block_structure = block_structure
        self.fitness = float('inf')
        self.makespan = 0
        self.total_delay = 0
        self.machine_balance = 0
        self.valid = True

    def copy(self):
        return Individual(
            self.sequence.copy(),
            self.machine_assignments.copy(),
            [bloc.copy() for bloc in self.block_structure]
        )


class GeneticAlgorithmScheduler:
    def __init__(self, ofs, machines, setup_time=30, tool_capacity=40,
                 population_size=50, generations=100,
                 crossover_rate=0.8, mutation_rate=0.2,
                 objective='makespan'):

        self.ofs = ofs
        self.machines = machines
        self.setup_time = setup_time
        self.tool_capacity = tool_capacity
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.objective = objective

        # Extraction des données et création des tâches unitaires
        self.of_data = self._extract_of_data()
        self.tasks = self._create_task_list()  # Liste de (of_id, op_code)

        self.best_fitness_history = []
        self.avg_fitness_history = []

    def _extract_of_data(self) -> Dict:
        data = {}
        for of in self.ofs:
            ops_data = {}

            # Déterminer les opérations basées sur le type de pièce et la phase
            # Phase 30/40 = OP1 + OP2 (si existent)
            # Phase 50/60/70 = OP1 seule

            type_piece = of.type_piece_id
            op1 = type_piece.operation_01_id
            op2 = type_piece.operation_02_id

            # OP1
            if op1 and of.phase in ['30', '40', '50', '60', '70']:
                ops_data['OP1'] = {
                    'id': op1.id,
                    'duration': op1.temps_standard * of.quantite,
                    # Simplification: liste des qté
                    'tools': op1.outil_ids.mapped('quantite_requise'),
                    'tool_ids': op1.outil_ids.ids,
                    'montage': type_piece.montage_id.id if type_piece.montage_id else False,
                    'palette': type_piece.palette_type
                }

            # OP2
            if op2 and of.phase in ['30', '40']:
                ops_data['OP2'] = {
                    'id': op2.id,
                    'duration': op2.temps_standard * of.quantite,
                    'tools': op2.outil_ids.mapped('quantite_requise'),
                    'tool_ids': op2.outil_ids.ids,
                    # Souvent même montage mais retourné, ou différent ? Supposons même pour l'instant ou géré par type pièce
                    'montage': type_piece.montage_id.id if type_piece.montage_id else False,
                    'palette': type_piece.palette_type
                }

            data[of.id] = {
                'numero': of.numero_of,
                'quantite': of.quantite,
                'date_livraison': of.date_livraison,
                'priorite': of.priorite,
                'ops': ops_data,
                'type_piece': of.type_piece_id.nom,
                'duree_chargement': of.duree_chargement_machine_min,
                'duree_rotation': of.duree_rotation_table_min
            }
        return data

    def _create_task_list(self) -> List[Tuple[int, int, str]]:
        """
        Créer une liste de tâches au niveau PIÈCE (pas OF)
        Format: (of_id, piece_index, op_code)
        Permet d'ordonnancer pièce par pièce plutôt que OF complet
        """
        tasks = []
        for of_id, data in self.of_data.items():
            quantite = data['quantite']
            for piece_idx in range(quantite):
                if 'OP1' in data['ops']:
                    tasks.append((of_id, piece_idx, 'OP1'))
                if 'OP2' in data['ops']:
                    tasks.append((of_id, piece_idx, 'OP2'))
        return tasks

    def run(self) -> Tuple[Individual, Dict]:
        _logger.info(f"🧬 Démarrage AG Multi-Op: {len(self.tasks)} tâches")

        if not self.tasks:
            _logger.warning(
                "Aucune tâche à planifier (vérifiez les opérations des types de pièces).")
            return Individual([], [], []), {'makespan': 0, 'total_delay': 0, 'machine_balance': 0}

        population = self._initialize_population()
        for ind in population:
            self._evaluate_fitness(ind)

        best_individual = min(population, key=lambda x: x.fitness)

        for gen in range(self.generations):
            parents = self._selection(population)
            offspring = []

            for i in range(0, len(parents), 2):
                if i+1 < len(parents):
                    c1, c2 = self._crossover(parents[i], parents[i+1])
                    self._mutate(c1)
                    self._mutate(c2)
                    offspring.extend([c1, c2])

            for ind in offspring:
                self._evaluate_fitness(ind)

            population = self._replacement(population, offspring)
            current_best = min(population, key=lambda x: x.fitness)
            if current_best.fitness < best_individual.fitness:
                best_individual = current_best.copy()

            self.best_fitness_history.append(best_individual.fitness)
            self.avg_fitness_history.append(
                np.mean([i.fitness for i in population]))

        stats = {
            'final_fitness': best_individual.fitness,
            'makespan': best_individual.makespan,
            'total_delay': best_individual.total_delay,
            'best_fitness_history': self.best_fitness_history,
            'avg_fitness_history': self.avg_fitness_history
        }
        return best_individual, stats

    def _initialize_population(self) -> List[Individual]:
        pop = []
        for _ in range(self.population_size):
            # Séquence aléatoire mais valide topologiquement (OP1 avant OP2 pour un même OF)
            seq = self._generate_valid_sequence()
            blocks = self._create_blocks(seq)
            # Affectation machines aléatoire
            mach = [random.randint(0, len(self.machines)-1)
                    for _ in range(len(blocks))]
            pop.append(Individual(seq, mach, blocks))
        return pop

    def _generate_valid_sequence(self) -> List[Tuple[int, int, str]]:
        # Mélange aléatoire simple pour commencer
        # La contrainte de précédence sera gérée par le décodeur (fitness) ou réparation
        # Ici on fait un shuffle simple des tâches pièces
        seq = self.tasks.copy()
        random.shuffle(seq)
        return seq

    def _create_blocks(self, sequence: List[Tuple[int, int, str]]) -> List[List[Tuple[int, int, str]]]:
        blocks = []
        if not sequence:
            return blocks

        current_block = []
        current_tools = set()
        current_montage = None

        for task in sequence:
            of_id, piece_idx, op_code = task
            op_info = self.of_data[of_id]['ops'][op_code]
            task_tools = set(op_info['tool_ids'])
            task_montage = op_info['montage']

            # Règles de rupture de bloc :
            # 1. Changement de montage
            # 2. Capacité magasin dépassée

            is_compatible = True
            if current_montage is not None and task_montage != current_montage:
                is_compatible = False

            new_tools_union = current_tools.union(task_tools)
            if len(new_tools_union) > self.tool_capacity:
                is_compatible = False

            if is_compatible:
                current_block.append(task)
                current_tools = new_tools_union
                current_montage = task_montage
            else:
                blocks.append(current_block)
                current_block = [task]
                current_tools = task_tools
                current_montage = task_montage

        if current_block:
            blocks.append(current_block)
        return blocks

    def _evaluate_fitness(self, ind: Individual):
        # Simulation de l'ordonnancement
        machine_avail = {i: 0 for i in range(
            len(self.machines))}  # Temps fin machine
        # Temps fin OP1 pour chaque OF (pour contrainte précédence)
        of_op1_end = {}

        total_delay = 0

        for idx, block in enumerate(ind.block_structure):
            m_idx = ind.machine_assignments[idx]

            # Setup
            start_time = machine_avail[m_idx] + self.setup_time

            # Exécution du bloc
            for task in block:
                of_id, piece_idx, op_code = task
                op_info = self.of_data[of_id]['ops'][op_code]
                # Duration pour UNE pièce (pas tout l'OF)
                piece_duration = op_info['duration'] / \
                    self.of_data[of_id]['quantite']
                duration = piece_duration

                # Contrainte de précédence OP1 -> OP2 pour la MÊME PIÈCE
                ready_time = start_time
                if op_code == 'OP2':
                    piece_key = (of_id, piece_idx)
                    op1_end = of_op1_end.get(piece_key, 0)
                    # Ajout temps rotation/transfert
                    ready_time = max(ready_time, op1_end +
                                     self.of_data[of_id]['duree_rotation'])

                # Ajout temps chargement (si début bloc ou changement OF)
                # Simplification: on ajoute chargement à chaque tâche pour l'instant
                ready_time += self.of_data[of_id]['duree_chargement']

                # Machine doit être libre ET pièce prête
                start_task = max(machine_avail[m_idx], ready_time)
                end_task = start_task + duration

                machine_avail[m_idx] = end_task
                start_time = end_task  # Pour la prochaine tâche du bloc

                if op_code == 'OP1':
                    piece_key = (of_id, piece_idx)
                    of_op1_end[piece_key] = end_task

                # Calcul retard (sur la dernière opération de l'OF)
                # Si c'est la dernière opération de l'OF (OP2 ou OP1 si phase unique)
                is_last = False
                if op_code == 'OP2':
                    is_last = True
                elif op_code == 'OP1' and 'OP2' not in self.of_data[of_id]['ops']:
                    is_last = True

                if is_last:
                    due_date = self.of_data[of_id]['date_livraison']
                    if due_date:
                        # Conversion due_date (datetime) en minutes depuis le début (supposons start=0)
                        # Simplification: on compare juste les durées relatives si pas de date absolue
                        # TODO: Gérer dates absolues correctement
                        pass

        makespan = max(machine_avail.values())

        # Pénalité si OP2 planifié avant OP1 (cas impossible avec la logique ci-dessus car on attend ready_time,
        # mais cela peut créer des trous énormes si l'ordre est mauvais dans le chromosome)
        # On ne pénalise pas explicitement car le makespan augmentera naturellement

        ind.makespan = makespan
        ind.fitness = makespan  # + pénalités retards

    def _selection(self, pop):
        # Tournoi
        selected = []
        for _ in range(len(pop)):
            k = min(3, len(pop))
            candidates = random.sample(pop, k)
            selected.append(min(candidates, key=lambda x: x.fitness).copy())
        return selected

    def _crossover(self, p1, p2):
        # OX Crossover sur la séquence
        s1 = self._ox_crossover(p1.sequence, p2.sequence)
        s2 = self._ox_crossover(p2.sequence, p1.sequence)

        # Recréer blocs et machines (aléatoire ou hérité ?)
        # On recrée tout pour simplifier
        b1 = self._create_blocks(s1)
        b2 = self._create_blocks(s2)
        m1 = [random.randint(0, len(self.machines)-1) for _ in range(len(b1))]
        m2 = [random.randint(0, len(self.machines)-1) for _ in range(len(b2))]

        return Individual(s1, m1, b1), Individual(s2, m2, b2)

    def _ox_crossover(self, seq1, seq2):
        size = len(seq1)
        if size < 2:
            return seq1.copy()
        p1, p2 = sorted(random.sample(range(size), 2))
        child = [None]*size
        child[p1:p2] = seq1[p1:p2]

        current = 0
        for item in seq2:
            if item not in child[p1:p2]:
                while child[current] is not None:
                    current += 1
                child[current] = item
        return child

    def _mutate(self, ind):
        if random.random() < self.mutation_rate:
            if len(ind.sequence) < 2:
                return
            # Swap 2 tâches
            idx1, idx2 = random.sample(range(len(ind.sequence)), 2)
            ind.sequence[idx1], ind.sequence[idx2] = ind.sequence[idx2], ind.sequence[idx1]
            # Recalculer blocs
            ind.block_structure = self._create_blocks(ind.sequence)
            # Ajuster machines
            diff = len(ind.block_structure) - len(ind.machine_assignments)
            if diff > 0:
                ind.machine_assignments.extend(
                    [random.randint(0, len(self.machines)-1) for _ in range(diff)])
            else:
                ind.machine_assignments = ind.machine_assignments[:len(
                    ind.block_structure)]

    def _replacement(self, pop, off):
        combined = pop + off
        combined.sort(key=lambda x: x.fitness)
        return combined[:self.population_size]


def create_gantt_chart_data(individual: Individual, of_data: Dict, machines: List,
                            setup_time: int, start_date: datetime) -> List[Dict]:
    # Réimplémentation de la simulation pour générer les données Gantt
    # Similaire à _evaluate_fitness mais retourne les données détaillées
    gantt = []
    machine_avail = {i: start_date for i in range(len(machines))}
    of_op1_end = {}

    for idx, block in enumerate(individual.block_structure):
        m_idx = individual.machine_assignments[idx]
        m_name = machines[m_idx].nom

        # Setup
        start_setup = machine_avail[m_idx]
        end_setup = start_setup + timedelta(minutes=setup_time)
        gantt.append({
            'task': f"Setup Bloc {idx+1}",
            'machine': m_name,
            'start': start_setup,
            'end': end_setup,
            'type': 'setup',
            'color': '#FFA500'
        })

        current_time = end_setup

        for task in block:
            of_id, piece_idx, op_code = task
            op_info = of_data[of_id]['ops'][op_code]
            # Duration pour UNE pièce
            piece_duration = op_info['duration'] / of_data[of_id]['quantite']
            duration = piece_duration

            # Précédence pour la même pièce
            ready_time = current_time
            if op_code == 'OP2':
                piece_key = (of_id, piece_idx)
                op1_end = of_op1_end.get(piece_key, start_date)
                ready_time = max(
                    ready_time, op1_end + timedelta(minutes=of_data[of_id]['duree_rotation']))

            ready_time += timedelta(minutes=of_data[of_id]['duree_chargement'])

            start_task = max(current_time, ready_time)
            end_task = start_task + timedelta(minutes=duration)

            gantt.append({
                'task': f"{of_data[of_id]['numero']}-P{piece_idx+1} {op_code}",
                'machine': m_name,
                'start': start_task,
                'end': end_task,
                'type': 'production',
                'of_id': of_id,
                'piece_idx': piece_idx,
                'color': '#4CAF50' if op_code == 'OP1' else '#2196F3'
            })

            current_time = end_task
            if op_code == 'OP1':
                piece_key = (of_id, piece_idx)
                of_op1_end[piece_key] = end_task

        machine_avail[m_idx] = current_time

    return gantt
