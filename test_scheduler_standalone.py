# -*- coding: utf-8 -*-
"""
Script Standalone pour Tester l'Algorithme Génétique d'Ordonnancement CNC
VERSION FINALE : Logique corrigée + Style Gantt Original
Auteur: Bouaziz Nourddine - CESI LINEACT
"""

import random
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Tuple, Dict
import plotly.graph_objects as go
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)


# =============================================================================
# 1. CLASSES MOCK (CORRIGÉES)
# =============================================================================

class MockOutil:
    def __init__(self, id, nom, code, quantite_requise=1):
        self.id = id
        self.nom = nom
        self.code = code
        self.quantite_requise = quantite_requise


class MockOperation:
    def __init__(self, id, code, nom, temps_standard, outils=None):
        self.id = id
        self.code = code
        self.nom = nom
        self.temps_standard = temps_standard
        self.outil_ids = outils or []

    def mapped(self, field):
        if field == 'quantite_requise':
            return [o.quantite_requise for o in self.outil_ids]
        return []


class MockTypePiece:
    def __init__(self, id, nom, code):
        self.id = id
        self.nom = nom
        self.code = code


class MockOrdreFabrication:
    def __init__(self, id, numero_of, quantite, date_livraison, priorite, type_piece, operations):
        self.id = id
        self.numero_of = numero_of
        self.quantite = quantite
        self.date_livraison = date_livraison
        self.priorite = priorite
        self.type_piece_id = type_piece
        self.operation_ids = operations


class MockMachine:
    def __init__(self, id, nom, code, capacite_magasin=10):
        self.id = id
        self.nom = nom
        self.code = code
        self.capacite_magasin = capacite_magasin  # Attribut corrigé


# =============================================================================
# 2. ALGORITHME GÉNÉTIQUE
# =============================================================================

class Individual:
    def __init__(self, sequence, machine_assignments, block_structure):
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
                 population_size=100, generations=200,
                 crossover_rate=0.8, mutation_rate=0.2, objective='makespan'):
        self.ofs = ofs
        self.machines = machines
        self.setup_time = setup_time
        self.tool_capacity = tool_capacity
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.objective = objective
        self.of_ids = [of.id for of in ofs]
        self.of_data = self._extract_of_data()

    def _extract_of_data(self) -> Dict:
        data = {}
        for of in self.ofs:
            total_tools = 0
            for op in of.operation_ids:
                op_tools = op.mapped('quantite_requise')
                total_tools += sum(op_tools)

            total_time = sum(op.temps_standard *
                             of.quantite for op in of.operation_ids)
            data[of.id] = {
                'numero': of.numero_of,
                'quantite': of.quantite,
                'date_livraison': of.date_livraison,
                'total_tools': total_tools,
                'total_time': total_time,
                'type_piece': of.type_piece_id.nom if of.type_piece_id else '',
            }
        return data

    def run(self):
        _logger.info(f"🧬 Démarrage AG: Capacité Magasin={self.tool_capacity}")
        population = self._initialize_population()
        for ind in population:
            self._evaluate_fitness(ind)
        best_individual = min(population, key=lambda x: x.fitness)

        for generation in range(1, self.generations + 1):
            parents = self._selection(population)
            offspring = []
            for i in range(0, len(parents), 2):
                if i + 1 < len(parents):
                    p1, p2 = parents[i], parents[i+1]
                    c1, c2 = (self._crossover(p1, p2) if random.random() < self.crossover_rate
                              else (p1.copy(), p2.copy()))
                    if random.random() < self.mutation_rate:
                        self._mutate(c1)
                    if random.random() < self.mutation_rate:
                        self._mutate(c2)
                    offspring.extend([c1, c2])

            for ind in offspring:
                self._evaluate_fitness(ind)
            population = self._replacement(population, offspring)
            current_best = min(population, key=lambda x: x.fitness)
            if current_best.fitness < best_individual.fitness:
                best_individual = current_best

        stats = {'makespan': best_individual.makespan,
                 'final_fitness': best_individual.fitness}
        return best_individual, stats

    def _initialize_population(self):
        population = []
        for _ in range(self.population_size):
            seq = self.of_ids.copy()
            random.shuffle(seq)
            blocks = self._create_blocks_from_sequence(seq)
            machs = [random.randint(0, len(self.machines) - 1)
                     for _ in range(len(blocks))]
            population.append(Individual(seq, machs, blocks))
        return population

    def _create_blocks_from_sequence(self, sequence):
        blocks = []
        current_block = []
        current_tools = 0
        for of_id in sequence:
            of_tools = self.of_data[of_id]['total_tools']
            if current_tools + of_tools <= self.tool_capacity:
                current_block.append(of_id)
                current_tools += of_tools
            else:
                if current_block:
                    blocks.append(current_block)
                current_block = [of_id]
                current_tools = of_tools
        if current_block:
            blocks.append(current_block)
        return blocks

    def _evaluate_fitness(self, individual):
        machine_end_times = {i: 0 for i in range(len(self.machines))}
        for idx, block in enumerate(individual.block_structure):
            m_id = individual.machine_assignments[idx]
            start = machine_end_times[m_id] + self.setup_time
            duration = sum(self.of_data[of_id]['total_time']
                           for of_id in block)
            machine_end_times[m_id] = start + duration
        individual.makespan = max(
            machine_end_times.values()) if machine_end_times else 0
        individual.fitness = individual.makespan

    def _selection(self, population):
        selected = []
        for _ in range(len(population)):
            tournament = random.sample(population, 3)
            selected.append(min(tournament, key=lambda x: x.fitness).copy())
        return selected

    def _crossover(self, p1, p2):
        size = len(p1.sequence)
        pt1, pt2 = sorted(random.sample(range(size), 2))

        def ox(parent1, parent2):
            child = [-1]*size
            child[pt1:pt2] = parent1.sequence[pt1:pt2]
            p2_remain = [x for x in parent2.sequence if x not in child]
            idx = 0
            for i in range(size):
                if child[i] == -1:
                    child[i] = p2_remain[idx]
                    idx += 1
            return child

        c1_seq = ox(p1, p2)
        c2_seq = ox(p2, p1)
        c1_blocks = self._create_blocks_from_sequence(c1_seq)
        c2_blocks = self._create_blocks_from_sequence(c2_seq)
        # Assignations aléatoires simples pour l'exemple
        c1_mach = [random.randint(0, len(self.machines)-1)
                   for _ in range(len(c1_blocks))]
        c2_mach = [random.randint(0, len(self.machines)-1)
                   for _ in range(len(c2_blocks))]
        return Individual(c1_seq, c1_mach, c1_blocks), Individual(c2_seq, c2_mach, c2_blocks)

    def _mutate(self, individual):
        if len(individual.sequence) > 1:
            i, j = random.sample(range(len(individual.sequence)), 2)
            individual.sequence[i], individual.sequence[j] = individual.sequence[j], individual.sequence[i]
            individual.block_structure = self._create_blocks_from_sequence(
                individual.sequence)
            needed = len(individual.block_structure)
            current = len(individual.machine_assignments)
            if needed > current:
                individual.machine_assignments.extend(
                    [random.randint(0, len(self.machines)-1) for _ in range(needed-current)])
            elif needed < current:
                individual.machine_assignments = individual.machine_assignments[:needed]

    def _replacement(self, pop, off):
        combined = pop + off
        combined.sort(key=lambda x: x.fitness)
        return combined[:self.population_size]


