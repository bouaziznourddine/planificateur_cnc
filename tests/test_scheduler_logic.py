import unittest
from unittest.mock import MagicMock
import sys
import os
from datetime import datetime, timedelta

# Add the models directory to path so we can import the scheduler
sys.path.append(r"c:\Program Files (x86)\Odoo 12.0\server\addons\planificateur_cnc\models")

# Mock Odoo environment before importing
sys.modules['odoo'] = MagicMock()
sys.modules['odoo.models'] = MagicMock()
sys.modules['odoo.fields'] = MagicMock()
sys.modules['odoo.exceptions'] = MagicMock()

from genetic_algorithm_scheduler import GeneticAlgorithmScheduler, Individual

class TestGAScheduler(unittest.TestCase):
    def setUp(self):
        # Mock Machines
        self.machine1 = MagicMock()
        self.machine1.id = 1
        self.machine1.nom = "Machine A"
        self.machine1.capacite_magasin = 40
        
        self.machine2 = MagicMock()
        self.machine2.id = 2
        self.machine2.nom = "Machine B"
        self.machine2.capacite_magasin = 40
        
        self.machines = [self.machine1, self.machine2]
        
        # Mock OFs
        self.of1 = MagicMock()
        self.of1.id = 101
        self.of1.numero_of = "OF001"
        self.of1.quantite = 10
        self.of1.date_livraison = datetime.now() + timedelta(days=5)
        self.of1.priorite = 1
        self.of1.phase = '30' # OP1 + OP2
        self.of1.duree_chargement_machine_min = 5
        self.of1.duree_rotation_table_min = 2
        
        # Mock Type Piece & Operations
        self.op1 = MagicMock()
        self.op1.id = 1
        self.op1.temps_standard = 10.0 # 10 min/piece
        self.op1.outil_ids = MagicMock()
        self.op1.outil_ids.mapped.return_value = [1, 1] # 2 tools
        self.op1.outil_ids.ids = [10, 11]
        
        self.op2 = MagicMock()
        self.op2.id = 2
        self.op2.temps_standard = 5.0 # 5 min/piece
        self.op2.outil_ids = MagicMock()
        self.op2.outil_ids.mapped.return_value = [1] # 1 tool
        self.op2.outil_ids.ids = [12]
        
        self.type_piece = MagicMock()
        self.type_piece.nom = "Piece X"
        self.type_piece.operation_01_id = self.op1
        self.type_piece.operation_02_id = self.op2
        self.type_piece.montage_id.id = 50
        self.type_piece.palette_type = 'S'
        
        self.of1.type_piece_id = self.type_piece
        
        self.ofs = [self.of1]

    def test_initialization(self):
        ga = GeneticAlgorithmScheduler(self.ofs, self.machines)
        self.assertEqual(len(ga.tasks), 2) # OP1 and OP2
        self.assertIn((101, 'OP1'), ga.tasks)
        self.assertIn((101, 'OP2'), ga.tasks)
        
    def test_block_creation(self):
        ga = GeneticAlgorithmScheduler(self.ofs, self.machines)
        # Force a sequence
        seq = [(101, 'OP1'), (101, 'OP2')]
        blocks = ga._create_blocks(seq)
        # Should be 1 block if tools fit (2+1=3 < 40) and same montage (50)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(len(blocks[0]), 2)
        
    def test_block_break_on_montage(self):
        # Create another OF with different montage
        of2 = MagicMock()
        of2.id = 102
        of2.numero_of = "OF002"
        of2.quantite = 5
        of2.phase = '50' # OP1 only
        of2.duree_chargement_machine_min = 5
        of2.duree_rotation_table_min = 2
        
        tp2 = MagicMock()
        tp2.operation_01_id = self.op1
        tp2.operation_02_id = None
        tp2.montage_id.id = 51 # Different montage
        of2.type_piece_id = tp2
        
        ga = GeneticAlgorithmScheduler([self.of1, of2], self.machines)
        seq = [(101, 'OP1'), (102, 'OP1')]
        blocks = ga._create_blocks(seq)
        
        self.assertEqual(len(blocks), 2) # Should split because of montage
        
    def test_fitness_precedence(self):
        ga = GeneticAlgorithmScheduler(self.ofs, self.machines)
        
        # Case 1: OP1 then OP2 (Good)
        seq = [(101, 'OP1'), (101, 'OP2')]
        blocks = [[(101, 'OP1'), (101, 'OP2')]]
        ind = Individual(seq, [0], blocks) # Machine 0
        ga._evaluate_fitness(ind)
        
        # Duration:
        # OP1: 10*10 = 100
        # OP2: 5*10 = 50
        # Setup: 30
        # OP1 Start: 30 + 5(load) = 35. End: 35+100 = 135.
        # OP2 Start: max(135, 135 + 2(rot)) + 5(load) = 137 + 5 = 142. End: 142+50 = 192.
        # Makespan should be 192.
        
        print(f"Makespan Good: {ind.makespan}")
        self.assertGreater(ind.makespan, 190)

if __name__ == '__main__':
    unittest.main()
