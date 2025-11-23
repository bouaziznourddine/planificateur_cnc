# -*- coding: utf-8 -*-
"""
Script Standalone pour Tester l'Algorithme Génétique d'Ordonnancement CNC
Auteur: Bouaziz Nourddine - CESI LINEACT
Date: Novembre 2025

Ce script permet de tester l'algorithme génétique sans dépendance à Odoo.
Il génère des données de test et visualise les résultats.

Usage:
    python test_genetic_algorithm_standalone.py
    
Dépendances:
    pip install numpy plotly pandas
"""

import random
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Tuple, Dict
import plotly.graph_objects as go
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import pandas as pd
import logging
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)


# =============================================================================
# CLASSES MOCK POUR SIMULER LES OBJETS ODOO
# =============================================================================

class MockOutil:
    """Simule un outil de fabrication Odoo"""
    def __init__(self, id, nom, code, quantite_requise=1):
        self.id = id
        self.nom = nom
        self.code = code
        self.quantite_requise = quantite_requise


class MockOperation:
    """Simule une opération de fabrication Odoo"""
    def __init__(self, id, code, nom, temps_standard, outils=None):
        self.id = id
        self.code = code
        self.nom = nom
        self.temps_standard = temps_standard  # en minutes
        self.outil_ids = outils or []
    
    def mapped(self, field):
        """Simule la méthode mapped d'Odoo"""
        if field == 'quantite_requise':
            return [o.quantite_requise for o in self.outil_ids]
        return []


class MockTypePiece:
    """Simule un type de pièce Odoo"""
    def __init__(self, id, nom, code):
        self.id = id
        self.nom = nom
        self.code = code


class MockOrdreFabrication:
    """Simule un ordre de fabrication Odoo"""
    def __init__(self, id, numero_of, quantite, date_livraison, priorite, 
                 type_piece, operations):
        self.id = id
        self.numero_of = numero_of
        self.quantite = quantite
        self.date_livraison = date_livraison
        self.priorite = priorite
        self.type_piece_id = type_piece
        self.operation_ids = operations


class MockMachine:
    """Simule une machine CNC Odoo"""
    def __init__(self, id, nom, code, capacite_magasin=40):
        self.id = id
        self.nom = nom
        self.code = code
        self.capacite_magasin = capacite_magasin


# =============================================================================
# ALGORITHME GÉNÉTIQUE (EXTRAIT DE ODOO)
# =============================================================================

