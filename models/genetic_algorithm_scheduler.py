# -*- coding: utf-8 -*-
"""
Algorithme Génétique pour l'ordonnancement de machines CNC
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
    Représentation d'un individu (solution) pour l'algorithme génétique.
    Chromosome = [sequence_of, machine_assignments, block_structure]
    """
    def __init__(self, sequence: List[int], machine_assignments: List[int], 
                 block_structure: List[List[int]]):
        self.sequence = sequence  # Ordre des OF
        self.machine_assignments = machine_assignments  # Machine assignée à chaque bloc
        self.block_structure = block_structure  # Structure des blocs [[OF_ids], [OF_ids], ...]
        self.fitness = float('inf')  # À minimiser (makespan)
        self.makespan = 0
        self.total_delay = 0
        self.machine_balance = 0
        self.valid = True
        
    def copy(self):
        """Créer une copie profonde de l'individu"""
        return Individual(
            self.sequence.copy(),
            self.machine_assignments.copy(),
            [bloc.copy() for bloc in self.block_structure]
        )


class GeneticAlgorithmScheduler:
    """
    Ordonnanceur basé sur un algorithme génétique pour machines CNC.
    Optimise simultanément:
    - La séquence des OF
    - La création des blocs (contrainte capacité outils)
    - L'affectation des blocs aux machines
    """
    
    def __init__(self, ofs, machines, setup_time=30, tool_capacity=40,
                 population_size=100, generations=200, 
                 crossover_rate=0.8, mutation_rate=0.2,
                 objective='makespan'):
        """
        Initialisation de l'algorithme génétique.
        
        Args:
            ofs: Liste des ordres de fabrication (recordset Odoo)
            machines: Liste des machines disponibles (recordset Odoo)
            setup_time: Temps de setup en minutes
            tool_capacity: Capacité du magasin d'outils
            population_size: Taille de la population
            generations: Nombre de générations
            crossover_rate: Taux de croisement
            mutation_rate: Taux de mutation
            objective: Objectif d'optimisation ('makespan', 'delay', 'balance')
        """
        self.ofs = ofs
        self.machines = machines
        self.setup_time = setup_time
        self.tool_capacity = tool_capacity
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.objective = objective
        
        # Données extraites des OF
        self.of_ids = [of.id for of in ofs]
        self.of_data = self._extract_of_data()
        
        # Statistiques
        self.best_fitness_history = []
        self.avg_fitness_history = []
        
    def _extract_of_data(self) -> Dict:
        """Extraire les données nécessaires des OF pour le calcul"""
        data = {}
        for of in self.ofs:
            # total_tools = sum(op.outil_ids.mapped('quantite_requise') for op in of.operation_ids)
            total_tools = sum(sum(op.outil_ids.mapped('quantite_requise')) for op in of.operation_ids)
            total_time = sum(op.temps_standard * of.quantite for op in of.operation_ids)
            
            data[of.id] = {
                'numero': of.numero_of,
                'quantite': of.quantite,
                'date_livraison': of.date_livraison,
                'priorite': of.priorite,
                'total_tools': total_tools,
                'total_time': total_time,  # en minutes
                'operations': [(op.code, op.temps_standard) for op in of.operation_ids],
                'type_piece': of.type_piece_id.nom if of.type_piece_id else '',
            }
        return data
    
    def run(self) -> Tuple[Individual, Dict]:
        """
        Exécuter l'algorithme génétique.
        
        Returns:
            Tuple (meilleur_individu, statistiques)
        """
        _logger.info(f"🧬 Démarrage AG: Population={self.population_size}, Générations={self.generations}")
        
        # Initialisation de la population
        population = self._initialize_population()
        
        # Évaluation initiale
        for individual in population:
            self._evaluate_fitness(individual)
        
        best_individual = min(population, key=lambda x: x.fitness)
        _logger.info(f"Gen 0: Meilleur fitness = {best_individual.fitness:.2f} min (makespan)")
        
        # Évolution
        for generation in range(1, self.generations + 1):
            # Sélection
            parents = self._selection(population)
            
            # Nouvelle génération
            offspring = []
            for i in range(0, len(parents), 2):
                if i + 1 < len(parents):
                    parent1, parent2 = parents[i], parents[i + 1]
                    
                    # Croisement
                    if random.random() < self.crossover_rate:
                        child1, child2 = self._crossover(parent1, parent2)
                    else:
                        child1, child2 = parent1.copy(), parent2.copy()
                    
                    # Mutation
                    if random.random() < self.mutation_rate:
                        self._mutate(child1)
                    if random.random() < self.mutation_rate:
                        self._mutate(child2)
                    
                    offspring.extend([child1, child2])
            
            # Évaluation des enfants
            for individual in offspring:
                self._evaluate_fitness(individual)
            
            # Remplacement (élitisme)
            population = self._replacement(population, offspring)
            
            # Mise à jour du meilleur
            current_best = min(population, key=lambda x: x.fitness)
            if current_best.fitness < best_individual.fitness:
                best_individual = current_best
            
            # Statistiques
            avg_fitness = np.mean([ind.fitness for ind in population])
            self.best_fitness_history.append(best_individual.fitness)
            self.avg_fitness_history.append(avg_fitness)
            
            # Log périodique
            if generation % 20 == 0 or generation == self.generations:
                _logger.info(f"Gen {generation}: Best={best_individual.fitness:.2f}, "
                           f"Avg={avg_fitness:.2f}, Makespan={best_individual.makespan:.2f} min")
        
        stats = {
            'final_fitness': best_individual.fitness,
            'makespan': best_individual.makespan,
            'total_delay': best_individual.total_delay,
            'machine_balance': best_individual.machine_balance,
            'generations': self.generations,
            'best_fitness_history': self.best_fitness_history,
            'avg_fitness_history': self.avg_fitness_history,
        }
        
        _logger.info(f"✅ AG terminé: Meilleur makespan = {best_individual.makespan:.2f} min")
        
        return best_individual, stats
    
    def _initialize_population(self) -> List[Individual]:
        """Créer la population initiale"""
        population = []
        
        for _ in range(self.population_size):
            # Séquence aléatoire des OF
            sequence = self.of_ids.copy()
            random.shuffle(sequence)
            
            # Créer les blocs en respectant la contrainte de capacité outils
            block_structure = self._create_blocks_from_sequence(sequence)
            
            # Affectation aléatoire des blocs aux machines
            machine_assignments = [random.randint(0, len(self.machines) - 1) 
                                  for _ in range(len(block_structure))]
            
            individual = Individual(sequence, machine_assignments, block_structure)
            population.append(individual)
        
        return population
    
    def _create_blocks_from_sequence(self, sequence: List[int]) -> List[List[int]]:
        """
        Créer des blocs à partir d'une séquence en respectant la contrainte de capacité outils.
        """
        blocks = []
        current_block = []
        current_tools = 0
        
        for of_id in sequence:
            of_tools = self.of_data[of_id]['total_tools']
            
            # Vérifier si on peut ajouter l'OF au bloc courant
            if current_tools + of_tools <= self.tool_capacity:
                current_block.append(of_id)
                current_tools += of_tools
            else:
                # Sauvegarder le bloc courant et en créer un nouveau
                if current_block:
                    blocks.append(current_block)
                current_block = [of_id]
                current_tools = of_tools
        
        # Ajouter le dernier bloc
        if current_block:
            blocks.append(current_block)
        
        return blocks
    
    def _evaluate_fitness(self, individual: Individual):
        """
        Calculer la fitness d'un individu.
        Fitness = fonction de: makespan, retards, équilibrage charge
        """
        # Calculer le makespan et les retards
        machine_schedules = {i: [] for i in range(len(self.machines))}
        machine_end_times = {i: 0 for i in range(len(self.machines))}
        total_delay = 0
        
        # Planifier chaque bloc
        for idx, block in enumerate(individual.block_structure):
            machine_id = individual.machine_assignments[idx]
            
            # Temps de début = temps de fin de la machine + setup
            start_time = machine_end_times[machine_id] + self.setup_time
            
            # Temps total du bloc
            block_duration = sum(self.of_data[of_id]['total_time'] for of_id in block)
            
            end_time = start_time + block_duration
            machine_end_times[machine_id] = end_time
            
            machine_schedules[machine_id].append({
                'block_idx': idx,
                'start': start_time,
                'end': end_time,
                'ofs': block
            })
            
            # Calculer les retards
            for of_id in block:
                if self.of_data[of_id]['date_livraison']:
                    # Calculer le retard en minutes (simplifié)
                    delay = max(0, end_time - 0)  # À ajuster avec les vraies dates
                    total_delay += delay
        
        # Makespan = temps de fin maximum
        makespan = max(machine_end_times.values())
        
        # Équilibrage de charge
        machine_loads = list(machine_end_times.values())
        load_variance = np.var(machine_loads) if len(machine_loads) > 1 else 0
        
        # Calcul de la fitness selon l'objectif
        if self.objective == 'makespan':
            fitness = makespan
        elif self.objective == 'delay':
            fitness = total_delay + makespan * 0.1  # Makespan comme objectif secondaire
        elif self.objective == 'balance':
            fitness = load_variance + makespan * 0.1
        else:
            # Multi-objectif: combinaison pondérée
            fitness = makespan + total_delay * 0.1 + load_variance * 0.05
        
        individual.fitness = fitness
        individual.makespan = makespan
        individual.total_delay = total_delay
        individual.machine_balance = load_variance
        individual.valid = True
    
    def _selection(self, population: List[Individual]) -> List[Individual]:
        """
        Sélection par tournoi.
        """
        tournament_size = 3
        selected = []
        
        for _ in range(len(population)):
            tournament = random.sample(population, tournament_size)
            winner = min(tournament, key=lambda x: x.fitness)
            selected.append(winner.copy())
        
        return selected
    
    def _crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """
        Croisement à deux points pour la séquence (Order Crossover - OX).
        """
        # Croisement de la séquence (OX)
        size = len(parent1.sequence)
        point1, point2 = sorted(random.sample(range(size), 2))
        
        # Enfant 1
        child1_seq = [-1] * size
        child1_seq[point1:point2] = parent1.sequence[point1:point2]
        
        # Remplir avec les éléments de parent2 dans l'ordre
        parent2_filtered = [x for x in parent2.sequence if x not in child1_seq]
        idx = 0
        for i in range(size):
            if child1_seq[i] == -1:
                child1_seq[i] = parent2_filtered[idx]
                idx += 1
        
        # Enfant 2 (inverse)
        child2_seq = [-1] * size
        child2_seq[point1:point2] = parent2.sequence[point1:point2]
        parent1_filtered = [x for x in parent1.sequence if x not in child2_seq]
        idx = 0
        for i in range(size):
            if child2_seq[i] == -1:
                child2_seq[i] = parent1_filtered[idx]
                idx += 1
        
        # Recréer les blocs
        child1_blocks = self._create_blocks_from_sequence(child1_seq)
        child2_blocks = self._create_blocks_from_sequence(child2_seq)
        
        # Croisement des affectations machines (uniforme)
        child1_machines = []
        child2_machines = []
        for i in range(max(len(child1_blocks), len(child2_blocks))):
            if random.random() < 0.5:
                m1 = parent1.machine_assignments[min(i, len(parent1.machine_assignments)-1)]
                m2 = parent2.machine_assignments[min(i, len(parent2.machine_assignments)-1)]
            else:
                m2 = parent1.machine_assignments[min(i, len(parent1.machine_assignments)-1)]
                m1 = parent2.machine_assignments[min(i, len(parent2.machine_assignments)-1)]
            
            if i < len(child1_blocks):
                child1_machines.append(m1)
            if i < len(child2_blocks):
                child2_machines.append(m2)
        
        child1 = Individual(child1_seq, child1_machines, child1_blocks)
        child2 = Individual(child2_seq, child2_machines, child2_blocks)
        
        return child1, child2
    
    def _mutate(self, individual: Individual):
        """
        Mutation: échange de deux OF dans la séquence ou changement d'affectation machine.
        """
        mutation_type = random.choice(['swap', 'machine', 'insert'])
        
        if mutation_type == 'swap' and len(individual.sequence) > 1:
            # Échange de deux positions
            i, j = random.sample(range(len(individual.sequence)), 2)
            individual.sequence[i], individual.sequence[j] = individual.sequence[j], individual.sequence[i]
            # Recréer les blocs
            individual.block_structure = self._create_blocks_from_sequence(individual.sequence)
            # Ajuster les affectations machines
            if len(individual.machine_assignments) != len(individual.block_structure):
                diff = len(individual.block_structure) - len(individual.machine_assignments)
                if diff > 0:
                    individual.machine_assignments.extend([random.randint(0, len(self.machines)-1) for _ in range(diff)])
                else:
                    individual.machine_assignments = individual.machine_assignments[:len(individual.block_structure)]
        
        elif mutation_type == 'machine' and individual.machine_assignments:
            # Changer l'affectation d'un bloc
            block_idx = random.randint(0, len(individual.machine_assignments) - 1)
            individual.machine_assignments[block_idx] = random.randint(0, len(self.machines) - 1)
        
        elif mutation_type == 'insert' and len(individual.sequence) > 1:
            # Insertion: retirer un OF et le réinsérer ailleurs
            i = random.randint(0, len(individual.sequence) - 1)
            j = random.randint(0, len(individual.sequence) - 1)
            of = individual.sequence.pop(i)
            individual.sequence.insert(j, of)
            # Recréer les blocs
            individual.block_structure = self._create_blocks_from_sequence(individual.sequence)
            # Ajuster les affectations machines
            if len(individual.machine_assignments) != len(individual.block_structure):
                diff = len(individual.block_structure) - len(individual.machine_assignments)
                if diff > 0:
                    individual.machine_assignments.extend([random.randint(0, len(self.machines)-1) for _ in range(diff)])
                else:
                    individual.machine_assignments = individual.machine_assignments[:len(individual.block_structure)]
    
    def _replacement(self, population: List[Individual], offspring: List[Individual]) -> List[Individual]:
        """
        Remplacement avec élitisme: garder les meilleurs individus.
        """
        # Combiner population et enfants
        combined = population + offspring
        
        # Trier par fitness
        combined.sort(key=lambda x: x.fitness)
        
        # Garder les meilleurs
        return combined[:self.population_size]


