# -*- coding: utf-8 -*-
"""
Générateur de Diagramme de Gantt pour le planificateur CNC
Version corrigée - Affichage correct de toutes les tâches
Auteur: Bouaziz Nourddine - CESI LINEACT
"""

import plotly.figure_factory as ff
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class GanttChartGenerator:
    """
    Générateur de diagrammes de Gantt pour la visualisation du planning CNC.
    """
    
    def __init__(self, gantt_data: list, title: str = "Planning de Production CNC"):
        """
        Initialiser le générateur de Gantt.
        
        Args:
            gantt_data: Liste de dictionnaires avec les données de planning
                       Format: {'task', 'machine', 'start', 'end', 'type', 'color', ...}
            title: Titre du diagramme
        """
        self.gantt_data = gantt_data
        self.title = title
        
    def generate_plotly_figure(self) -> go.Figure:
        """
        Générer une figure Plotly interactive.
        
        Returns:
            Figure Plotly
        """
        # Préparer les données pour Plotly
        df_data = []
        
        for item in self.gantt_data:
            df_data.append({
                'Task': item['task'],
                'Start': item['start'],
                'Finish': item['end'],
                'Resource': item['machine'],
                'Type': item.get('type', 'production'),
                'Description': self._format_description(item)
            })
        
        df = pd.DataFrame(df_data)
        
        # Créer le diagramme de Gantt
        if len(df) > 0:
            # Grouper par machine (ressource)
            colors_dict = {}
            for item in self.gantt_data:
                task_name = item['task']
                if item.get('type') == 'setup':
                    colors_dict[task_name] = '#FFA500'  # Orange pour setup
                else:
                    colors_dict[task_name] = item.get('color', '#4CAF50')  # Vert pour production
            
            # Créer le Gantt avec figure_factory
            fig = ff.create_gantt(
                df,
                colors=colors_dict,
                index_col='Resource',
                show_colorbar=True,
                group_tasks=True,
                showgrid_x=True,
                showgrid_y=True,
                title=self.title
            )
            
            # Améliorer le layout
            fig.update_layout(
                xaxis_title="Temps",
                yaxis_title="Machines",
                height=600,
                font=dict(size=12),
                hovermode='closest',
                plot_bgcolor='white',
                xaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='LightGray',
                    tickformat='%d/%m/%Y %H:%M'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='LightGray'
                )
            )
            
            # Ajouter des informations au hover
            fig.update_traces(
                hovertemplate='<b>%{y}</b><br>' +
                             'Tâche: %{text}<br>' +
                             'Début: %{base|%d/%m %H:%M}<br>' +
                             'Fin: %{x|%d/%m %H:%M}<br>' +
                             '<extra></extra>'
            )
        else:
            # Figure vide si pas de données
            fig = go.Figure()
            fig.update_layout(
                title=self.title,
                annotations=[{
                    'text': 'Aucune donnée de planning disponible',
                    'xref': 'paper',
                    'yref': 'paper',
                    'showarrow': False,
                    'font': {'size': 20}
                }]
            )
        
        return fig
    
    
    def generate_advanced_gantt(self) -> go.Figure:
        """
        Générer un diagramme de Gantt avancé avec plus de détails.
        CORRECTION: Utiliser create_gantt de figure_factory pour un affichage correct
        """
        # Préparer les données au format DataFrame pour create_gantt
        df_data = []
        
        for item in self.gantt_data:
            # S'assurer que start et end sont des datetime
            start = item['start']
            end = item['end']
            
            # Convertir en datetime si nécessaire
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            if isinstance(end, str):
                end = datetime.fromisoformat(end)
            
            # Si la date est juste une date (pas datetime), convertir
            if hasattr(start, 'date') and not hasattr(start, 'hour'):
                start = datetime.combine(start, datetime.min.time())
            if hasattr(end, 'date') and not hasattr(end, 'hour'):
                end = datetime.combine(end, datetime.min.time())
                
            df_data.append({
                'Task': item['task'],
                'Start': start,
                'Finish': end,
                'Resource': item['machine'],
                'Description': self._format_description(item)
            })
        
        if not df_data:
            fig = go.Figure()
            fig.update_layout(
                title=self.title,
                annotations=[{
                    'text': 'Aucune donnée de planning disponible',
                    'xref': 'paper',
                    'yref': 'paper',
                    'showarrow': False,
                    'font': {'size': 20}
                }]
            )
            return fig
        
        df = pd.DataFrame(df_data)
        
        # Créer le dictionnaire de couleurs
        colors_dict = {}
        for item in self.gantt_data:
            task_name = item['task']
            if item.get('type') == 'setup':
                colors_dict[task_name] = '#FFA500'  # Orange pour setup
            else:
                colors_dict[task_name] = item.get('color', '#4CAF50')  # Vert pour production
        
        # Créer le Gantt avec figure_factory - MÉTHODE CORRECTE
        fig = ff.create_gantt(
            df,
            colors=colors_dict,
            index_col='Resource',
            show_colorbar=False,
            group_tasks=True,
            showgrid_x=True,
            showgrid_y=True,
            title=self.title,
            bar_width=0.4,
            height=max(400, len(set(item['machine'] for item in self.gantt_data)) * 150)
        )
        
        # Améliorer le layout
        fig.update_layout(
            title=dict(
                text=self.title,
                x=0.5,
                xanchor='center',
                font=dict(size=20, color='#333')
            ),
            xaxis=dict(
                title='Temps',
                showgrid=True,
                gridwidth=1,
                gridcolor='LightGray',
                tickformat='%d/%m/%Y %H:%M',
                type='date'
            ),
            yaxis=dict(
                title='Machines',
                showgrid=True,
                gridwidth=1,
                gridcolor='LightGray'
            ),
            hovermode='closest',
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white',
            font=dict(size=12, family='Arial, sans-serif'),
        )
        
        # Mettre à jour le hover pour afficher les détails
        for i, item in enumerate(self.gantt_data):
            if i < len(fig.data):
                duration = (item['end'] - item['start']).total_seconds() / 3600
                hover_text = self._format_hover_text(item, duration)
                fig.data[i].hoverinfo = 'text'
                fig.data[i].text = hover_text
        
        return fig

    def save_as_html(self, filename: str = "gantt_chart.html"):
        """
        Sauvegarder le diagramme en HTML interactif.
        
        Args:
            filename: Nom du fichier de sortie
        """
        fig = self.generate_advanced_gantt()
        fig.write_html(filename)
        _logger.info(f"Diagramme de Gantt sauvegardé: {filename}")
        return filename
    
    def save_as_png(self, filename: str = "gantt_chart.png", width: int = 1400, height: int = 800):
        """
        Sauvegarder le diagramme en PNG.
        Nécessite kaleido: pip install kaleido
        
        Args:
            filename: Nom du fichier de sortie
            width: Largeur en pixels
            height: Hauteur en pixels
        """
        fig = self.generate_advanced_gantt()
        try:
            fig.write_image(filename, width=width, height=height)
            _logger.info(f"Diagramme de Gantt sauvegardé: {filename}")
            return filename
        except Exception as e:
            _logger.error(f"Erreur lors de la sauvegarde PNG: {e}")
            _logger.info("Installez kaleido: pip install kaleido")
            return None
    
    def get_base64_html(self) -> str:
        """
        Obtenir le diagramme en base64 HTML pour intégration dans Odoo.
        
        Returns:
            String base64 du HTML
        """
        fig = self.generate_advanced_gantt()
        html_str = fig.to_html(include_plotlyjs='cdn')
        html_bytes = html_str.encode('utf-8')
        return base64.b64encode(html_bytes).decode('utf-8')
    
    def _format_description(self, item: dict) -> str:
        """Formater la description pour le tooltip"""
        desc = f"{item['task']}"
        if item.get('type_piece'):
            desc += f" - {item['type_piece']}"
        if item.get('quantite'):
            desc += f" (Qté: {item['quantite']})"
        return desc
    
    def _format_hover_text(self, item: dict, duration: float) -> str:
        """Formater le texte du hover"""
        hover = f"<b>{item['task']}</b><br>"
        hover += f"Machine: {item['machine']}<br>"
        hover += f"Début: {item['start'].strftime('%d/%m/%Y %H:%M')}<br>"
        hover += f"Fin: {item['end'].strftime('%d/%m/%Y %H:%M')}<br>"
        hover += f"Durée: {duration:.2f} h<br>"
        
        if item.get('type') == 'setup':
            hover += "Type: Setup<br>"
        else:
            hover += "Type: Production<br>"
            if item.get('type_piece'):
                hover += f"Pièce: {item['type_piece']}<br>"
            if item.get('quantite'):
                hover += f"Quantité: {item['quantite']}<br>"
        
        return hover
    
    @staticmethod
    def create_convergence_chart(best_fitness_history: list, avg_fitness_history: list) -> go.Figure:
        """
        Créer un graphique de convergence de l'algorithme génétique.
        
        Args:
            best_fitness_history: Historique des meilleures fitness
            avg_fitness_history: Historique des fitness moyennes
            
        Returns:
            Figure Plotly
        """
        fig = go.Figure()
        
        generations = list(range(len(best_fitness_history)))
        
        # Courbe meilleure fitness
        fig.add_trace(go.Scatter(
            x=generations,
            y=best_fitness_history,
            mode='lines',
            name='Meilleure Fitness',
            line=dict(color='#4CAF50', width=2),showlegend=True,
        ))
        
        # Courbe fitness moyenne
        fig.add_trace(go.Scatter(
            x=generations,
            y=avg_fitness_history,
            mode='lines',
            name='Fitness Moyenne',
            line=dict(color='#2196F3', width=2, dash='dash'),showlegend=True,
        ))
        
        fig.update_layout(
            title='Convergence de l\'Algorithme Génétique',
            xaxis_title='Génération',
            yaxis_title='Fitness (Makespan en minutes)',
            hovermode='x unified',
            plot_bgcolor='white',
            font=dict(size=12),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99
            )
        )
        
        return fig


