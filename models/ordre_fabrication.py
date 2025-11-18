# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OrdreFabrication(models.Model):
    _name = 'ordre.fabrication'
    _description = 'Ordre de Fabrication'
    _order = 'priorite desc, date_livraison'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Identification
    numero_of = fields.Char('Numéro OF', required=True, copy=False, tracking=True)
    nom = fields.Char('Nom', compute='_compute_nom', store=True)
    reference_client = fields.Char('Référence Client')
    
    # Dates
    date_creation = fields.Date('Date Création', default=fields.Date.context_today, readonly=True)
    date_livraison = fields.Date('Date Livraison', required=True, tracking=True)
    date_debut_prevu = fields.Datetime('Début Prévu', readonly=True)
    date_fin_prevu = fields.Datetime('Fin Prévu', readonly=True)
    
    # Quantités
    quantite = fields.Integer('Quantité', required=True, default=1, tracking=True)
    quantite_chargee = fields.Integer('Qté Chargée', readonly=True)
    quantite_terminee = fields.Integer('Qté Terminée', readonly=True)
    quantite_restante = fields.Integer('Qté Restante', compute='_compute_quantites')
    
    # Priorité et état
    priorite = fields.Integer('Priorité', default=5, tracking=True, help="1=Urgent, 10=Basse")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('scheduled', 'Planifié'),
        ('in_progress', 'En Cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], default='draft', tracking=True)
    
    # Relations
    type_piece_id = fields.Many2one('piece.type', 'Type de Pièce', required=True, ondelete='restrict')
    operation_ids = fields.Many2many('operation.fabrication', string='Opérations')
    bloc_id = fields.Many2one('bloc.production', 'Bloc', readonly=True, ondelete='set null')
    machine_assignee_id = fields.Many2one('machine.cnc', 'Machine Assignée', readonly=True)
    piece_ids = fields.One2many('piece.fabrication', 'of_id', 'Pièces')
    
    # Calculs
    temps_total_estime = fields.Float('Temps Total (min)', compute='_compute_temps_total', store=True)
    nombre_outils_requis = fields.Integer('Outils Requis', compute='_compute_outils_requis', store=True)
    
    # Retard
    retard_jours = fields.Integer('Retard (jours)', compute='_compute_retard')
    est_en_retard = fields.Boolean('En Retard?', compute='_compute_retard')
    
    # Notes
    notes = fields.Text('Notes')
    
    @api.depends('numero_of', 'type_piece_id')
    def _compute_nom(self):
        for rec in self:
            if rec.type_piece_id:
                rec.nom = f"{rec.numero_of} - {rec.type_piece_id.nom}"
            else:
                rec.nom = rec.numero_of
    
    @api.depends('quantite', 'quantite_chargee', 'quantite_terminee')
    def _compute_quantites(self):
        for rec in self:
            rec.quantite_restante = rec.quantite - rec.quantite_terminee
    
    @api.depends('operation_ids', 'quantite')
    def _compute_temps_total(self):
        for rec in self:
            total = sum(op.temps_standard * rec.quantite for op in rec.operation_ids)
            rec.temps_total_estime = total
    
    @api.depends('operation_ids')
    def _compute_outils_requis(self):
        for rec in self:
            total = sum(len(op.outil_ids) for op in rec.operation_ids)
            rec.nombre_outils_requis = total
    
    @api.depends('date_fin_prevu', 'date_livraison')
    def _compute_retard(self):
        for rec in self:
            if rec.date_fin_prevu and rec.date_livraison:
                delta = (rec.date_fin_prevu.date() - rec.date_livraison).days
                rec.retard_jours = max(0, delta)
                rec.est_en_retard = delta > 0
            else:
                rec.retard_jours = 0
                rec.est_en_retard = False
    
    def action_confirm(self):
        """Confirmer l'OF"""
        self.state = 'confirmed'
    
    def action_cancel(self):
        """Annuler l'OF"""
        self.state = 'cancel'
    
    @api.constrains('quantite')
    def _check_quantite(self):
        for rec in self:
            if rec.quantite <= 0:
                raise ValidationError("La quantité doit être positive")
    
    @api.constrains('priorite')
    def _check_priorite(self):
        for rec in self:
            if not (1 <= rec.priorite <= 10):
                raise ValidationError("La priorité doit être entre 1 et 10")
