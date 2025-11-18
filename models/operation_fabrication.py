# -*- coding: utf-8 -*-
from odoo import models, fields

class OperationFabrication(models.Model):
    _name = 'operation.fabrication'
    _description = 'Opération de Fabrication'
    
    code = fields.Char('Code', required=True)
    nom = fields.Char('Nom', required=True)
    description = fields.Text('Description')
    temps_standard = fields.Float('Temps Standard (min)', required=True)
    outil_ids = fields.Many2many('outil.fabrication', string='Outils Nécessaires')
    sequence = fields.Integer('Séquence', default=10)
    # planificateur_id = fields.Many2one('planificateur.cnc', 'Planificateur', ondelete='cascade')