def generate_statistics_report(stats: dict, gantt_data: list) -> dict:
    """
    Générer un rapport statistique du planning.
    
    Args:
        stats: Statistiques de l'algorithme génétique
        gantt_data: Données du diagramme de Gantt
        
    Returns:
        Dictionnaire avec les statistiques formatées
    """
    # Calculer les statistiques par machine
    machines = {}
    for item in gantt_data:
        if item.get('type') != 'setup':
            machine = item['machine']
            if machine not in machines:
                machines[machine] = {
                    'total_time': 0,
                    'num_tasks': 0,
                    'tasks': []
                }
            
            duration = (item['end'] - item['start']).total_seconds() / 60  # en minutes
            machines[machine]['total_time'] += duration
            machines[machine]['num_tasks'] += 1
            machines[machine]['tasks'].append(item['task'])
    
    # Calculer l'utilisation
    if machines:
        max_time = max(m['total_time'] for m in machines.values())
        for machine in machines.values():
            machine['utilization'] = (machine['total_time'] / max_time * 100) if max_time > 0 else 0
    
    report = {
        'makespan': stats.get('makespan', 0),
        'total_delay': stats.get('total_delay', 0),
        'machine_balance': stats.get('machine_balance', 0),
        'num_generations': stats.get('generations', 0),
        'final_fitness': stats.get('final_fitness', 0),
        'machines': machines,
        'total_tasks': len([item for item in gantt_data if item.get('type') != 'setup']),
        'total_setups': len([item for item in gantt_data if item.get('type') == 'setup'])
    }
    
    return report