# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MachineCNC(models.Model):
    _name = 'machine.cnc'
    _description = 'Machine CNC'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    capacite_magasin = fields.Integer('Capacité Magasin Outils', default=40)
    type_machine = fields.Selection([('3axes', '3 Axes'), ('5axes', '5 Axes')], default='3axes')
    active = fields.Boolean(default=True)
    etat_machine = fields.Selection([
        ('disponible', 'Disponible'),
        ('en_marche', 'En Marche'),
        ('panne', 'En Panne'),
        ('maintenance', 'En Maintenance')
    ], string='État Actuel', default='disponible')
    equipement_special = fields.Selection([('aucun', 'Aucun'), ('rotary', 'Rotary (4e axe)')], string='Équipement Spécial', default='aucun')
    notes = fields.Text('Notes')


class MagasinStockage(models.Model):
    _name = 'magasin.stockage'
    _description = 'Zone de Stockage (Magasin)'

    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    capacite_max_S = fields.Integer('Capacité Max Palettes S', default=10)
    capacite_max_B = fields.Integer('Capacité Max Palettes B', default=10)


class Rotary(models.Model):
    _name = 'rotary.equipement'
    _description = 'Équipement Rotary (4ème axe)'

    nom = fields.Char('Nom', required=True)
    max_position_S = fields.Integer('Max Positions S', default=4)
    max_position_B = fields.Integer('Max Positions B', default=2)


class MontagePiece(models.Model):
    _name = 'montage.piece'
    _description = 'Montage de Fixation'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code')
    capacite_max = fields.Integer('Capacité Maximum')
    temps_montage = fields.Float('Temps Montage (min)')
    type_piece_compatible_id = fields.Many2one('piece.type', string='Type de Pièce Compatible')
    qty_montage_maxi = fields.Integer('Quantité Maxi par Montage', default=1)


class OperateurProduction(models.Model):
    _name = 'operateur.production'
    _description = 'Opérateur de Production'
    
    name = fields.Char('Nom', required=True)
    matricule = fields.Char('Matricule')
    competences = fields.Text('Compétences')
    available = fields.Boolean('Disponible', default=True)


class TypeOutil(models.Model):
    _name = 'type.outil'
    _description = "Type d'Outil"

    name = fields.Char('Nom', required=True)


class OutilFabrication(models.Model):
    _name = 'outil.fabrication'
    _description = 'Outil de Coupe'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True) # UniqueID
    numero = fields.Char('Numéro Référence')
    diametre = fields.Float('Diamètre (mm)')
    rayon = fields.Float('Rayon (mm)')
    arete_coupante = fields.Char('Arête Coupante')
    longueur = fields.Float('Longueur (mm)')
    type_outil_id = fields.Many2one('type.outil', string="Type d'Outil")
    type_outil = fields.Selection([('fraise', 'Fraise'), ('foret', 'Foret'), ('taraud', 'Taraud')], string="Catégorie") 
    quantite_requise = fields.Integer('Quantité Requise', default=1)


class PaletteFabrication(models.Model):
    _name = 'palette.fabrication'
    _description = 'Palette de Fixation'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code')
    type_palette = fields.Selection([('S', 'Petite (S)'), ('B', 'Grande (B)')], required=True)
    capacite = fields.Integer('Capacité Pièces')
    etat = fields.Selection([('disponible', 'Disponible'), ('utilisee', 'Utilisée'), ('maintenance', 'Maintenance')], default='disponible')


class OperationFabrication(models.Model):
    _name = 'operation.fabrication'
    _description = 'Opération de Fabrication'
    
    code = fields.Char('Code', required=True) # UniqueID
    nom = fields.Char('Nom', required=True)
    description = fields.Text('Description')
    temps_standard = fields.Float('Temps Standard (min)', required=True)
    outil_ids = fields.Many2many('outil.fabrication', string='Outils Nécessaires')
    sequence = fields.Integer('Séquence', default=10)
    fichiers_3d_piece = fields.Char('Fichier 3D')
    nb_outils = fields.Integer('Nombre Outils', compute='_compute_nb_outils', store=True)

    @api.depends('outil_ids')
    def _compute_nb_outils(self):
        for rec in self:
            rec.nb_outils = len(rec.outil_ids)


