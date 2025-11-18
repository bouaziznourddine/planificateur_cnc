# -*- coding: utf-8 -*-
from odoo import models, fields

class OperateurProduction(models.Model):
    _name = 'operateur.production'
    _description = 'Opérateur de Production'
    
    name = fields.Char('Nom', required=True)
    matricule = fields.Char('Matricule')
    competences = fields.Text('Compétences')
    available = fields.Boolean('Disponible', default=True)
