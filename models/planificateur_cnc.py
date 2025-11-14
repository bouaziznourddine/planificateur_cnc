# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import xlsxwriter
import base64
from io import BytesIO

_logger = logging.getLogger(__name__)


class PlanificateurCNC(models.Model):
    _name = 'planificateur.cnc'
    _description = 'Planificateur CNC - Ordonnancement de production'
    _order = 'date_creation desc'

    name = fields.Char(string='Nom du scénario', required=True)
    date_creation = fields.Datetime(
        string='Date de création',
        default=fields.Datetime.now,
        readonly=True
    )
    date_debut_horizon = fields.Datetime(
        string='Début de l\'horizon de planification',
        required=True,
        default=fields.Datetime.now
    )
    date_fin_horizon = fields.Datetime(
        string='Fin de l\'horizon de planification',
        required=True
    )
    
    # Capacités des machines
    machine_1_id = fields.Many2one(
        'machine.cnc',
        string='Machine 1',
        required=True
    )
    machine_2_id = fields.Many2one(
        'machine.cnc',
        string='Machine 2',
        required=True
    )
    cap_outils_machine_1 = fields.Integer(
        string='Capacité outils Machine 1',
        related='machine_1_id.cap_outil',
        readonly=True
    )
    cap_outils_machine_2 = fields.Integer(
        string='Capacité outils Machine 2',
        related='machine_2_id.cap_outil',
        readonly=True
    )
    
    # OF Candidats et sélectionnés
    of_candidat_ids = fields.Many2many(
        'ordre.fabrication',
        'planificateur_of_candidat_rel',
        'planificateur_id',
        'of_id',
        string='OF Candidats'
    )
    of_selectionne_ids = fields.Many2many(
        'ordre.fabrication',
        'planificateur_of_selectionne_rel',
        'planificateur_id',
        'of_id',
        string='OF Sélectionnés'
    )
    
    # Blocs de production générés
    bloc_production_ids = fields.One2many(
        'bloc.production',
        'planificateur_id',
        string='Blocs de production'
    )
    
    # Planning timeline
    timeline_ids = fields.One2many(
        'planning.timeline',
        'planificateur_id',
        string='Timeline du planning'
    )
    
    # État et résultats
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('of_selected', 'OF Sélectionnés'),
        ('optimized', 'Optimisé'),
        ('planned', 'Planifié'),
        ('done', 'Terminé')
    ], string='État', default='draft', required=True)
    
    # Paramètres d'optimisation
    objectif_principal = fields.Selection([
        ('minimiser_retard', 'Minimiser les retards'),
        ('maximiser_production', 'Maximiser la production'),
        ('minimiser_makespan', 'Minimiser le temps total'),
        ('minimiser_idle', 'Réduire les temps morts'),
        ('minimiser_setup', 'Réduire les changements d\'outils'),
        ('equilibrer_charge', 'Équilibrer la charge')
    ], string='Objectif principal', default='minimiser_retard', required=True)
    
    temps_setup_bloc = fields.Float(
        string='Temps de setup par bloc (minutes)',
        default=30.0,
        help='Temps de préparation machine au début de chaque bloc'
    )
    
    # Résultats de l\'optimisation
    nb_of_optimises = fields.Integer(
        string='Nombre d\'OF optimisés',
        compute='_compute_stats',
        store=True
    )
    nb_blocs_generes = fields.Integer(
        string='Nombre de blocs générés',
        compute='_compute_stats',
        store=True
    )
    duree_totale_makespan = fields.Float(
        string='Durée totale (heures)',
        compute='_compute_stats',
        store=True
    )
    
    # Export Excel
    excel_file = fields.Binary(string='Fichier Excel')
    excel_filename = fields.Char(string='Nom du fichier')
    
    @api.depends('of_selectionne_ids', 'bloc_production_ids', 'timeline_ids')
    def _compute_stats(self):
        """Calcule les statistiques du planning"""
        for record in self:
            record.nb_of_optimises = len(record.of_selectionne_ids)
            record.nb_blocs_generes = len(record.bloc_production_ids)
            
            if record.timeline_ids:
                dates_fin = [t.date_fin for t in record.timeline_ids if t.date_fin]
                dates_debut = [t.date_debut for t in record.timeline_ids if t.date_debut]
                if dates_fin and dates_debut:
                    duree = max(dates_fin) - min(dates_debut)
                    record.duree_totale_makespan = duree.total_seconds() / 3600
                else:
                    record.duree_totale_makespan = 0
            else:
                record.duree_totale_makespan = 0

    def action_selectionner_of(self):
        """Ajouter les OF candidats sélectionnés"""
        return {
            'name': 'Sélectionner les OF',
            'type': 'ir.actions.act_window',
            'res_model': 'ordre.fabrication',
            'view_mode': 'tree',
            'target': 'new',
            'domain': [('state', 'in', ['draft', 'confirmed'])],
            'context': {'planificateur_id': self.id}
        }

    def action_optimiser(self):
        """
        FONCTION PRINCIPALE D'OPTIMISATION
        
        Cette fonction implémente l'algorithme d'optimisation selon le rapport Maugars.
        Elle doit :
        1. Vérifier les contraintes des OF candidats
        2. Créer des blocs de production optimisés
        3. Respecter toutes les contraintes identifiées
        4. Optimiser selon l'objectif principal
        
        Contraintes critiques à respecter (Section 3 du rapport) :
        - Capacité d'outils du bloc ≤ capacité magasin
        - Séquence d'opérations (OP1 puis OP2)
        - Unicité machine par OF
        - Non-préemption
        - Capacité montage
        - Disponibilité opérateurs
        """
        self.ensure_one()
        
        if not self.of_candidat_ids:
            raise UserError("Aucun OF candidat sélectionné.")
        
        _logger.info(f"Début de l'optimisation pour le scénario {self.name}")
        
        try:
            # ÉTAPE 1 : Validation des contraintes
            self._valider_contraintes_of()
            
            # ÉTAPE 2 : Tri et priorisation des OF
            of_tries = self._trier_of_par_priorite()
            
            # ÉTAPE 3 : Création des blocs de production
            blocs_optimises = self._creer_blocs_production(of_tries)
            
            # ÉTAPE 4 : Affectation des machines
            self._affecter_machines_aux_blocs(blocs_optimises)
            
            # ÉTAPE 5 : Enregistrement des OF sélectionnés
            self.of_selectionne_ids = [(6, 0, [of.id for of in of_tries])]
            
            # ÉTAPE 6 : Mise à jour de l'état
            self.state = 'optimized'
            
            _logger.info(f"Optimisation terminée : {len(blocs_optimises)} blocs créés")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Optimisation réussie'),
                    'message': _(f'{len(self.of_selectionne_ids)} OF optimisés en {len(blocs_optimises)} blocs'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Erreur lors de l'optimisation : {str(e)}")
            raise UserError(f"Erreur lors de l'optimisation : {str(e)}")

    def _valider_contraintes_of(self):
        """
        Valide que tous les OF candidats respectent les contraintes de base
        (Section 3.6 du rapport : Solutions NON Acceptables)
        """
        for of in self.of_candidat_ids:
            # Contrainte 1 : Disponibilité des outils
            if not of.nb_outils_total or of.nb_outils_total <= 0:
                raise ValidationError(
                    f"OF {of.name} : Nombre d'outils invalide ({of.nb_outils_total})"
                )
            
            # Contrainte 2 & 3 : Type et capacité palette
            if not of.piece_type_id.palette_type:
                raise ValidationError(
                    f"OF {of.name} : Type de palette non défini"
                )
            
            if of.nb_pieces_par_palettes <= 0:
                raise ValidationError(
                    f"OF {of.name} : Capacité palette invalide"
                )
            
            # Contrainte 9 : Capacité montage
            if of.qty_montage_maxi and of.qty_piece_montage > of.qty_montage_maxi:
                raise ValidationError(
                    f"OF {of.name} : Dépasse la capacité du montage "
                    f"({of.qty_piece_montage} > {of.qty_montage_maxi})"
                )
            
            # Contrainte 10 : Cohérence chargement
            if of.nb_pieces_chargees > of.nb_pieces_prevues:
                raise ValidationError(
                    f"OF {of.name} : Pièces chargées > pièces prévues"
                )
            
            # Contrainte 11 : Cohérence production
            if of.nb_pieces_terminees > of.quantite:
                raise ValidationError(
                    f"OF {of.name} : Pièces terminées > quantité commandée"
                )

    def _trier_of_par_priorite(self):
        """
        Trie les OF selon l'objectif principal et les priorités
        
        Retourne une liste ordonnée d'OF à traiter
        """
        of_list = list(self.of_candidat_ids)
        
        if self.objectif_principal == 'minimiser_retard':
            # Tri par date de livraison (EDD - Earliest Due Date)
            of_list.sort(key=lambda of: (
                of.date_planifiee_livraison or datetime.max,
                -of.quantite  # En cas d'égalité, privilégier les petits lots
            ))
            
        elif self.objectif_principal == 'maximiser_production':
            # Tri par quantité décroissante
            of_list.sort(key=lambda of: -of.quantite)
            
        elif self.objectif_principal == 'minimiser_makespan':
            # Tri par durée croissante (SPT - Shortest Processing Time)
            of_list.sort(key=lambda of: (
                of.duree_operation_min or 0,
                of.date_planifiee_livraison or datetime.max
            ))
            
        elif self.objectif_principal == 'minimiser_setup':
            # Regrouper par type de pièce pour minimiser les changements
            of_list.sort(key=lambda of: (
                of.piece_type_id.id,
                of.date_planifiee_livraison or datetime.max
            ))
            
        else:
            # Par défaut : tri par date de livraison
            of_list.sort(key=lambda of: of.date_planifiee_livraison or datetime.max)
        
        return of_list

    def _creer_blocs_production(self, of_tries):
        """
        Crée les blocs de production en respectant la contrainte de capacité d'outils
        
        ALGORITHME DE CRÉATION DES BLOCS (Contrainte 3.1 du rapport) :
        - Un bloc regroupe des OF exécutés consécutivement sans interruption
        - Contrainte principale : Σ(outils OF) ≤ capacité magasin
        - Un seul setup au début du bloc
        
        Args:
            of_tries: Liste d'OF triés par priorité
            
        Returns:
            Liste des blocs créés
        """
        blocs = []
        bloc_courant = {
            'of_ids': [],
            'nb_outils_total': 0,
            'duree_totale': 0,
            'sequence': 1
        }
        
        # Capacité maximale (prendre la plus petite des deux machines)
        cap_max = min(self.cap_outils_machine_1, self.cap_outils_machine_2)
        
        for of in of_tries:
            nb_outils_of = of.nb_outils_total or 0
            
            # Vérifier si l'OF peut entrer dans le bloc courant
            if (bloc_courant['nb_outils_total'] + nb_outils_of) <= cap_max:
                # Ajouter l'OF au bloc courant
                bloc_courant['of_ids'].append(of.id)
                bloc_courant['nb_outils_total'] += nb_outils_of
                bloc_courant['duree_totale'] += (of.duree_operation_min or 0)
                
            else:
                # Le bloc courant est plein, le sauvegarder et créer un nouveau bloc
                if bloc_courant['of_ids']:
                    blocs.append(self._enregistrer_bloc(bloc_courant))
                
                # Vérifier que l'OF seul peut tenir dans un bloc
                if nb_outils_of > cap_max:
                    _logger.warning(
                        f"OF {of.name} nécessite {nb_outils_of} outils "
                        f"mais la capacité est de {cap_max}. OF ignoré."
                    )
                    continue
                
                # Démarrer un nouveau bloc avec cet OF
                bloc_courant = {
                    'of_ids': [of.id],
                    'nb_outils_total': nb_outils_of,
                    'duree_totale': of.duree_operation_min or 0,
                    'sequence': len(blocs) + 1
                }
        
        # Sauvegarder le dernier bloc s'il contient des OF
        if bloc_courant['of_ids']:
            blocs.append(self._enregistrer_bloc(bloc_courant))
        
        return blocs

    def _enregistrer_bloc(self, bloc_data):
        """Enregistre un bloc de production dans la base"""
        bloc = self.env['bloc.production'].create({
            'planificateur_id': self.id,
            'sequence': bloc_data['sequence'],
            'nb_outils_total': bloc_data['nb_outils_total'],
            'duree_totale_min': bloc_data['duree_totale'],
            'temps_setup_min': self.temps_setup_bloc,
            'of_ids': [(6, 0, bloc_data['of_ids'])]
        })
        return bloc

    def _affecter_machines_aux_blocs(self, blocs):
        """
        Affecte les blocs aux machines en équilibrant la charge
        
        Stratégie :
        - Alterner entre Machine 1 et Machine 2
        - Ou affecter à la machine avec le moins de charge
        """
        if not blocs:
            return
        
        charge_machine_1 = 0
        charge_machine_2 = 0
        
        for bloc in blocs:
            # Affecter à la machine avec le moins de charge
            if charge_machine_1 <= charge_machine_2:
                bloc.machine_id = self.machine_1_id
                charge_machine_1 += bloc.duree_totale_min + bloc.temps_setup_min
            else:
                bloc.machine_id = self.machine_2_id
                charge_machine_2 += bloc.duree_totale_min + bloc.temps_setup_min

    def action_generer_planning(self):
        """
        Génère le planning détaillé avec dates de début et fin
        pour chaque OF/opération
        """
        self.ensure_one()
        
        if not self.of_selectionne_ids:
            raise UserError("Aucun OF sélectionné. Veuillez d'abord optimiser.")
        
        if not self.bloc_production_ids:
            raise UserError("Aucun bloc de production. Veuillez d'abord optimiser.")
        
        # Supprimer l'ancien planning
        self.timeline_ids.unlink()
        
        # Générer le nouveau planning
        date_courante = self.date_debut_horizon
        
        for bloc in self.bloc_production_ids.sorted('sequence'):
            # Setup du bloc
            date_fin_setup = date_courante + timedelta(minutes=bloc.temps_setup_min)
            
            # Traiter chaque OF du bloc
            for of in bloc.of_ids:
                date_debut_of = date_fin_setup
                duree_of = of.duree_operation_min or 0
                date_fin_of = date_debut_of + timedelta(minutes=duree_of)
                
                # Créer l'entrée timeline
                self.env['planning.timeline'].create({
                    'planificateur_id': self.id,
                    'of_id': of.id,
                    'bloc_id': bloc.id,
                    'machine_id': bloc.machine_id.id,
                    'date_debut': date_debut_of,
                    'date_fin': date_fin_of,
                    'duree_min': duree_of,
                    'is_setup': False
                })
                
                date_fin_setup = date_fin_of
            
            date_courante = date_fin_setup
        
        self.state = 'planned'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Planning généré'),
                'message': _(f'Planning créé avec {len(self.timeline_ids)} opérations'),
                'type': 'success',
            }
        }

    def action_exporter_excel(self):
        """Exporte le planning en format Excel"""
        self.ensure_one()
        
        if not self.timeline_ids:
            raise UserError("Aucun planning à exporter. Veuillez d'abord générer le planning.")
        
        # Créer le fichier Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy hh:mm'
        })
        
        # Feuille 1 : Timeline
        sheet1 = workbook.add_worksheet('Timeline')
        headers = ['OF', 'Machine', 'Bloc', 'Début', 'Fin', 'Durée (min)', 'Type pièce']
        
        for col, header in enumerate(headers):
            sheet1.write(0, col, header, header_format)
        
        row = 1
        for timeline in self.timeline_ids.sorted('date_debut'):
            sheet1.write(row, 0, timeline.of_id.name)
            sheet1.write(row, 1, timeline.machine_id.name)
            sheet1.write(row, 2, f"Bloc {timeline.bloc_id.sequence}")
            sheet1.write(row, 3, timeline.date_debut, date_format)
            sheet1.write(row, 4, timeline.date_fin, date_format)
            sheet1.write(row, 5, timeline.duree_min)
            sheet1.write(row, 6, timeline.of_id.piece_type_id.name or '')
            row += 1
        
        # Feuille 2 : Blocs de production
        sheet2 = workbook.add_worksheet('Blocs')
        headers2 = ['Bloc', 'Machine', 'Nb OF', 'Nb Outils', 'Durée (min)', 'Setup (min)']
        
        for col, header in enumerate(headers2):
            sheet2.write(0, col, header, header_format)
        
        row = 1
        for bloc in self.bloc_production_ids.sorted('sequence'):
            sheet2.write(row, 0, f"Bloc {bloc.sequence}")
            sheet2.write(row, 1, bloc.machine_id.name if bloc.machine_id else '')
            sheet2.write(row, 2, len(bloc.of_ids))
            sheet2.write(row, 3, bloc.nb_outils_total)
            sheet2.write(row, 4, bloc.duree_totale_min)
            sheet2.write(row, 5, bloc.temps_setup_min)
            row += 1
        
        workbook.close()
        output.seek(0)
        
        # Sauvegarder le fichier
        filename = f'Planning_{self.name}_{fields.Date.today()}.xlsx'
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': filename
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Export réussi'),
                'message': _(f'Le fichier {filename} a été généré'),
                'type': 'success',
            }
        }

    @api.constrains('date_debut_horizon', 'date_fin_horizon')
    def _check_horizon_dates(self):
        """Vérifie que l'horizon de planification est cohérent"""
        for record in self:
            if record.date_fin_horizon <= record.date_debut_horizon:
                raise ValidationError(
                    "La date de fin doit être postérieure à la date de début."
                )
