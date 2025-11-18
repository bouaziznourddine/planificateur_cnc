# -*- coding: utf-8 -*-
from odoo import models, fields

class PaletteFabrication(models.Model):
    _name = 'palette.fabrication'
    _description = 'Palette de Fixation'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code')
    type_palette = fields.Selection([('S', 'Petite (S)'), ('B', 'Grande (B)')], required=True)
    capacite = fields.Integer('Capacité Pièces')
