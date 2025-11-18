# -*- coding: utf-8 -*-
from odoo import models, fields

class MachineCNC(models.Model):
    _name = 'machine.cnc'
    _description = 'Machine CNC'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    capacite_magasin = fields.Integer('Capacité Magasin Outils', default=40)
    type_machine = fields.Selection([('3axes', '3 Axes'), ('5axes', '5 Axes')], default='3axes')
    active = fields.Boolean(default=True)
    notes = fields.Text('Notes')
