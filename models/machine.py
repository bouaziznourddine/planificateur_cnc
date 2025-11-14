# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PieceType(models.Model):
    _name = 'piece.type'
    _description = 'Type de Pièce'

    name = fields.Char(string='Référence', required=True)
    description = fields.Text(string='Description')
    
    # Opérations
    operation_01_id = fields.Many2one(
        'operation.fabrication',
        string='Opération 1 (OP1)',
        required=True
    )
    operation_02_id = fields.Many2one(
        'operation.fabrication',
        string='Opération 2 (OP2)'
    )
    
    # Palette
    palette_type = fields.Selection([
        ('S', 'Small - ITS148 (petite)'),
        ('B', 'Big - PC210 (grande)')
    ], string='Type de palette', required=True)
    
    # Montage
    montage_id = fields.Many2one(
        'montage.piece',
        string='Montage associé'
    )
    
    # Outils
    nb_outils_total = fields.Integer(
        string='Nombre total d\'outils',
        compute='_compute_nb_outils',
        store=True
    )
    nb_outils_op1 = fields.Integer(
        string='Outils pour OP1',
        related='operation_01_id.nb_outils',
        readonly=True
    )
    nb_outils_op2 = fields.Integer(
        string='Outils pour OP2',
        related='operation_02_id.nb_outils',
        readonly=True
    )
    
    @api.depends('operation_01_id.nb_outils', 'operation_02_id.nb_outils')
    def _compute_nb_outils(self):
        for record in self:
            nb_op1 = record.operation_01_id.nb_outils if record.operation_01_id else 0
            nb_op2 = record.operation_02_id.nb_outils if record.operation_02_id else 0
            record.nb_outils_total = nb_op1 + nb_op2


class Operation(models.Model):
    _name = 'operation.fabrication'
    _description = 'Opération de Fabrication'

    name = fields.Char(string='Code opération', required=True)
    description = fields.Text(string='Description')
    temps_standard_min = fields.Float(string='Temps standard (min)')
    
    # Programme CN
    programme_cn = fields.Char(string='Programme CN')
    fichier_3d = fields.Char(string='Fichier 3D')
    
    # Outils
    outil_ids = fields.Many2many(
        'outil.fabrication',
        'operation_outil_rel',
        'operation_id',
        'outil_id',
        string='Outils nécessaires'
    )
    nb_outils = fields.Integer(
        string='Nombre d\'outils',
        compute='_compute_nb_outils',
        store=True
    )
    
    @api.depends('outil_ids')
    def _compute_nb_outils(self):
        for record in self:
            record.nb_outils = len(record.outil_ids)


class Outil(models.Model):
    _name = 'outil.fabrication'
    _description = 'Outil de Fabrication'

    name = fields.Char(string='Désignation', required=True)
    numero = fields.Char(string='Numéro')
    type_outil_id = fields.Many2one(
        'type.outil',
        string='Type d\'outil'
    )
    diametre = fields.Float(string='Diamètre (mm)')
    rayon = fields.Float(string='Rayon (mm)')
    arete_coupante = fields.Char(string='Arête coupante')
    
    # Durée de vie (informative, non utilisée dans l'ordonnancement selon rapport)
    duree_vie_info = fields.Float(
        string='Durée de vie (info)',
        help='Information seulement - les outils sont neufs à chaque bloc'
    )


class TypeOutil(models.Model):
    _name = 'type.outil'
    _description = 'Type d\'Outil'

    name = fields.Char(string='Nom du type', required=True)
    description = fields.Text(string='Description')
    outil_ids = fields.One2many(
        'outil.fabrication',
        'type_outil_id',
        string='Outils'
    )


class Palette(models.Model):
    _name = 'palette.fabrication'
    _description = 'Palette'

    name = fields.Char(string='Identifiant', required=True)
    palette_type = fields.Selection([
        ('S', 'Small - ITS148'),
        ('B', 'Big - PC210')
    ], string='Type', required=True)
    
    state = fields.Selection([
        ('available', 'Disponible'),
        ('in_use', 'En utilisation'),
        ('maintenance', 'En maintenance')
    ], string='État', default='available')


