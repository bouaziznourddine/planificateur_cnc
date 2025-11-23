from typing import List, Dict
from datetime import datetime, timedelta, date
from .genetic_algorithm_scheduler import Individual


def create_piece_level_gantt_data(individual: Individual, of_data: Dict, machines: List,
                                  setup_time: int, start_date) -> List[Dict]:
    """
    Créer les données pour le diagramme de Gantt DÉTAILLÉ (niveau pièce).
    Chaque OF est découpé en N tâches (N = quantité).
    """
    gantt_data = []

    if isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_datetime = datetime.combine(start_date, datetime.min.time())
    else:
        start_datetime = start_date

    machine_end_times = {i: start_datetime for i in range(len(machines))}

    # Palette de couleurs
    colors = [
        '#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD',
        '#8C564B', '#E377C2', '#7F7F7F', '#BCBD22', '#17BECF',
        '#AEC7E8', '#FFBB78', '#98DF8A', '#FF9896', '#C5B0D5',
        '#C49C94', '#F7B6D2', '#C7C7C7', '#DBDB8D', '#9EDAE5'
    ]
    type_piece_colors = {}

    for idx, block in enumerate(individual.block_structure):
        machine_id = individual.machine_assignments[idx]
        machine_name = machines[machine_id].nom if hasattr(
            machines[machine_id], 'nom') else f"Machine {machine_id + 1}"

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
            'description': f'Setup Bloc {idx + 1}'
        })

        current_time = setup_end

        # Opérations des OF dans le bloc
        for of_id in block:
            of_info = of_data[of_id]
            total_duration = of_info['total_time']
            quantity = of_info['quantite']

            # Durée par pièce
            duration_per_piece = total_duration / quantity if quantity > 0 else 0

            # Couleur
            tp = of_info['type_piece']
            if tp not in type_piece_colors:
                type_piece_colors[tp] = colors[len(
                    type_piece_colors) % len(colors)]
            color = type_piece_colors[tp]

            # Créer une tâche pour CHAQUE pièce
            for p_idx in range(quantity):
                piece_start = current_time
                piece_end = piece_start + timedelta(minutes=duration_per_piece)

                gantt_data.append({
                    # Nom unique pour le hover
                    'task': f"{of_info['numero']} - P{p_idx + 1}",
                    # Pour le groupement visuel si besoin
                    'parent_of': of_info['numero'],
                    'machine': machine_name,
                    'start': piece_start,
                    'end': piece_end,
                    'type': 'piece',
                    'of_id': of_id,
                    'piece_index': p_idx + 1,
                    'type_piece': of_info['type_piece'],
                    'color': color,
                    'description': f"OF: {of_info['numero']} | Pièce: {p_idx + 1}/{quantity}"
                })

                current_time = piece_end

        machine_end_times[machine_id] = current_time

    return gantt_data
