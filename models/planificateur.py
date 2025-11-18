# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import base64
from io import BytesIO

try:
    from ..genetic_algorithm_scheduler import GeneticAlgorithmScheduler, create_gantt_chart_data
    from ..gantt_chart_generator import GanttChartGenerator, generate_statistics_report
    AG_AVAILABLE = True
except ImportError:
    AG_AVAILABLE = False
    logging.warning("AG non disponible. Installez: pip install plotly pandas numpy")

_logger = logging.getLogger(__name__)


class PlanificateurCNC(models.Model):
    _name = 'planificateur.cnc'
    _description = 'Planificateur CNC avec Algorithme Génétique'
    _order = 'date_creation desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Informations de base
    nom = fields.Char('Nom du Scénario', required=True, tracking=True)
    date_creation = fields.Datetime('Date Création', default=fields.Datetime.now, readonly=True)
    date_debut = fields.Date('Date Début', required=True, tracking=True)
    date_fin = fields.Date('Date Fin', required=True, tracking=True)
    horizon_planification = fields.Integer('Horizon (jours)', compute='_compute_horizon')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé'),
        ('optimized', 'Optimisé'),
        ('scheduled', 'Planifié'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True)
    
    # Relations
    machine_ids = fields.Many2many('machine.cnc', string='Machines CNC', required=True)
    of_candidat_ids = fields.Many2many(
        'ordre.fabrication', 'planificateur_of_candidat_rel',
        'planificateur_id', 'of_id', string='OF Candidats'
    )
    of_selectionne_ids = fields.Many2many(
        'ordre.fabrication', 'planificateur_of_selectionne_rel',
        'planificateur_id', 'of_id', string='OF Sélectionnés', readonly=True
    )
    bloc_production_ids = fields.One2many('bloc.production', 'planificateur_id', string='Blocs')
    timeline_ids = fields.One2many('planning.timeline', 'planificateur_id', string='Timeline')
    
    # Paramètres d'optimisation
    objectif_principal = fields.Selection([
        ('minimize_delays', 'Minimiser les Retards'),
        ('minimize_makespan', 'Minimiser le Makespan'),
        ('maximize_production', 'Maximiser la Production'),
        ('balance_load', 'Équilibrer la Charge'),
    ], string='Objectif', default='minimize_makespan', required=True)
    
    temps_setup = fields.Integer('Temps Setup (min)', default=30)
    
    # Paramètres Algorithme Génétique
    use_genetic_algorithm = fields.Boolean('Utiliser AG', default=True)
    ga_population_size = fields.Integer('Population', default=100)
    ga_generations = fields.Integer('Générations', default=200)
    ga_crossover_rate = fields.Float('Taux Croisement', default=0.8, digits=(3, 2))
    ga_mutation_rate = fields.Float('Taux Mutation', default=0.2, digits=(3, 2))
    
    # Résultats d'optimisation
    makespan_final = fields.Float('Makespan (min)', readonly=True, digits=(16, 2))
    makespan_hours = fields.Float('Makespan (h)', compute='_compute_makespan_hours')
    total_delay = fields.Float('Retard Total (min)', readonly=True, digits=(16, 2))
    machine_balance = fields.Float('Équilibrage', readonly=True, digits=(16, 4))
    optimization_time = fields.Float('Temps Optim (s)', readonly=True, digits=(16, 2))
    
    # Statistiques
    nb_of_total = fields.Integer('Nombre OF Total', compute='_compute_statistics')
    nb_of_optimises = fields.Integer('Nombre OF Optimisés', compute='_compute_statistics')
    nb_blocs = fields.Integer('Nombre de Blocs', compute='_compute_statistics')
    taux_utilisation = fields.Float('Taux Utilisation (%)', compute='_compute_statistics')
    
    # Visualisations
    gantt_attachment_id = fields.Many2one('ir.attachment', string="Gantt Attachment", readonly=True)
    convergence_attachment_id = fields.Many2one('ir.attachment', string="Convergence Attachment", readonly=True)
    statistics_report = fields.Text('Statistiques', readonly=True)
    gantt_iframe_html = fields.Html(
            'Gantt Iframe', 
            compute='_compute_gantt_iframe',
            sanitize=False
        )
    convergence_iframe_html = fields.Html(
            'Convergence Iframe', 
            compute='_compute_convergence_iframe',
            sanitize=False
        )
    @api.depends('convergence_attachment_id')
    def _compute_convergence_iframe(self):
        for rec in self:
            if rec.convergence_attachment_id:
                rec.convergence_iframe_html = f'''
                    <iframe src="/web/content/{rec.convergence_attachment_id.id}" 
                            style="width:100%; height:400px; border:none;">
                    </iframe>
                '''
            else:
                rec.convergence_iframe_html = '<p>Aucun graphique disponible</p>'
    def action_view_convergence(self):
        """Ouvrir la convergence dans un nouvel onglet"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.convergence_attachment_id.id}',
            'target': 'new',
        }
    @api.depends('gantt_attachment_id')
    def _compute_gantt_iframe(self):
            for rec in self:
                if rec.gantt_attachment_id:
                    rec.gantt_iframe_html = f'''
                        <iframe src="/web/content/{rec.gantt_attachment_id.id}" 
                                style="width:100%; height:600px; border:none;">
                        </iframe>
                    '''
                else:
                    rec.gantt_iframe_html = '<p>Aucun diagramme disponible</p>'
    
    # Export
    excel_file = fields.Binary('Fichier Excel', readonly=True)
    excel_filename = fields.Char('Nom Fichier')
    
    # Notes
    notes = fields.Text('Notes')
    
    @api.depends('date_debut', 'date_fin')
    def _compute_horizon(self):
        for rec in self:
            if rec.date_debut and rec.date_fin:
                delta = (rec.date_fin - rec.date_debut).days
                rec.horizon_planification = delta
            else:
                rec.horizon_planification = 0
    
    @api.depends('makespan_final')
    def _compute_makespan_hours(self):
        for rec in self:
            rec.makespan_hours = rec.makespan_final / 60.0 if rec.makespan_final else 0
    
    @api.depends('of_candidat_ids', 'of_selectionne_ids', 'bloc_production_ids', 'makespan_final')
    def _compute_statistics(self):
        for rec in self:
            rec.nb_of_total = len(rec.of_candidat_ids)
            rec.nb_of_optimises = len(rec.of_selectionne_ids)
            rec.nb_blocs = len(rec.bloc_production_ids)
            
            if rec.makespan_final and len(rec.machine_ids) > 0:
                total_capacity = rec.makespan_final * len(rec.machine_ids)
                total_used = sum(b.duree_totale for b in rec.bloc_production_ids)
                rec.taux_utilisation = (total_used / total_capacity * 100) if total_capacity else 0
            else:
                rec.taux_utilisation = 0
    
    def action_validate(self):
        """Valider le scénario"""
        self.ensure_one()
        if not self.of_candidat_ids:
            raise UserError("Ajoutez au moins un OF candidat.")
        if not self.machine_ids:
            raise UserError("Ajoutez au moins une machine.")
        self.state = 'validated'
    
    def action_optimiser(self):
        """Optimiser avec AG ou heuristique"""
        self.ensure_one()
        
        if not self.of_candidat_ids:
            raise UserError("Aucun OF candidat.")
        if not self.machine_ids:
            raise UserError("Aucune machine.")
        
        if self.use_genetic_algorithm and AG_AVAILABLE:
            return self._optimize_with_ga()
        else:
            return self._optimize_heuristic()
    
    def _optimize_with_ga(self):
        """Optimisation par algorithme génétique"""
        start = datetime.now()
        
        try:
            tool_capacity = self.machine_ids[0].capacite_magasin or 40
            
            ga = GeneticAlgorithmScheduler(
                ofs=self.of_candidat_ids,
                machines=self.machine_ids,
                setup_time=self.temps_setup,
                tool_capacity=tool_capacity,
                population_size=self.ga_population_size,
                generations=self.ga_generations,
                crossover_rate=self.ga_crossover_rate,
                mutation_rate=self.ga_mutation_rate,
                objective=self._map_objective()
            )
            
            solution, stats = ga.run()
            
            self._apply_solution(solution, ga.of_data)
            
            self.write({
                'makespan_final': stats['makespan'],
                'total_delay': stats['total_delay'],
                'machine_balance': stats['machine_balance'],
                'optimization_time': (datetime.now() - start).total_seconds(),
                'state': 'optimized',
            })
            
            self._generate_visualizations(solution, ga.of_data, stats)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Optimisation Réussie!',
                    'message': f'Makespan: {self.makespan_final:.0f} min ({self.makespan_hours:.1f}h)',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Erreur AG: {e}", exc_info=True)
            raise UserError(f"Erreur d'optimisation: {str(e)}")
    
    def _optimize_heuristic(self):
        """Optimisation heuristique simple"""
        # TODO: Implémenter heuristique
        self.state = 'optimized'
        return True
    
    def _map_objective(self):
        """Mapper objectif Odoo vers AG"""
        mapping = {
            'minimize_delays': 'delay',
            'minimize_makespan': 'makespan',
            'maximize_production': 'makespan',
            'balance_load': 'balance',
        }
        return mapping.get(self.objectif_principal, 'makespan')
    
    def _apply_solution(self, solution, of_data):
        """Appliquer la solution AG"""
        print("solution")
        print(solution)
        self.bloc_production_ids.unlink()
        self.timeline_ids.unlink()
        
        for idx, block_ofs in enumerate(solution.block_structure):
            machine = self.machine_ids[solution.machine_assignments[idx]]
            total_tools = sum(of_data[of_id]['total_tools'] for of_id in block_ofs)
            total_time = sum(of_data[of_id]['total_time'] for of_id in block_ofs)
            
            bloc = self.env['bloc.production'].create({
                'planificateur_id': self.id,
                'nom': f'Bloc {idx + 1}',
                'machine_id': machine.id,
                'sequence': idx + 1,
                'capacite_outils_utilisee': total_tools,
                'duree_totale': total_time,
            })
            
            ofs = self.of_candidat_ids.filtered(lambda o: o.id in block_ofs)
            for of in ofs:
                of.write({'bloc_id': bloc.id, 'machine_assignee_id': machine.id, 'state': 'scheduled'})
        
        self.of_selectionne_ids = [(6, 0, [of.id for of_id in solution.sequence 
                                            for of in self.of_candidat_ids.filtered(lambda o: o.id == of_id)])]
    def action_view_gantt(self):
        """Ouvrir le Gantt dans un nouvel onglet"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.gantt_attachment_id.id}',
            'target': 'new',
        }
    def _generate_visualizations(self, solution, of_data, stats):
        """Générer Gantt et graphiques"""
        try:
            gantt_data = create_gantt_chart_data(
                solution, of_data, self.machine_ids,
                self.temps_setup, self.date_debut or datetime.now()
            )

            gen = GanttChartGenerator(gantt_data, f"Planning - {self.nom}")
            fig = gen.generate_advanced_gantt()
            html_content = fig.to_html(include_plotlyjs='cdn')
            
            # Créer attachment pour Gantt
            gantt_attachment = self._create_html_attachment(
                f'gantt_{self.id}.html', 
                html_content
            )
            self.gantt_attachment_id = gantt_attachment.id

            # Convergence chart
            if 'best_fitness_history' in stats:
                fig_conv = GanttChartGenerator.create_convergence_chart(
                    stats['best_fitness_history'], stats['avg_fitness_history']
                )
                conv_html = fig_conv.to_html(include_plotlyjs='cdn')
                conv_attachment = self._create_html_attachment(
                    f'convergence_{self.id}.html',
                    conv_html
                )
                self.convergence_attachment_id = conv_attachment.id
            
            report = generate_statistics_report(stats, gantt_data)
            self.statistics_report = self._format_stats(report)
            
        except Exception as e:
            _logger.error(f"Erreur visualisation: {e}")

    def _create_html_attachment(self, filename, html_content):
        """Créer un attachment HTML"""
        attachment_vals = {
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(html_content.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'text/html',
            'public': True,
        }
        return self.env['ir.attachment'].create(attachment_vals)


    def _format_stats(self, report):
        """Formater rapport statistique"""
        text = "="*60 + "\n"
        text += "RAPPORT STATISTIQUE\n"
        text += "="*60 + "\n\n"
        text += f"Makespan: {report['makespan']:.2f} min ({report['makespan']/60:.2f}h)\n"
        text += f"Retard Total: {report['total_delay']:.2f} min\n"
        text += f"Tâches: {report['total_tasks']}\n"
        text += f"Setups: {report['total_setups']}\n\n"
        
        text += "MACHINES:\n"
        text += "-"*60 + "\n"
        for machine, data in report['machines'].items():
            text += f"{machine}: {data['total_time']:.2f}min, {data['num_tasks']} tâches\n"
        
        return text
    
    def action_export_excel(self):
        """Exporter en Excel"""
        # TODO: Implémenter export Excel avec openpyxl
        raise UserError("Export Excel en cours d'implémentation")
    
    def action_cancel(self):
        """Annuler"""
        self.state = 'cancel'
    
    def action_reset_draft(self):
        """Remettre en brouillon"""
        self.write({
            'state': 'draft',
            'makespan_final': 0,
            'total_delay': 0,
            'machine_balance': 0,
            'optimization_time': 0,
            'gantt_chart_html': False,
            'convergence_chart_html': False,
            'statistics_report': False,
        })
        self.bloc_production_ids.unlink()
        self.timeline_ids.unlink()
    
    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.date_debut and rec.date_fin and rec.date_fin < rec.date_debut:
                raise ValidationError("La date de fin doit être après la date de début")
    
    @api.constrains('ga_population_size', 'ga_generations')
    def _check_ga_params(self):
        for rec in self:
            if rec.use_genetic_algorithm:
                if not (10 <= rec.ga_population_size <= 500):
                    raise ValidationError("Population: 10-500")
                if not (10 <= rec.ga_generations <= 1000):
                    raise ValidationError("Générations: 10-1000")
    
    @api.constrains('ga_crossover_rate', 'ga_mutation_rate')
    def _check_ga_rates(self):
        for rec in self:
            if rec.use_genetic_algorithm:
                if not (0 <= rec.ga_crossover_rate <= 1):
                    raise ValidationError("Croisement: 0-1")
                if not (0 <= rec.ga_mutation_rate <= 1):
                    raise ValidationError("Mutation: 0-1")