class Montage(models.Model):
    _name = 'montage.piece'
    _description = 'Montage de Fixation'

    name = fields.Char(string='Référence', required=True)
    piece_type_id = fields.Many2one(
        'piece.type',
        string='Type de pièce compatible'
    )
    capacite_max = fields.Integer(
        string='Capacité maximale',
        required=True,
        help='Nombre max de pièces fixables'
    )


class Machine(models.Model):
    _name = 'machine.cnc'
    _description = 'Machine CNC'

    name = fields.Char(string='Nom', required=True)
    type_machine = fields.Char(string='Type', default='CNC')
    cap_outil = fields.Integer(
        string='Capacité magasin outils',
        required=True,
        help='Nombre max d\'outils stockables'
    )
    
    has_rotary = fields.Boolean(
        string='Équipée rotary (4ème axe)',
        default=False
    )
    
    state = fields.Selection([
        ('available', 'Disponible'),
        ('running', 'En marche'),
        ('maintenance', 'En maintenance'),
        ('breakdown', 'En panne')
    ], string='État', default='available')


class Operateur(models.Model):
    _name = 'operateur.production'
    _description = 'Opérateur de Production'

    name = fields.Char(string='Nom', required=True)
    matricule = fields.Char(string='Matricule')
    
    # Horaires de travail
    heure_debut = fields.Float(string='Heure début (h)', default=8.0)
    heure_fin = fields.Float(string='Heure fin (h)', default=17.0)
    
    state = fields.Selection([
        ('available', 'Disponible'),
        ('busy', 'Occupé'),
        ('break', 'En pause'),
        ('absent', 'Absent')
    ], string='État', default='available')


class Piece(models.Model):
    _name = 'piece.fabrication'
    _description = 'Pièce'

    name = fields.Char(string='Identifiant', required=True)
    of_id = fields.Many2one(
        'ordre.fabrication',
        string='Ordre de fabrication',
        required=True,
        ondelete='cascade'
    )
    piece_type_id = fields.Many2one(
        'piece.type',
        string='Type de pièce',
        related='of_id.piece_type_id',
        store=True
    )
    
    # État
    etat_piece = fields.Selection([
        ('pl', 'Planifié'),
        ('en', 'En cours'),
        ('te', 'Terminé'),
        ('er', 'Erreur'),
        ('fi', 'Fini')
    ], string='État', default='pl')
    
    # Dates
    date_debut_production = fields.Datetime(string='Début production')
    date_fin_production = fields.Datetime(string='Fin production')
    duree_production_min = fields.Float(string='Durée production (min)')
    
    # Palettes
    palette_op1 = fields.Char(string='Palette OP1')
    palette_op2 = fields.Char(string='Palette OP2')
    
    # Magasin
    date_chargement_magasin = fields.Datetime(string='Chargement magasin')
    emplacement_magasin = fields.Char(string='Emplacement magasin')


class PlanningTimeline(models.Model):
    _name = 'planning.timeline'
    _description = 'Timeline du Planning'
    _order = 'date_debut'

    planificateur_id = fields.Many2one(
        'planificateur.cnc',
        string='Planificateur',
        required=True,
        ondelete='cascade'
    )
    of_id = fields.Many2one(
        'ordre.fabrication',
        string='Ordre de fabrication',
        required=True
    )
    bloc_id = fields.Many2one(
        'bloc.production',
        string='Bloc de production'
    )
    machine_id = fields.Many2one(
        'machine.cnc',
        string='Machine'
    )
    
    date_debut = fields.Datetime(string='Date début', required=True)
    date_fin = fields.Datetime(string='Date fin', required=True)
    duree_min = fields.Float(string='Durée (min)')
    
    is_setup = fields.Boolean(
        string='Setup',
        default=False,
        help='Indique si c\'est un temps de setup'
    )
    
    # Champs calculés pour affichage
    retard_jours = fields.Float(
        string='Retard (jours)',
        compute='_compute_retard',
        store=True
    )
    
    @api.depends('date_fin', 'of_id.date_planifiee_livraison')
    def _compute_retard(self):
        for record in self:
            if record.date_fin and record.of_id.date_planifiee_livraison:
                delta = record.date_fin - record.of_id.date_planifiee_livraison
                record.retard_jours = delta.total_seconds() / 86400
            else:
                record.retard_jours = 0
