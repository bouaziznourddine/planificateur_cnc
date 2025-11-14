# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BlocProduction(models.Model):
    _name = 'bloc.production'
    _description = 'Bloc de Production'
    _order = 'sequence'

    name = fields.Char(string='Nom', compute='_compute_name', store=True)
    sequence = fields.Integer(string='Séquence', required=True)
    planificateur_id = fields.Many2one(
        'planificateur.cnc',
        string='Planificateur',
        required=True,
        ondelete='cascade'
    )
    
    # OF du bloc
    of_ids = fields.Many2many(
        'ordre.fabrication',
        'bloc_of_rel',
        'bloc_id',
        'of_id',
        string='Ordres de fabrication'
    )
    nb_of = fields.Integer(
        string='Nombre d\'OF',
        compute='_compute_nb_of',
        store=True
    )
    
    # Machine affectée
    machine_id = fields.Many2one(
        'machine.cnc',
        string='Machine affectée'
    )
    
    # Outils et capacité
    nb_outils_total = fields.Integer(
        string='Nombre total d\'outils',
        help='Somme des outils nécessaires pour tous les OF du bloc'
    )
    cap_outils_machine = fields.Integer(
        string='Capacité machine',
        related='machine_id.cap_outil',
        readonly=True
    )
    taux_utilisation_outils = fields.Float(
        string='Taux d\'utilisation (%)',
        compute='_compute_taux_utilisation',
        store=True
    )
    
    # Temps
    temps_setup_min = fields.Float(
        string='Temps de setup (min)',
        default=30.0,
        help='Temps de préparation au début du bloc'
    )
    duree_totale_min = fields.Float(
        string='Durée totale OF (min)',
        help='Somme des durées de tous les OF'
    )
    duree_bloc_totale_min = fields.Float(
        string='Durée bloc (setup + OF)',
        compute='_compute_duree_totale',
        store=True
    )
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('ready', 'Prêt'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé')
    ], string='État', default='draft')
    
    @api.depends('sequence', 'machine_id')
    def _compute_name(self):
        for record in self:
            machine_name = record.machine_id.name if record.machine_id else 'Non affecté'
            record.name = f"Bloc {record.sequence} - {machine_name}"
    
    @api.depends('of_ids')
    def _compute_nb_of(self):
        for record in self:
            record.nb_of = len(record.of_ids)
    
    @api.depends('nb_outils_total', 'cap_outils_machine')
    def _compute_taux_utilisation(self):
        for record in self:
            if record.cap_outils_machine > 0:
                record.taux_utilisation_outils = (
                    record.nb_outils_total / record.cap_outils_machine * 100
                )
            else:
                record.taux_utilisation_outils = 0
    
    @api.depends('temps_setup_min', 'duree_totale_min')
    def _compute_duree_totale(self):
        for record in self:
            record.duree_bloc_totale_min = record.temps_setup_min + record.duree_totale_min
    
    @api.constrains('nb_outils_total', 'cap_outils_machine')
    def _check_capacite_outils(self):
        """Contrainte 3.1 du rapport : Capacité d'outils du bloc"""
        for record in self:
            if record.machine_id and record.nb_outils_total > record.cap_outils_machine:
                raise ValidationError(
                    f"Le bloc {record.name} nécessite {record.nb_outils_total} outils "
                    f"mais la machine {record.machine_id.name} n'a qu'une capacité de "
                    f"{record.cap_outils_machine} outils. "
                    f"Contrainte 3.1 du rapport : INACCEPTABLE."
                )