class PieceType(models.Model):
    _name = 'piece.type'
    _description = 'Type de Pièce'
    
    nom = fields.Char('Nom', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')
    
    # Opérations spécifiques
    operation_01_id = fields.Many2one('operation.fabrication', string='Opération 1')
    operation_02_id = fields.Many2one('operation.fabrication', string='Opération 2')
    
    palette_type = fields.Selection([('S', 'Petite (S)'), ('B', 'Grande (B)')], string='Type Palette Requis', required=True)
    montage_id = fields.Many2one('montage.piece', 'Montage Associé')
    
    # Anciens champs gardés pour compatibilité ou calculés
    operation_ids = fields.Many2many('operation.fabrication', string='Toutes Opérations')
    temps_cycle = fields.Float('Temps Cycle Total (min)', compute='_compute_temps_cycle')

    @api.depends('operation_01_id', 'operation_02_id')
    def _compute_temps_cycle(self):
        for rec in self:
            t1 = rec.operation_01_id.temps_standard if rec.operation_01_id else 0
            t2 = rec.operation_02_id.temps_standard if rec.operation_02_id else 0
            rec.temps_cycle = t1 + t2


class OrdreFabrication(models.Model):
    _name = 'ordre.fabrication'
    _description = 'Ordre de Fabrication'
    _order = 'priorite desc, date_livraison'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Identification
    numero_of = fields.Char('Numéro OF', required=True, copy=False, tracking=True)
    nom = fields.Char('Nom', compute='_compute_nom', store=True)
    reference_client = fields.Char('Référence Client')
    
    # Dates
    date_creation = fields.Date('Date Création', default=fields.Date.context_today, readonly=True)
    date_livraison = fields.Datetime('Date Livraison Prévue', required=True, tracking=True)
    delai_fin_fab = fields.Datetime('Délai Fin Fab')

    # Planification
    date_debut_prevu = fields.Datetime('Début Prévu', readonly=True)
    date_fin_prevu = fields.Datetime('Fin Prévu', readonly=True)
    
    # Quantités
    quantite = fields.Integer('Quantité Totale', required=True, default=1, tracking=True)
    nb_pieces_prevues = fields.Integer('Nb Pièces Prévues', compute='_compute_nb_pieces_prevues', store=True)
    nb_pieces_chargees = fields.Integer('Nb Pièces Chargées', readonly=True)
    nb_pieces_terminees = fields.Integer('Nb Pièces Terminées', readonly=True)
    quantite_restante = fields.Integer('Qté Restante', compute='_compute_quantites')
    
    # Technique
    type_piece_id = fields.Many2one('piece.type', 'Type de Pièce', required=True, ondelete='restrict')
    programme_CN = fields.Char('Programme CN')
    phase = fields.Selection([
        ('30', 'Phase 30 (OP1+OP2)'), 
        ('40', 'Phase 40 (OP2)'), 
        ('50', 'Phase 50 (OP1 seul)'),
        ('60', 'Phase 60 (OP1 seul)'),
        ('70', 'Phase 70 (OP1 seul)')
    ], string='Phase', default='30')
    
    # Durées détaillées
    duree_chargement_machine_min = fields.Integer('Durée Chargement (min)', default=5)
    duree_rotation_table_min = fields.Integer('Durée Rotation (min)', default=2)
    duree_usinage_min = fields.Integer('Durée Usinage (min)', compute='_compute_temps_total')
    
    # Priorité et état
    priorite = fields.Integer('Priorité', default=5, tracking=True, help="1=Urgent, 10=Basse")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('scheduled', 'Planifié'),
        ('in_progress', 'En Cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], default='draft', tracking=True)
    
    # Relations
    operation_ids = fields.Many2many('operation.fabrication', string='Opérations', compute='_compute_operations', store=True)
    bloc_id = fields.Many2one('bloc.production', 'Bloc', readonly=True, ondelete='set null')
    machine_assignee_id = fields.Many2one('machine.cnc', 'Machine Assignée', readonly=True)
    piece_ids = fields.One2many('piece.fabrication', 'of_id', 'Pièces')
    
    # Calculs
    temps_total_estime = fields.Float('Temps Total (min)', compute='_compute_temps_total', store=True)
    nombre_outils_requis = fields.Integer('Outils Requis', compute='_compute_outils_requis', store=True)
    
    # Retard
    retard_jours = fields.Integer('Retard (jours)', compute='_compute_retard')
    est_en_retard = fields.Boolean('En Retard?', compute='_compute_retard')
    
    notes = fields.Text('Notes')
    
    @api.depends('numero_of', 'type_piece_id')
    def _compute_nom(self):
        for rec in self:
            if rec.type_piece_id:
                rec.nom = f"{rec.numero_of} - {rec.type_piece_id.nom}"
            else:
                rec.nom = rec.numero_of

    @api.depends('quantite')
    def _compute_nb_pieces_prevues(self):
        for rec in self:
            rec.nb_pieces_prevues = rec.quantite
    
    @api.depends('quantite', 'nb_pieces_terminees')
    def _compute_quantites(self):
        for rec in self:
            rec.quantite_restante = rec.quantite - rec.nb_pieces_terminees

    @api.depends('type_piece_id', 'phase')
    def _compute_operations(self):
        for rec in self:
            ops = []
            if rec.type_piece_id:
                if rec.phase in ['30', '40']: # OP1 + OP2 or sequence
                    if rec.type_piece_id.operation_01_id:
                        ops.append(rec.type_piece_id.operation_01_id.id)
                    if rec.type_piece_id.operation_02_id:
                        ops.append(rec.type_piece_id.operation_02_id.id)
                else: # Single OP
                    if rec.type_piece_id.operation_01_id:
                        ops.append(rec.type_piece_id.operation_01_id.id)
            rec.operation_ids = [(6, 0, ops)]
    
    @api.depends('operation_ids', 'quantite', 'duree_chargement_machine_min', 'duree_rotation_table_min')
    def _compute_temps_total(self):
        for rec in self:
            usinage = sum(op.temps_standard * rec.quantite for op in rec.operation_ids)
            rec.duree_usinage_min = int(usinage)
            total = usinage + rec.duree_chargement_machine_min + rec.duree_rotation_table_min
            rec.temps_total_estime = total
    
    @api.depends('operation_ids')
    def _compute_outils_requis(self):
        for rec in self:
            tools = rec.operation_ids.mapped('outil_ids')
            rec.nombre_outils_requis = len(tools)
    
    @api.depends('date_fin_prevu', 'date_livraison')
    def _compute_retard(self):
        for rec in self:
            if rec.date_fin_prevu and rec.date_livraison:
                delta = (rec.date_fin_prevu - rec.date_livraison).days
                rec.retard_jours = max(0, delta)
                rec.est_en_retard = delta > 0
            else:
                rec.retard_jours = 0
                rec.est_en_retard = False
    
    def action_confirm(self):
        self.state = 'confirmed'
    
    def action_cancel(self):
        self.state = 'cancel'
    
    @api.constrains('quantite')
    def _check_quantite(self):
        for rec in self:
            if rec.quantite <= 0:
                raise ValidationError("La quantité doit être positive")
    
    @api.constrains('priorite')
    def _check_priorite(self):
        for rec in self:
            if not (1 <= rec.priorite <= 10):
                raise ValidationError("La priorité doit être entre 1 et 10")


class PieceFabrication(models.Model):
    _name = 'piece.fabrication'
    _description = 'Pièce Individuelle'
    
    nom = fields.Char('Nom', compute='_compute_nom')
    numero_serie = fields.Char('N° Série', required=True)
    of_id = fields.Many2one('ordre.fabrication', 'OF', required=True, ondelete='cascade')
    type_piece_id = fields.Many2one('piece.type', related='of_id.type_piece_id', store=True)
    
    state = fields.Selection([
        ('pl', 'Planifié'), 
        ('en', 'En Cours'), 
        ('te', 'Terminé'),
        ('er', 'Erreur'),
        ('fi', 'Fini')
    ], default='pl', string='État Pièce')
    
    date_debut_production = fields.Datetime('Début Production')
    date_fin_production = fields.Datetime('Fin Production')
    duree_production_min = fields.Integer('Durée Prod (min)')
    
    palette_op1_id = fields.Many2one('palette.fabrication', 'Palette OP1')
    palette_op2_id = fields.Many2one('palette.fabrication', 'Palette OP2')
    
    emplacement_magasin = fields.Char('Emplacement Magasin')
    
    @api.depends('numero_serie', 'of_id')
    def _compute_nom(self):
        for rec in self:
            rec.nom = f"{rec.of_id.numero_of}-{rec.numero_serie}" if rec.of_id else rec.numero_serie


class BlocProduction(models.Model):
    _name = 'bloc.production'
    _description = 'Bloc de Production'
    _order = 'sequence, nom'
    
    nom = fields.Char('Nom', required=True)
    sequence = fields.Integer('Séquence', default=10)
    planificateur_id = fields.Many2one('planificateur.cnc', 'Planificateur', ondelete='cascade')
    
    machine_id = fields.Many2one('machine.cnc', 'Machine', required=True)
    of_ids = fields.One2many('ordre.fabrication', 'bloc_id', 'OF')
    date_debut = fields.Datetime('Début')
    date_fin = fields.Datetime('Fin')
    duree_totale = fields.Float('Durée (min)')
    capacite_outils_utilisee = fields.Integer('Outils Utilisés')
    state = fields.Selection([('draft', 'Brouillon'), ('planned', 'Planifié'), ('done', 'Terminé')], default='draft')


class PlanningTimeline(models.Model):
    _name = 'planning.timeline'
    _description = 'Timeline de Planification'
    
    planificateur_id = fields.Many2one('planificateur.cnc', 'Planificateur', ondelete='cascade')
    of_id = fields.Many2one('ordre.fabrication', 'OF')
    operation_id = fields.Many2one('operation.fabrication', 'Opération')
    machine_id = fields.Many2one('machine.cnc', 'Machine')
    date_debut = fields.Datetime('Début', required=True)
    date_fin = fields.Datetime('Fin', required=True)
    duree = fields.Float('Durée (min)')
    type_activite = fields.Selection([
        ('setup', 'Setup'), 
        ('production', 'Production'),
        ('transfert', 'Transfert')
    ], required=True)