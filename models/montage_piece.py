# -*- coding: utf-8 -*-
from odoo import models, fields

class MontagePiece(models.Model):
    _name = 'montage.piece'
    _description = 'Montage de Fixation'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code')
    capacite_max = fields.Integer('Capacité Maximum')
    temps_montage = fields.Float('Temps Montage (min)')
