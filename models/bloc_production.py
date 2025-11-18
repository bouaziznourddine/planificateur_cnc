# -*- coding: utf-8 -*-
from odoo import models, fields, api

class BlocProduction(models.Model):
    _name = 'bloc.production'
    _description = 'Bloc de Production'
    _order = 'sequence, nom'
    
    nom = fields.Char('Nom', required=True)
    sequence = fields.Integer('Séquence', default=10)
    planificateur_id = fields.Many2one('planificateur.cnc', 'Planificateur', ondelete='cascade')
    
    machine_id = fields.Many2one('machine.cnc', 'Machine', required=True)
    of_ids = fields.One2many('ordre.fabrication', 'bloc_id', 'OF')
    date_debut = fields.Datetime('Début')
    date_fin = fields.Datetime('Fin')
    duree_totale = fields.Float('Durée (min)')
    capacite_outils_utilisee = fields.Integer('Outils Utilisés')
    state = fields.Selection([('draft', 'Brouillon'), ('planned', 'Planifié'), ('done', 'Terminé')], default='draft')
 