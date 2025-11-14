# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OrdreFabrication(models.Model):
    _name = 'ordre.fabrication'
    _description = 'Ordre de Fabrication (OF)'
    _order = 'date_planifiee_livraison, name'

    name = fields.Char(string='Numéro OF', required=True, copy=False)
    description = fields.Text(string='Description')
    
    # Dates
    date_creation = fields.Datetime(
        string='Date de création',
        default=fields.Datetime.now,
        readonly=True
    )
    date_planifiee_livraison = fields.Datetime(
        string='Date prévue de livraison',
        required=True,
        help='Due date - objectif de livraison'
    )
    delai_fin_fab = fields.Datetime(
        string='Délai limite de fabrication'
    )
    
    # Type de pièce
    piece_type_id = fields.Many2one(
        'piece.type',
        string='Type de pièce',
        required=True
    )
    
    # Quantités
    quantite = fields.Integer(
        string='Quantité commandée',
        required=True,
        default=1
    )
    pieces_qty = fields.Char(
        string='Formule quantité',
        help='Format: p × Qt'
    )
    nb_pieces_prevues = fields.Integer(
        string='Pièces planifiées',
        default=0
    )
    nb_pieces_chargees = fields.Integer(
        string='Pièces chargées',
        default=0
    )
    nb_pieces_terminees = fields.Integer(
        string='Pièces terminées',
        default=0
    )
    nb_pieces_par_palettes = fields.Integer(
        string='Pièces par palette',
        required=True,
        default=1
    )
    
    # Montage
    qty_montage_maxi = fields.Integer(
        string='Capacité max montage',
        help='Nombre maximum de pièces par montage'
    )
    qty_piece_montage = fields.Integer(
        string='Pièces par montage',
        help='Nombre de pièces réellement chargées'
    )
    phase_type_montage_1ere_op = fields.Char(
        string='Phase et type montage 1ère op'
    )
    
    # Outils
    nb_outils_total = fields.Integer(
        string='Nombre total d\'outils',
        compute='_compute_outils_from_type',
        store=True,
        help='Nombre d\'outils nécessaires pour l\'OF complet'
    )
    
    # Programme et ressources
    programme_CN = fields.Char(string='Programme CN')
    type_operation = fields.Char(string='Type d\'opération')
    groupe_ressource = fields.Char(string='Groupe de ressources')
    machine_id = fields.Many2one('machine.cnc', string='Machine affectée')
    puce_RFID = fields.Char(string='Puce RFID')
    
    # Temps opératoires
    duree_operation_min = fields.Float(
        string='Durée opération (min)',
        compute='_compute_durees',
        store=True
    )
    duree_process_operation_min = fields.Float(
        string='Durée processus (min)'
    )
    duree_chargement_machine_min = fields.Float(
        string='Durée chargement (min)',
        default=5.0
    )
    duree_rotation_table_min = fields.Float(
        string='Durée rotation table (min)',
        default=2.0,
        help='Temps intervention opérateur entre OP1 et OP2'
    )
    duree_usinage_min = fields.Float(
        string='Durée usinage (min)'
    )
    
    # Dates d'exécution
    date_debut_operation = fields.Datetime(string='Début opération')
    date_fin_operation = fields.Datetime(string='Fin opération')
    date_debut_chargement_machine = fields.Datetime(string='Début chargement')
    date_fin_chargement_machine = fields.Datetime(string='Fin chargement')
    date_debut_rotation_table = fields.Datetime(string='Début rotation')
    date_fin_rotation_table = fields.Datetime(string='Fin rotation')
    date_debut_usinage = fields.Datetime(string='Début usinage')
    date_fin_usinage = fields.Datetime(string='Fin usinage')
    
    # Relations
    piece_ids = fields.One2many(
        'piece.fabrication',
        'of_id',
        string='Pièces'
    )
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('planned', 'Planifié'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé')
    ], string='État', default='draft', required=True)
    
    # Priorité
    priority = fields.Selection([
        ('0', 'Normale'),
        ('1', 'Moyenne'),
        ('2', 'Haute'),
        ('3', 'Urgente')
    ], string='Priorité', default='0')
    
    @api.depends('piece_type_id', 'piece_type_id.nb_outils_total')
    def _compute_outils_from_type(self):
        """Calcule le nombre d'outils depuis le type de pièce"""
        for record in self:
            if record.piece_type_id:
                record.nb_outils_total = record.piece_type_id.nb_outils_total
            else:
                record.nb_outils_total = 0
    
    @api.depends('duree_chargement_machine_min', 'duree_usinage_min', 
                 'duree_rotation_table_min', 'quantite')
    def _compute_durees(self):
        """Calcule la durée totale de l'opération"""
        for record in self:
            duree_piece = (
                record.duree_chargement_machine_min +
                record.duree_usinage_min +
                record.duree_rotation_table_min
            )
            record.duree_operation_min = duree_piece * record.quantite
    
    @api.constrains('nb_pieces_chargees', 'nb_pieces_prevues')
    def _check_coherence_chargement(self):
        """Contrainte 10 du rapport : Cohérence chargement"""
        for record in self:
            if record.nb_pieces_chargees > record.nb_pieces_prevues:
                raise ValidationError(
                    f"OF {record.name} : Le nombre de pièces chargées "
                    f"({record.nb_pieces_chargees}) ne peut pas dépasser "
                    f"le nombre de pièces prévues ({record.nb_pieces_prevues}). "
                    f"Contrainte 10 du rapport : INACCEPTABLE."
                )
    
    @api.constrains('nb_pieces_terminees', 'quantite')
    def _check_coherence_production(self):
        """Contrainte 11 du rapport : Cohérence production"""
        for record in self:
            if record.nb_pieces_terminees > record.quantite:
                raise ValidationError(
                    f"OF {record.name} : Le nombre de pièces terminées "
                    f"({record.nb_pieces_terminees}) ne peut pas dépasser "
                    f"la quantité commandée ({record.quantite}). "
                    f"Contrainte 11 du rapport : INACCEPTABLE."
                )
    
    @api.constrains('qty_piece_montage', 'qty_montage_maxi')
    def _check_capacite_montage(self):
        """Contrainte 9 du rapport : Capacité montage"""
        for record in self:
            if record.qty_montage_maxi and record.qty_piece_montage > record.qty_montage_maxi:
                raise ValidationError(
                    f"OF {record.name} : Le nombre de pièces par montage "
                    f"({record.qty_piece_montage}) dépasse la capacité maximale "
                    f"({record.qty_montage_maxi}). "
                    f"Contrainte 9 du rapport : INACCEPTABLE."
                )
    
    def action_confirmer(self):
        """Confirme l'OF et le rend disponible pour planification"""
        self.write({'state': 'confirmed'})
    
    def action_planifier(self):
        """Marque l'OF comme planifié"""
        self.write({'state': 'planned'})
    
    def action_demarrer(self):
        """Démarre la production"""
        self.write({
            'state': 'in_progress',
            'date_debut_operation': fields.Datetime.now()
        })
    
    def action_terminer(self):
        """Termine la production"""
        self.write({
            'state': 'done',
            'date_fin_operation': fields.Datetime.now(),
            'nb_pieces_terminees': self.quantite
        })