def create_gantt_chart_data(individual: Individual, of_data: Dict, machines: List, 
                           setup_time: int, start_date) -> List[Dict]:
    """
    Créer les données pour le diagramme de Gantt à partir de la meilleure solution.
    
    Returns:
        Liste de dictionnaires avec les informations de planification pour chaque opération
    """
    gantt_data = []
    
    # CORRECTION IMPORTANTE: Convertir start_date en datetime si c'est une date
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_datetime = datetime.combine(start_date, datetime.min.time())
    else:
        start_datetime = start_date
    
    # Initialiser avec des datetime, pas des dates
    machine_end_times = {i: start_datetime for i in range(len(machines))}
    
    for idx, block in enumerate(individual.block_structure):
        machine_id = individual.machine_assignments[idx]
        machine_name = machines[machine_id].nom if hasattr(machines[machine_id], 'nom') else f"Machine {machine_id + 1}"
        
        # Setup du bloc
        setup_start = machine_end_times[machine_id]
        setup_end = setup_start + timedelta(minutes=setup_time)
        
        gantt_data.append({
            'task': f'Setup Bloc {idx + 1}',
            'machine': machine_name,
            'start': setup_start,
            'end': setup_end,
            'type': 'setup',
            'color': '#FFA500',
        })
        
        current_time = setup_end
        
        # Opérations des OF dans le bloc
        for of_id in block:
            of_info = of_data[of_id]
            of_duration = of_info['total_time']
            of_end = current_time + timedelta(minutes=of_duration)
            
            gantt_data.append({
                'task': of_info['numero'],
                'machine': machine_name,
                'start': current_time,
                'end': of_end,
                'type': 'production',
                'of_id': of_id,
                'quantite': of_info['quantite'],
                'type_piece': of_info['type_piece'],
                'color': '#4CAF50',
            })
            
            current_time = of_end
        
        machine_end_times[machine_id] = current_time
    
    return gantt_data