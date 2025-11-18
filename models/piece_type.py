# -*- coding: utf-8 -*-
from odoo import models, fields

class PieceType(models.Model):
    _name = 'piece.type'
    _description = 'Type de Pièce'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')
    operation_ids = fields.Many2many('operation.fabrication', string='Opérations Standard')
    palette_type_id = fields.Many2one('palette.fabrication', string='Type Palette')
    montage_id = fields.Many2one('montage.piece', 'Montage')
    temps_cycle = fields.Float('Temps Cycle (min)')
