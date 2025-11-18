# -*- coding: utf-8 -*-
from odoo import models, fields

class PlanningTimeline(models.Model):
    _name = 'planning.timeline'
    _description = 'Timeline de Planification'
    
    planificateur_id = fields.Many2one('planificateur.cnc', 'Planificateur', ondelete='cascade')
    of_id = fields.Many2one('ordre.fabrication', 'OF')
    machine_id = fields.Many2one('machine.cnc', 'Machine')
    date_debut = fields.Datetime('Début', required=True)
    date_fin = fields.Datetime('Fin', required=True)
    duree = fields.Float('Durée (min)')
    type_activite = fields.Selection([('setup', 'Setup'), ('production', 'Production')], required=True)