# =============================================================================
# 3. VISUALISATION (STYLE ORIGINAL RESTAURÉ)
# =============================================================================

def create_gantt_chart_data(individual, of_data, machines, setup_time, start_date):
    """Prépare les données"""
    gantt_data = []
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_datetime = datetime.combine(start_date, datetime.min.time())
    else:
        start_datetime = start_date

    machine_end_times = {i: start_datetime for i in range(len(machines))}

    for idx, block in enumerate(individual.block_structure):
        machine_id = individual.machine_assignments[idx]
        machine_name = machines[machine_id].nom

        # Setup
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
        # OFs
        for of_id in block:
            of_info = of_data[of_id]
            duration = of_info['total_time']
            of_end = current_time + timedelta(minutes=duration)
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


def create_gantt_figure(gantt_data: List[Dict], title: str) -> go.Figure:
    """
    Créer un diagramme de Gantt interactif avec Plotly.
    STYLE: Original (V1.py) + DETAILS ENRICHIS DANS LA BOX
    """
    fig = go.Figure()

    machines = sorted(set(item['machine'] for item in gantt_data))

    for item in gantt_data:
        duration_hours = (item['end'] - item['start']).total_seconds() / 3600
        if duration_hours == 0:
            duration_hours = 0.5

        color = '#FFA500' if item.get(
            'type') == 'setup' else item.get('color', '#4CAF50')

        # --- CONSTRUCTION DU TEXTE DE LA BOX (HOVER) ---
        hover_text = f"<b>{item['task']}</b><br>"
        hover_text += f"Machine: {item['machine']}<br>"
        hover_text += f"📅 {item['start'].strftime('%d/%m %H:%M')} ➝ {item['end'].strftime('%d/%m %H:%M')}<br>"
        hover_text += f"⏱ Durée: {duration_hours:.2f} h<br>"

        if item.get('type') == 'setup':
            hover_text += "Type: Changement de série (Setup)<br>"
            # Optionnel: afficher combien d'outils sont chargés pour ce bloc
            if 'outil_count' in item:
                hover_text += f"🛠 Outils dans le magasin: {item['outil_count']}<br>"

        elif item.get('type') == 'production':
            hover_text += "--------------------------<br>"
            hover_text += f"🏭 Type Pièce: <b>{item.get('type_piece', 'N/A')}</b><br>"
            hover_text += f"📦 Quantité: {item.get('quantite', 0)}<br>"
            hover_text += f"🛠 Outils requis: {item.get('total_tools', 0)}<br>"

            # Gestion de la date de livraison et du retard
            livraison = item.get('date_livraison')
            if livraison:
                hover_text += f"🏁 Livraison due: {livraison}<br>"

                # Calcul du retard (Comparaison Date Fin vs Date Livraison)
                date_fin_of = item['end'].date()
                # Si livraison est un objet date, on compare direct, sinon conversion
                if isinstance(livraison, str):
                    # Si c'est une string, on ne peut pas comparer facilement sans parsing
                    pass
                else:
                    delta = (date_fin_of - livraison).days
                    if delta > 0:
                        hover_text += f"<b style='color:red; font-size:14px'>⚠ RETARD: {delta} Jours</b><br>"
                    else:
                        hover_text += f"<span style='color:green'>✓ Dans les temps ({abs(delta)}j avance)</span><br>"

        # Ajout de la trace
        fig.add_trace(go.Bar(
            x=[duration_hours * 3600000],
            y=[item['machine']],
            orientation='h',
            name=item['task'],
            base=item['start'],
            marker=dict(color=color, line=dict(color='rgb(0,0,0)', width=1)),
            # <extra></extra> cache le nom de la trace secondaire
            hovertemplate=hover_text + '<extra></extra>',
            showlegend=False,
            width=0.8
        ))

    # Mise en page inchangée
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center', font=dict(size=20)),
        xaxis=dict(
            title='Temps',
            showgrid=True,
            gridcolor='LightGray',
            type='date',
            tickformat='%d/%m\n%H:%M'  # Format date compact
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
# =============================================================================
# 4. EXÉCUTION
# =============================================================================


def generate_test_data(num_of=15, num_machines=2, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    machines = [MockMachine(
        i+1, f"Machine CNC {i+1}", f"M{i+1}", 30) for i in range(num_machines)]
    types = [MockTypePiece(i, f"Type {chr(65+i)}", f"T{i}") for i in range(4)]
    outils = [MockOutil(i, f"Outil {i}", f"T{i}", 1) for i in range(15)]

    ofs = []
    base_date = date.today()
    for i in range(num_of):
        ops = []
        for j in range(random.randint(2, 4)):
            ops.append(MockOperation(j, f"OP{j}", "Op", random.uniform(10, 40),
                                     random.sample(outils, random.randint(1, 3))))

        ofs.append(MockOrdreFabrication(i, f"OF-{i:03d}", random.randint(1, 10),
                                        base_date, 1, random.choice(types), ops))
    return ofs, machines


def main():
    print("=== TEST AG AVEC STYLE GANTT ORIGINAL (V1) ===")

    # Données
    ofs, machines = generate_test_data(25, 2)
    CAPACITY = machines[0].capacite_magasin

    # Optimisation
    scheduler = GeneticAlgorithmScheduler(
        ofs, machines, tool_capacity=CAPACITY)
    solution, stats = scheduler.run()

    print(f"Résultat: Makespan = {stats['makespan']:.2f} min")

    individual.machine_assignments = individual.machine_assignments[:needed]

    def _replacement(self, pop, off):
        combined = pop + off
        combined.sort(key=lambda x: x.fitness)
        return combined[:self.population_size]


# =============================================================================
# 3. VISUALISATION (STYLE ORIGINAL RESTAURÉ)
# =============================================================================

def create_gantt_chart_data(individual, of_data, machines, setup_time, start_date):
    """Prépare les données"""
    gantt_data = []
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_datetime = datetime.combine(start_date, datetime.min.time())
    else:
        start_datetime = start_date

    machine_end_times = {i: start_datetime for i in range(len(machines))}

    for idx, block in enumerate(individual.block_structure):
        machine_id = individual.machine_assignments[idx]
        machine_name = machines[machine_id].nom

        # Setup
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
        # OFs
        for of_id in block:
            of_info = of_data[of_id]
            duration = of_info['total_time']
            of_end = current_time + timedelta(minutes=duration)
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


def create_gantt_figure(gantt_data: List[Dict], title: str) -> go.Figure:
    """
    Créer un diagramme de Gantt interactif avec Plotly.
    STYLE: Original (V1.py) + DETAILS ENRICHIS DANS LA BOX
    """
    fig = go.Figure()

    machines = sorted(set(item['machine'] for item in gantt_data))

    for item in gantt_data:
        duration_hours = (item['end'] - item['start']).total_seconds() / 3600
        if duration_hours == 0:
            duration_hours = 0.5

        color = '#FFA500' if item.get(
            'type') == 'setup' else item.get('color', '#4CAF50')

        # --- CONSTRUCTION DU TEXTE DE LA BOX (HOVER) ---
        hover_text = f"<b>{item['task']}</b><br>"
        hover_text += f"Machine: {item['machine']}<br>"
        hover_text += f"📅 {item['start'].strftime('%d/%m %H:%M')} ➝ {item['end'].strftime('%d/%m %H:%M')}<br>"
        hover_text += f"⏱ Durée: {duration_hours:.2f} h<br>"

        if item.get('type') == 'setup':
            hover_text += "Type: Changement de série (Setup)<br>"
            # Optionnel: afficher combien d'outils sont chargés pour ce bloc
            if 'outil_count' in item:
                hover_text += f"🛠 Outils dans le magasin: {item['outil_count']}<br>"

        elif item.get('type') == 'production':
            hover_text += "--------------------------<br>"
            hover_text += f"🏭 Type Pièce: <b>{item.get('type_piece', 'N/A')}</b><br>"
            hover_text += f"📦 Quantité: {item.get('quantite', 0)}<br>"
            hover_text += f"🛠 Outils requis: {item.get('total_tools', 0)}<br>"

            # Gestion de la date de livraison et du retard
            livraison = item.get('date_livraison')
            if livraison:
                hover_text += f"🏁 Livraison due: {livraison}<br>"

                # Calcul du retard (Comparaison Date Fin vs Date Livraison)
                date_fin_of = item['end'].date()
                # Si livraison est un objet date, on compare direct, sinon conversion
                if isinstance(livraison, str):
                    # Si c'est une string, on ne peut pas comparer facilement sans parsing
                    pass
                else:
                    delta = (date_fin_of - livraison).days
                    if delta > 0:
                        hover_text += f"<b style='color:red; font-size:14px'>⚠ RETARD: {delta} Jours</b><br>"
                    else:
                        hover_text += f"<span style='color:green'>✓ Dans les temps ({abs(delta)}j avance)</span><br>"

        # Ajout de la trace
        fig.add_trace(go.Bar(
            x=[duration_hours * 3600000],
            y=[item['machine']],
            orientation='h',
            name=item['task'],
            base=item['start'],
            marker=dict(color=color, line=dict(color='rgb(0,0,0)', width=1)),
            # <extra></extra> cache le nom de la trace secondaire
            hovertemplate=hover_text + '<extra></extra>',
            showlegend=False,
            width=0.8
        ))

    # Mise en page inchangée
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center', font=dict(size=20)),
        xaxis=dict(
            title='Temps',
            showgrid=True,
            gridcolor='LightGray',
            type='date',
            tickformat='%d/%m\n%H:%M'  # Format date compact
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
# =============================================================================
# 4. EXÉCUTION
# =============================================================================


def generate_test_data(num_of=15, num_machines=2, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    machines = [MockMachine(
        i+1, f"Machine CNC {i+1}", f"M{i+1}", 30) for i in range(num_machines)]
    types = [MockTypePiece(i, f"Type {chr(65+i)}", f"T{i}") for i in range(4)]
    outils = [MockOutil(i, f"Outil {i}", f"T{i}", 1) for i in range(15)]

    ofs = []
    base_date = date.today()
    for i in range(num_of):
        ops = []
        for j in range(random.randint(2, 4)):
            ops.append(MockOperation(j, f"OP{j}", "Op", random.uniform(10, 40),
                                     random.sample(outils, random.randint(1, 3))))

        ofs.append(MockOrdreFabrication(i, f"OF-{i:03d}", random.randint(1, 10),
                                        base_date, 1, random.choice(types), ops))
    return ofs, machines


def main():
    print("=== TEST AG AVEC STYLE GANTT ORIGINAL (V1) ===")

    # Données
    ofs, machines = generate_test_data(25, 2)
    CAPACITY = machines[0].capacite_magasin

    # Optimisation
    scheduler = GeneticAlgorithmScheduler(
        ofs, machines, tool_capacity=CAPACITY)
    solution, stats = scheduler.run()

    print(f"Résultat: Makespan = {stats['makespan']:.2f} min")

    # Visualisation (C'est ici que le style original est appliqué)
    gantt_data = create_gantt_chart_data(
        solution, scheduler.of_data, machines, 30, datetime.now())

    # Appel de la fonction originale restaurée
    fig = create_gantt_figure(
        gantt_data, "Planning Production - Style V1 Original")
    output_file = "c:\\Program Files (x86)\\Odoo 12.0\\server\\addons\\planificateur_cnc\\gantt_test.html"
    fig.write_html(output_file)
    print(f"Graphique sauvegardé dans : {output_file}")


if __name__ == "__main__":
    main()
