# -*- coding: utf-8 -*-
"""
Module Planificateur CNC avec génération de diagrammes de Gantt
Extension du module planificateur_cnc pour générer des graphiques visuels
Inspiré du rapport d'ordonnancement Maugars
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import base64
from io import BytesIO

_logger = logging.getLogger(__name__)


class PlanificateurCNCGantt(models.Model):
    """Extension du planificateur CNC avec génération de graphiques"""
    _inherit = 'planificateur.cnc'
    
    # Champs pour stocker les images générées
    gantt_image = fields.Binary(
        string='Diagramme de Gantt',
        readonly=True,
        attachment=True,
        help='Diagramme de Gantt haute résolution du planning'
    )
    gantt_image_filename = fields.Char(
        string='Nom du fichier Gantt',
        readonly=True
    )
    timeline_image = fields.Binary(
        string='Image Timeline',
        readonly=True,
        attachment=True,
        help='Timeline visuelle simplifiée du planning'
    )
    timeline_image_filename = fields.Char(
        string='Nom du fichier Timeline',
        readonly=True
    )
    
    # Statistiques visuelles
    vue_graphique_disponible = fields.Boolean(
        string='Vue graphique disponible',
        compute='_compute_vue_graphique',
        help='Indique si les graphiques peuvent être générés'
    )
    
    @api.depends('timeline_ids', 'state')
    def _compute_vue_graphique(self):
        """Détermine si la vue graphique est disponible"""
        for record in self:
            record.vue_graphique_disponible = (
                record.state == 'planned' and 
                len(record.timeline_ids) > 0
            )
    
    def action_generer_graphiques(self):
        """
        Génère tous les graphiques du planning
        - Diagramme de Gantt
        - Timeline visuelle
        """
        self.ensure_one()
        
        if not self.timeline_ids:
            raise UserError(
                "Aucune timeline disponible. "
                "Veuillez d'abord générer le planning."
            )
        
        try:
            # Générer le diagramme de Gantt
            gantt_data = self._generer_diagramme_gantt()
            if gantt_data:
                filename = f'Gantt_{self.name}_{fields.Date.today()}.png'
                self.write({
                    'gantt_image': base64.b64encode(gantt_data),
                    'gantt_image_filename': filename
                })
                _logger.info(f"Diagramme de Gantt généré : {filename}")
            
            # Générer la timeline visuelle
            timeline_data = self._generer_timeline_visuelle()
            if timeline_data:
                filename = f'Timeline_{self.name}_{fields.Date.today()}.png'
                self.write({
                    'timeline_image': base64.b64encode(timeline_data),
                    'timeline_image_filename': filename
                })
                _logger.info(f"Timeline générée : {filename}")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Graphiques générés'),
                    'message': _('Le diagramme de Gantt et la timeline ont été créés avec succès'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Erreur lors de la génération des graphiques : {str(e)}")
            raise UserError(
                f"Erreur lors de la génération des graphiques : {str(e)}\n"
                f"Vérifiez que matplotlib est installé."
            )
    
    def _generer_diagramme_gantt(self):
        """
        Génère un diagramme de Gantt professionnel
        
        Returns:
            bytes: Image PNG en bytes ou None si erreur
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # Backend non-interactif
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from matplotlib.dates import DateFormatter, HourLocator
            import matplotlib.dates as mdates
            
            # Récupérer les données du planning
            timelines = self.timeline_ids.sorted('date_debut')
            if not timelines:
                return None
            
            # Préparer les données pour le Gantt
            machines = set()
            gantt_data = []
            
            for timeline in timelines:
                machine_name = timeline.machine_id.name if timeline.machine_id else 'Non assigné'
                machines.add(machine_name)
                
                gantt_data.append({
                    'machine': machine_name,
                    'of_name': timeline.of_id.name,
                    'bloc': timeline.bloc_id.sequence if timeline.bloc_id else 0,
                    'start': timeline.date_debut,
                    'end': timeline.date_fin,
                    'duration': timeline.duree_min,
                    'is_setup': timeline.is_setup,
                    'piece_type': timeline.of_id.piece_type_id.name if timeline.of_id.piece_type_id else 'N/A'
                })
            
            # Organiser les machines
            machines_list = sorted(list(machines))
            machine_positions = {machine: i for i, machine in enumerate(machines_list)}
            
            # Créer la figure
            fig, ax = plt.subplots(figsize=(20, 8))
            
            # Couleurs pour les blocs
            couleurs_blocs = {
                1: '#1f77b4',  # Bleu
                2: '#ff7f0e',  # Orange
                3: '#2ca02c',  # Vert
                4: '#d62728',  # Rouge
                5: '#9467bd',  # Violet
                6: '#8c564b',  # Marron
                7: '#e377c2',  # Rose
                8: '#7f7f7f',  # Gris
            }
            
            # Tracer les barres du Gantt
            for data in gantt_data:
                y_pos = machine_positions[data['machine']]
                start_date = data['start']
                end_date = data['end']
                
                # Couleur selon le bloc
                bloc_num = data['bloc']
                couleur = couleurs_blocs.get(bloc_num, '#95a5a6')
                
                # Style différent pour les setups
                if data['is_setup']:
                    couleur = '#ecf0f1'
                    edgecolor = '#34495e'
                    linestyle = '--'
                    alpha = 0.5
                else:
                    edgecolor = 'black'
                    linestyle = '-'
                    alpha = 0.9
                
                # Dessiner la barre
                ax.barh(
                    y_pos, 
                    (end_date - start_date).total_seconds() / 3600,  # Durée en heures
                    left=start_date,
                    height=0.6,
                    color=couleur,
                    edgecolor=edgecolor,
                    linewidth=2,
                    linestyle=linestyle,
                    alpha=alpha
                )
                
                # Ajouter le nom de l'OF si l'espace le permet
                duree_heures = (end_date - start_date).total_seconds() / 3600
                if duree_heures > 1:  # Si la durée est > 1h, afficher le texte
                    mid_point = start_date + (end_date - start_date) / 2
                    label = f"{data['of_name']}\n{duree_heures:.1f}h"
                    ax.text(
                        mid_point, y_pos, label,
                        ha='center', va='center',
                        fontsize=9,
                        weight='bold',
                        color='white' if not data['is_setup'] else 'black'
                    )
            
            # Configuration des axes
            ax.set_yticks(range(len(machines_list)))
            ax.set_yticklabels(machines_list, fontsize=12, weight='bold')
            ax.set_ylim(-0.5, len(machines_list) - 0.5)
            
            # Format de l'axe temporel
            ax.xaxis.set_major_formatter(DateFormatter('%d/%m\n%H:%M'))
            ax.xaxis.set_major_locator(HourLocator(interval=4))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')
            
            # Grille
            ax.grid(True, axis='x', linestyle='--', alpha=0.3)
            ax.set_axisbelow(True)
            
            # Titre et labels
            titre = f'Diagramme de Gantt - {self.name}'
            sous_titre = (
                f'{len(self.of_selectionne_ids)} OF | '
                f'{len(self.bloc_production_ids)} Blocs | '
                f'Période : {self.date_debut_horizon.strftime("%d/%m/%Y")} - '
                f'{self.date_fin_horizon.strftime("%d/%m/%Y")}'
            )
            
            ax.set_title(
                f'{titre}\n{sous_titre}',
                fontsize=16,
                weight='bold',
                pad=20
            )
            ax.set_xlabel('Date et Heure', fontsize=12, weight='bold')
            ax.set_ylabel('Machines CNC', fontsize=12, weight='bold')
            
            # Légende
            legend_elements = []
            for bloc_num in sorted(set(d['bloc'] for d in gantt_data if not d['is_setup'])):
                couleur = couleurs_blocs.get(bloc_num, '#95a5a6')
                legend_elements.append(
                    mpatches.Patch(color=couleur, label=f'Bloc {bloc_num}')
                )
            legend_elements.append(
                mpatches.Patch(
                    facecolor='#ecf0f1',
                    edgecolor='#34495e',
                    linestyle='--',
                    label='Setup'
                )
            )
            
            ax.legend(
                handles=legend_elements,
                loc='upper right',
                fontsize=10,
                framealpha=0.9
            )
            
            # Sauvegarder l'image
            plt.tight_layout()
            img_buffer = BytesIO()
            plt.savefig(
                img_buffer,
                format='png',
                dpi=300,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none'
            )
            plt.close(fig)
            
            img_data = img_buffer.getvalue()
            img_buffer.close()
            
            return img_data
            
        except ImportError:
            _logger.warning("Matplotlib non disponible, génération de l'image de fallback")
            return self._generer_gantt_fallback()
        except Exception as e:
            _logger.error(f"Erreur génération Gantt : {str(e)}")
            return self._generer_gantt_fallback()
    
    def _generer_timeline_visuelle(self):
        """
        Génère une timeline visuelle simplifiée (vue horizontale)
        
        Returns:
            bytes: Image PNG en bytes ou None si erreur
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            
            # Récupérer les données
            timelines = self.timeline_ids.sorted('date_debut')
            if not timelines:
                return None
            
            # Préparer les données
            timeline_data = []
            temps_total = 0
            
            for timeline in timelines:
                if not timeline.is_setup:  # Ignorer les setups dans la timeline
                    duree_heures = timeline.duree_min / 60.0
                    timeline_data.append({
                        'nom': timeline.of_id.name,
                        'duree': duree_heures,
                        'machine': timeline.machine_id.name if timeline.machine_id else 'N/A',
                        'bloc': timeline.bloc_id.sequence if timeline.bloc_id else 0,
                        'outils': timeline.of_id.nb_outils_total or 0
                    })
                    temps_total += duree_heures
            
            if not timeline_data:
                return None
            
            # Créer la figure
            fig = plt.figure(figsize=(20, 8))
            ax = fig.add_subplot(111)
            
            # Couleurs
            couleurs = [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
            ]
            
            # Paramètres de dessin
            largeur_totale = 18
            hauteur_barre = 0.6
            position_x = 0
            
            # Label "CNC" sur le côté
            ax.text(
                -1.5, 0, 'CNC',
                rotation=90,
                va='center',
                ha='center',
                fontsize=20,
                weight='bold',
                color='#2E4057'
            )
            
            # Dessiner les rectangles
            for i, data in enumerate(timeline_data):
                # Calculer la largeur proportionnelle
                largeur = max(1.0, (data['duree'] / temps_total) * largeur_totale)
                couleur = couleurs[i % len(couleurs)]
                
                # Dessiner le rectangle
                rect = patches.Rectangle(
                    (position_x, -hauteur_barre/2),
                    largeur,
                    hauteur_barre,
                    linewidth=2,
                    edgecolor='black',
                    facecolor=couleur,
                    alpha=0.85
                )
                ax.add_patch(rect)
                
                # Ajouter le label de l'OF
                if largeur > 1.5:
                    ax.text(
                        position_x + largeur/2, 0,
                        f"OF{i+1}",
                        ha='center',
                        va='center',
                        fontsize=14,
                        weight='bold',
                        color='white'
                    )
                
                # Afficher la durée en dessous
                ax.text(
                    position_x + largeur/2,
                    -hauteur_barre/2 - 0.15,
                    f"{data['duree']:.1f}h",
                    ha='center',
                    va='top',
                    fontsize=14,
                    weight='bold',
                    color='black'
                )
                
                # Afficher la machine au-dessus
                ax.text(
                    position_x + largeur/2,
                    hauteur_barre/2 + 0.15,
                    data['machine'],
                    ha='center',
                    va='bottom',
                    fontsize=10,
                    color='#34495e'
                )
                
                position_x += largeur
            
            # Flèche "Temps"
            ax.text(
                position_x + 0.8, 0,
                'Temps →',
                va='center',
                ha='left',
                fontsize=16,
                style='italic',
                color='#2E4057',
                weight='bold'
            )
            
            # Configuration des axes
            ax.set_xlim(-2, position_x + 2)
            ax.set_ylim(-1.2, 1.0)
            ax.axis('off')
            
            # Titre
            nb_of = len(timeline_data)
            outils_total = sum(d['outils'] for d in timeline_data)
            cap_total = (self.cap_outils_machine_1 + self.cap_outils_machine_2) / 2
            
            titre = f'Planning CNC - Timeline CNC\n'
            sous_titre = (
                f'{nb_of} OF sélectionnés | '
                f'{temps_total:.1f}h total | '
                f'{outils_total:.0f}/{cap_total:.0f} outils'
            )
            
            plt.title(
                f'{titre}{sous_titre}',
                fontsize=18,
                weight='bold',
                pad=25,
                color='#2E4057'
            )
            
            # Sauvegarder
            img_buffer = BytesIO()
            plt.tight_layout(pad=2.0)
            plt.savefig(
                img_buffer,
                format='png',
                dpi=300,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none',
                pad_inches=0.3
            )
            plt.close(fig)
            
            img_data = img_buffer.getvalue()
            img_buffer.close()
            
            return img_data
            
        except ImportError:
            _logger.warning("Matplotlib non disponible pour la timeline")
            return self._generer_timeline_fallback()
        except Exception as e:
            _logger.error(f"Erreur génération timeline : {str(e)}")
            return self._generer_timeline_fallback()
    
    def _generer_gantt_fallback(self):
        """
        Génère un diagramme de Gantt simple avec PIL si matplotlib n'est pas disponible
        
        Returns:
            bytes: Image PNG en bytes
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Dimensions
            width = 1800
            height = 600
            
            # Créer l'image
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Couleurs
            couleurs = [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
            ]
            
            # Titre
            try:
                font_titre = ImageFont.truetype("arial.ttf", 24)
                font_normal = ImageFont.truetype("arial.ttf", 14)
            except:
                font_titre = ImageFont.load_default()
                font_normal = ImageFont.load_default()
            
            draw.text(
                (width//2, 30),
                f'Diagramme de Gantt - {self.name}',
                fill='black',
                font=font_titre,
                anchor='mm'
            )
            
            # Récupérer les machines
            machines = set()
            for timeline in self.timeline_ids:
                if timeline.machine_id:
                    machines.add(timeline.machine_id.name)
            
            machines_list = sorted(list(machines))
            if not machines_list:
                machines_list = ['Machine CNC']
            
            # Espacement
            y_start = 100
            y_spacing = (height - 150) // len(machines_list)
            x_start = 150
            x_width = width - 200
            
            # Dessiner les lignes de machines
            for i, machine in enumerate(machines_list):
                y_pos = y_start + i * y_spacing
                
                # Nom de la machine
                draw.text(
                    (50, y_pos),
                    machine,
                    fill='black',
                    font=font_normal
                )
                
                # Ligne de base
                draw.line(
                    [(x_start, y_pos), (x_start + x_width, y_pos)],
                    fill='#cccccc',
                    width=2
                )
            
            # Dessiner les barres (simplifié)
            timelines = self.timeline_ids.sorted('date_debut')
            if timelines:
                date_min = min(t.date_debut for t in timelines)
                date_max = max(t.date_fin for t in timelines)
                duree_totale = (date_max - date_min).total_seconds()
                
                for idx, timeline in enumerate(timelines):
                    if timeline.machine_id and timeline.machine_id.name in machines_list:
                        machine_idx = machines_list.index(timeline.machine_id.name)
                        y_pos = y_start + machine_idx * y_spacing
                        
                        # Position et largeur
                        x_offset = ((timeline.date_debut - date_min).total_seconds() / duree_totale) * x_width
                        x_largeur = ((timeline.date_fin - timeline.date_debut).total_seconds() / duree_totale) * x_width
                        
                        x1 = x_start + x_offset
                        x2 = x1 + max(x_largeur, 10)
                        y1 = y_pos - 20
                        y2 = y_pos + 20
                        
                        # Couleur
                        couleur = couleurs[idx % len(couleurs)]
                        
                        # Dessiner le rectangle
                        draw.rectangle(
                            [x1, y1, x2, y2],
                            fill=couleur,
                            outline='black',
                            width=2
                        )
                        
                        # Label si espace suffisant
                        if x_largeur > 30:
                            text = timeline.of_id.name[:10]
                            draw.text(
                                ((x1 + x2)/2, (y1 + y2)/2),
                                text,
                                fill='white',
                                font=font_normal,
                                anchor='mm'
                            )
            
            # Sauvegarder
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG', quality=95)
            return img_buffer.getvalue()
            
        except Exception as e:
            _logger.error(f"Erreur génération Gantt fallback : {str(e)}")
            return None
    
    def _generer_timeline_fallback(self):
        """
        Génère une timeline simple avec PIL
        
        Returns:
            bytes: Image PNG en bytes
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            width = 1600
            height = 400
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            couleurs = [
                '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'
            ]
            
            try:
                font_large = ImageFont.truetype("arial.ttf", 24)
                font_normal = ImageFont.truetype("arial.ttf", 14)
            except:
                font_large = ImageFont.load_default()
                font_normal = ImageFont.load_default()
            
            # Titre
            draw.text(
                (width//2, 30),
                f'{self.name} - Timeline CNC',
                fill='black',
                font=font_large,
                anchor='mm'
            )
            
            # Dessiner les OF
            x_start = 150
            rect_height = 120
            y_pos = (height - rect_height) // 2
            
            timeline_count = len(self.timeline_ids)
            if timeline_count == 0:
                timeline_count = 1
            
            rect_width = min((width - 300) // timeline_count, 150)
            
            for i in range(min(timeline_count, 10)):
                x1 = x_start + i * (rect_width + 10)
                x2 = x1 + rect_width
                y1 = y_pos
                y2 = y1 + rect_height
                
                couleur = couleurs[i % len(couleurs)]
                
                draw.rectangle(
                    [x1, y1, x2, y2],
                    fill=couleur,
                    outline='black',
                    width=3
                )
                
                # Label
                draw.text(
                    ((x1 + x2)/2, (y1 + y2)/2),
                    f"OF{i+1}",
                    fill='white',
                    font=font_large,
                    anchor='mm'
                )
            
            # Labels
            draw.text((30, height//2), 'CNC', fill='black', font=font_large)
            draw.text((width-120, height//2), 'Temps →', fill='gray', font=font_normal)
            
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG', quality=95)
            return img_buffer.getvalue()
            
        except Exception as e:
            _logger.error(f"Erreur génération timeline fallback : {str(e)}")
            return None