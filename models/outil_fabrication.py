# -*- coding: utf-8 -*-
from odoo import models, fields

class OutilFabrication(models.Model):
    _name = 'outil.fabrication'
    _description = 'Outil de Coupe'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    diametre = fields.Float('Diamètre (mm)')
    longueur = fields.Float('Longueur (mm)')
    type_outil = fields.Selection([('fraise', 'Fraise'), ('foret', 'Foret'), ('taraud', 'Taraud')], required=True)
    quantite_requise = fields.Integer('Quantité Requise', default=1)