class Individual:
    """
    Représentation d'un individu (solution) pour l'algorithme génétique.
    Chromosome = [sequence_of, machine_assignments, block_structure]
    """
    def __init__(self, sequence: List[int], machine_assignments: List[int], 
                 block_structure: List[List[int]]):
        self.sequence = sequence  # Ordre des OF
        self.machine_assignments = machine_assignments  # Machine assignée à chaque bloc
        self.block_structure = block_structure  # Structure des blocs [[OF_ids], ...]
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
            ofs: Liste des ordres de fabrication
            machines: Liste des machines disponibles
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
            total_tools = sum(
                sum(op.outil_ids.mapped('quantite_requise') if hasattr(op.outil_ids, 'mapped') 
                    else [o.quantite_requise for o in op.outil_ids])
                for op in of.operation_ids
            )
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
            
            # Calculer les retards (simplifié)
            for of_id in block:
                if self.of_data[of_id]['date_livraison']:
                    delay = max(0, end_time - 0)
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
            fitness = total_delay + makespan * 0.1
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
        """Sélection par tournoi."""
        tournament_size = 3
        selected = []
        
        for _ in range(len(population)):
            tournament = random.sample(population, tournament_size)
            winner = min(tournament, key=lambda x: x.fitness)
            selected.append(winner.copy())
        
        return selected
    
    def _crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Croisement à deux points pour la séquence (Order Crossover - OX)."""
        size = len(parent1.sequence)
        point1, point2 = sorted(random.sample(range(size), 2))
        
        # Enfant 1
        child1_seq = [-1] * size
        child1_seq[point1:point2] = parent1.sequence[point1:point2]
        
        parent2_filtered = [x for x in parent2.sequence if x not in child1_seq]
        idx = 0
        for i in range(size):
            if child1_seq[i] == -1:
                child1_seq[i] = parent2_filtered[idx]
                idx += 1
        
        # Enfant 2
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
        
        # Croisement des affectations machines
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
        """Mutation: échange, changement machine, ou insertion."""
        mutation_type = random.choice(['swap', 'machine', 'insert'])
        
        if mutation_type == 'swap' and len(individual.sequence) > 1:
            i, j = random.sample(range(len(individual.sequence)), 2)
            individual.sequence[i], individual.sequence[j] = individual.sequence[j], individual.sequence[i]
            individual.block_structure = self._create_blocks_from_sequence(individual.sequence)
            self._adjust_machine_assignments(individual)
        
        elif mutation_type == 'machine' and individual.machine_assignments:
            block_idx = random.randint(0, len(individual.machine_assignments) - 1)
            individual.machine_assignments[block_idx] = random.randint(0, len(self.machines) - 1)
        
        elif mutation_type == 'insert' and len(individual.sequence) > 1:
            i = random.randint(0, len(individual.sequence) - 1)
            j = random.randint(0, len(individual.sequence) - 1)
            of = individual.sequence.pop(i)
            individual.sequence.insert(j, of)
            individual.block_structure = self._create_blocks_from_sequence(individual.sequence)
            self._adjust_machine_assignments(individual)
    
    def _adjust_machine_assignments(self, individual: Individual):
        """Ajuster les affectations machines après modification de la structure."""
        if len(individual.machine_assignments) != len(individual.block_structure):
            diff = len(individual.block_structure) - len(individual.machine_assignments)
            if diff > 0:
                individual.machine_assignments.extend(
                    [random.randint(0, len(self.machines)-1) for _ in range(diff)]
                )
            else:
                individual.machine_assignments = individual.machine_assignments[:len(individual.block_structure)]
    
    def _replacement(self, population: List[Individual], offspring: List[Individual]) -> List[Individual]:
        """Remplacement avec élitisme."""
        combined = population + offspring
        combined.sort(key=lambda x: x.fitness)
        return combined[:self.population_size]


# =============================================================================
# GÉNÉRATION DES DONNÉES DE GANTT
# =============================================================================

def create_gantt_chart_data(individual: Individual, of_data: Dict, machines: List, 
                           setup_time: int, start_date) -> List[Dict]:
    """
    Créer les données pour le diagramme de Gantt à partir de la meilleure solution.
    """
    gantt_data = []
    machine_end_times = {i: start_date for i in range(len(machines))}
    
    for idx, block in enumerate(individual.block_structure):
        machine_id = individual.machine_assignments[idx]
        machine_name = machines[machine_id].nom
        
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


# =============================================================================
# VISUALISATION
# =============================================================================

def create_gantt_figure(gantt_data: List[Dict], title: str) -> go.Figure:
    """Créer un diagramme de Gantt interactif avec Plotly."""
    fig = go.Figure()
    
    machines = sorted(set(item['machine'] for item in gantt_data))
    
    for item in gantt_data:
        duration_hours = (item['end'] - item['start']).total_seconds() / 3600
        if duration_hours == 0:
            duration_hours = 0.5
        
        color = '#FFA500' if item.get('type') == 'setup' else item.get('color', '#4CAF50')
        
        hover_text = f"<b>{item['task']}</b><br>"
        hover_text += f"Machine: {item['machine']}<br>"
        hover_text += f"Début: {item['start'].strftime('%d/%m/%Y %H:%M')}<br>"
        hover_text += f"Fin: {item['end'].strftime('%d/%m/%Y %H:%M')}<br>"
        hover_text += f"Durée: {duration_hours:.2f} h<br>"
        
        if item.get('type') != 'setup':
            hover_text += f"Type: Production<br>"
            if item.get('type_piece'):
                hover_text += f"Pièce: {item['type_piece']}<br>"
            if item.get('quantite'):
                hover_text += f"Quantité: {item['quantite']}<br>"
        else:
            hover_text += "Type: Setup<br>"
        
        fig.add_trace(go.Bar(
            x=[duration_hours * 3600000],
            y=[item['machine']],
            orientation='h',
            name=item['task'],
            base=item['start'],
            marker=dict(color=color, line=dict(color='rgb(0,0,0)', width=1)),
            hovertemplate=hover_text + '<extra></extra>',
            showlegend=False,
            width=0.8
        ))
    
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center', font=dict(size=20)),
        xaxis=dict(
            title='Temps',
            showgrid=True,
            gridcolor='LightGray',
            type='date',
            tickformat='%d/%m/%Y\n%H:%M'
        ),
        yaxis=dict(
            title='Machines',
            showgrid=True,
            gridcolor='LightGray',
            categoryorder='array',
            categoryarray=machines
        ),
        barmode='overlay',
        height=max(400, len(machines) * 150),
        hovermode='closest',
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='white',
        font=dict(size=12),
        bargap=0.1
    )
    
    return fig


def create_convergence_figure(best_fitness: List[float], avg_fitness: List[float]) -> go.Figure:
    """Créer un graphique de convergence."""
    fig = go.Figure()
    
    generations = list(range(len(best_fitness)))
    
    fig.add_trace(go.Scatter(
        x=generations,
        y=best_fitness,
        mode='lines',
        name='Meilleure Fitness',
        line=dict(color='#4CAF50', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=generations,
        y=avg_fitness,
        mode='lines',
        name='Fitness Moyenne',
        line=dict(color='#2196F3', width=2, dash='dash')
    ))
    
    fig.update_layout(
        title="Convergence de l'Algorithme Génétique",
        xaxis_title='Génération',
        yaxis_title='Fitness (Makespan en minutes)',
        hovermode='x unified',
        plot_bgcolor='white',
        font=dict(size=12),
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    
    return fig


def create_machine_load_figure(gantt_data: List[Dict], machines: List) -> go.Figure:
    """Créer un graphique de charge des machines."""
    machine_loads = {m.nom: 0 for m in machines}
    
    for item in gantt_data:
        if item.get('type') != 'setup':
            duration = (item['end'] - item['start']).total_seconds() / 60
            machine_loads[item['machine']] += duration
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(machine_loads.keys()),
            y=list(machine_loads.values()),
            marker_color=['#4CAF50', '#2196F3', '#FFA500', '#E91E63'][:len(machines)],
            text=[f"{v:.0f} min" for v in machine_loads.values()],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="Charge par Machine (minutes de production)",
        xaxis_title='Machine',
        yaxis_title='Temps (minutes)',
        plot_bgcolor='white',
        font=dict(size=12)
    )
    
    return fig


# =============================================================================
# GÉNÉRATION DES DONNÉES DE TEST
# =============================================================================

def generate_test_data(num_of=15, num_machines=3, seed=42):
    """
    Générer des données de test réalistes.
    
    Args:
        num_of: Nombre d'ordres de fabrication
        num_machines: Nombre de machines CNC
        seed: Graine pour la reproductibilité
        
    Returns:
        Tuple (liste_of, liste_machines)
    """
    random.seed(seed)
    np.random.seed(seed)
    
    # Créer les machines
    machines = []
    for i in range(num_machines):
        machine = MockMachine(
            id=i + 1,
            nom=f"Machine CNC {i + 1}",
            code=f"M{i + 1}",
            capacite_magasin=40 if i < 2 else 60
        )
        machines.append(machine)
    
    # Créer les types de pièces
    types_pieces = [
        MockTypePiece(1, "Pièce Type A", "PTA"),
        MockTypePiece(2, "Pièce Type B", "PTB"),
        MockTypePiece(3, "Pièce Type C", "PTC"),
        MockTypePiece(4, "Pièce Type D", "PTD"),
    ]
    
    # Créer les outils
    outils = []
    for i in range(10):
        outil = MockOutil(
            id=i + 1,
            nom=f"Outil {i + 1}",
            code=f"T{i + 1:02d}",
            quantite_requise=random.randint(1, 3)
        )
        outils.append(outil)
    
    # Créer les OF
    ofs = []
    base_date = date.today()
    
    for i in range(num_of):
        # Opérations aléatoires
        num_ops = random.randint(2, 5)
        operations = []
        
        for j in range(num_ops):
            # Sélectionner des outils aléatoires
            num_outils = random.randint(1, 3)
            op_outils = random.sample(outils, num_outils)
            
            op = MockOperation(
                id=i * 10 + j + 1,
                code=f"OP{j + 1:02d}",
                nom=f"Opération {j + 1}",
                temps_standard=random.uniform(5, 30),  # 5-30 minutes par pièce
                outils=op_outils
            )
            operations.append(op)
        
        # Créer l'OF
        of = MockOrdreFabrication(
            id=i + 1,
            numero_of=f"OF-{i + 1:05d}",
            quantite=random.randint(1, 20),
            date_livraison=base_date + timedelta(days=random.randint(1, 14)),
            priorite=random.randint(1, 10),
            type_piece=random.choice(types_pieces),
            operations=operations
        )
        ofs.append(of)
    
    return ofs, machines


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main():
    """Fonction principale pour tester l'algorithme."""
    print("=" * 70)
    print("  TEST ALGORITHME GÉNÉTIQUE - ORDONNANCEMENT CNC")
    print("  OPTIMAN Project - CESI LINEACT")
    print("=" * 70)
    print()
    
    # Paramètres de configuration
    NUM_OF = 15
    NUM_MACHINES = 3
    POPULATION_SIZE = 50
    GENERATIONS = 100
    SETUP_TIME = 30  # minutes
    TOOL_CAPACITY = 40
    
    # Générer les données de test
    print("📊 Génération des données de test...")
    ofs, machines = generate_test_data(num_of=NUM_OF, num_machines=NUM_MACHINES, seed=42)
    
    print(f"   - {len(ofs)} ordres de fabrication")
    print(f"   - {len(machines)} machines CNC")
    print()
    
    # Afficher les OF générés
    print("📋 Ordres de fabrication:")
    print("-" * 70)
    total_time = 0
    for of in ofs:
        of_time = sum(op.temps_standard * of.quantite for op in of.operation_ids)
        total_time += of_time
        tools = sum(
            sum([o.quantite_requise for o in op.outil_ids])
            for op in of.operation_ids
        )
        print(f"   {of.numero_of}: Qté={of.quantite:2d}, "
              f"Pièce={of.type_piece_id.nom:15s}, "
              f"Temps={of_time:6.1f} min, "
              f"Outils={tools:2d}, "
              f"Priorité={of.priorite:2d}")
    print("-" * 70)
    print(f"   Temps total de production: {total_time:.1f} min ({total_time/60:.1f} h)")
    print()
    
    # Créer et exécuter l'algorithme génétique
    print("🧬 Configuration de l'Algorithme Génétique:")
    print(f"   - Population: {POPULATION_SIZE}")
    print(f"   - Générations: {GENERATIONS}")
    print(f"   - Temps de setup: {SETUP_TIME} min")
    print(f"   - Capacité outils: {TOOL_CAPACITY}")
    print()
    
    scheduler = GeneticAlgorithmScheduler(
        ofs=ofs,
        machines=machines,
        setup_time=SETUP_TIME,
        tool_capacity=TOOL_CAPACITY,
        population_size=POPULATION_SIZE,
        generations=GENERATIONS,
        crossover_rate=0.85,
        mutation_rate=0.15,
        objective='makespan'
    )
    
    # Exécuter l'optimisation
    best_solution, stats = scheduler.run()
    
    # Afficher les résultats
    print()
    print("=" * 70)
    print("  RÉSULTATS DE L'OPTIMISATION")
    print("=" * 70)
    print()
    print(f"   📈 Makespan: {stats['makespan']:.2f} min ({stats['makespan']/60:.2f} h)")
    print(f"   📉 Fitness finale: {stats['final_fitness']:.2f}")
    print(f"   ⚖️  Variance charge: {stats['machine_balance']:.2f}")
    print(f"   📊 Nombre de blocs: {len(best_solution.block_structure)}")
    print()
    
    # Détails des blocs
    print("📦 Structure des blocs:")
    print("-" * 70)
    for idx, block in enumerate(best_solution.block_structure):
        machine_id = best_solution.machine_assignments[idx]
        machine_name = machines[machine_id].nom
        of_nums = [scheduler.of_data[of_id]['numero'] for of_id in block]
        total_tools = sum(scheduler.of_data[of_id]['total_tools'] for of_id in block)
        total_time = sum(scheduler.of_data[of_id]['total_time'] for of_id in block)
        print(f"   Bloc {idx + 1} ({machine_name}):")
        print(f"      OF: {', '.join(of_nums)}")
        print(f"      Outils: {total_tools}/{TOOL_CAPACITY}, Temps: {total_time:.1f} min")
    print("-" * 70)
    print()
    
    # Générer le diagramme de Gantt
    print("📊 Génération des visualisations...")
    start_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    gantt_data = create_gantt_chart_data(
        best_solution, scheduler.of_data, machines, SETUP_TIME, start_date
    )
    
    # Créer les figures
    gantt_fig = create_gantt_figure(gantt_data, "Planning de Production CNC - Optimisé par AG")
    convergence_fig = create_convergence_figure(
        stats['best_fitness_history'], 
        stats['avg_fitness_history']
    )
    machine_load_fig = create_machine_load_figure(gantt_data, machines)
    
    # Sauvegarder en HTML
    gantt_fig.write_html("gantt_chart.html")
    # convergence_fig.write_html("convergence.html")
    # machine_load_fig.write_html("machine_load.html")
    
    print()
    print("✅ Fichiers générés:")
    print("   - gantt_chart.html     (Diagramme de Gantt)")
    print("   - convergence.html     (Courbe de convergence)")
    print("   - machine_load.html    (Charge des machines)")
    print()
    
    # Créer un rapport combiné
    combined_fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Convergence de l'AG",
            "Charge par Machine",
            "", ""
        ),
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy", "colspan": 2}, None]
        ],
        row_heights=[0.4, 0.6],
        vertical_spacing=0.15
    )
    
    # Ajouter convergence
    combined_fig.add_trace(
        go.Scatter(
            x=list(range(len(stats['best_fitness_history']))),
            y=stats['best_fitness_history'],
            name='Meilleure Fitness',
            line=dict(color='#4CAF50')
        ),
        row=1, col=1
    )
    combined_fig.add_trace(
        go.Scatter(
            x=list(range(len(stats['avg_fitness_history']))),
            y=stats['avg_fitness_history'],
            name='Fitness Moyenne',
            line=dict(color='#2196F3', dash='dash')
        ),
        row=1, col=1
    )
    
    # Ajouter charge machines
    machine_loads = {m.nom: 0 for m in machines}
    for item in gantt_data:
        if item.get('type') != 'setup':
            duration = (item['end'] - item['start']).total_seconds() / 60
            machine_loads[item['machine']] += duration
    
    combined_fig.add_trace(
        go.Bar(
            x=list(machine_loads.keys()),
            y=list(machine_loads.values()),
            marker_color=['#4CAF50', '#2196F3', '#FFA500'][:len(machines)],
            showlegend=False
        ),
        row=1, col=2
    )
    
    combined_fig.update_layout(
        title_text="Rapport d'Optimisation - Algorithme Génétique CNC",
        height=800,
        showlegend=True
    )
    
    combined_fig.write_html("rapport_complet.html")
    print("   - rapport_complet.html (Rapport combiné)")
    print()
    
    # Afficher les statistiques finales
    print("=" * 70)
    print("  STATISTIQUES FINALES")
    print("=" * 70)
    
    # Calculer utilisation
    machine_loads_list = list(machine_loads.values())
    max_load = max(machine_loads_list)
    utilizations = [(load / max_load * 100) if max_load > 0 else 0 for load in machine_loads_list]
    
    print()
    print("   Utilisation des machines:")
    for i, machine in enumerate(machines):
        print(f"      {machine.nom}: {machine_loads_list[i]:.1f} min ({utilizations[i]:.1f}%)")
    
    print()
    print(f"   Amélioration: {((stats['best_fitness_history'][0] - stats['final_fitness']) / stats['best_fitness_history'][0] * 100):.1f}%")
    print()
    print("=" * 70)
    print("  FIN DU TEST")
    print("=" * 70)
    
    return best_solution, stats, gantt_data


if __name__ == "__main__":
    best_solution, stats, gantt_data = main()