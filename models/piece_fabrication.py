# -*- coding: utf-8 -*-
from odoo import models, fields,api  

class PieceFabrication(models.Model):
    _name = 'piece.fabrication'
    _description = 'Pièce Individuelle'
    
    nom = fields.Char('Nom', compute='_compute_nom')
    numero_serie = fields.Char('N° Série', required=True)
    of_id = fields.Many2one('ordre.fabrication', 'OF', required=True, ondelete='cascade')
    state = fields.Selection([('to_do', 'À Faire'), ('in_progress', 'En Cours'), ('done', 'Terminé')], default='to_do')
    
    @api.depends('numero_serie', 'of_id')
    def _compute_nom(self):
        for rec in self:
            rec.nom = f"{rec.of_id.numero_of}-{rec.numero_serie}" if rec.of_id else rec.numero_serie
