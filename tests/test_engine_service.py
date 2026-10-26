import sys
import os
from pathlib import Path
import unittest

src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.engine_service import EngineService, get_config_file_path


class TestEngineService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stockfish_exists = (src_dir / "stockfish.exe").exists()

    def setUp(self):
        if not self.stockfish_exists:
            self.skipTest("stockfish.exe not found in src/")

    def tearDown(self):
        EngineService.cleanup()

    def test_engine_initialization_and_cleanup(self):
        ok = EngineService.initialize()
        self.assertTrue(ok)
        EngineService.cleanup()

    def test_engine_best_move_standard_opening(self):
        start_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        best_move, updated_fen, mate_flag = EngineService.get_best_move(depth=5, fen=start_fen)
        self.assertIsNotNone(best_move)
        self.assertNotEqual(best_move, "(none)")
        self.assertEqual(len(best_move), 4)  # e.g., 'e2e4'
        self.assertIsNotNone(updated_fen)
        self.assertFalse(mate_flag)

    def test_engine_checkmate_position(self):
        # Fool's mate position: 1. f3 e5 2. g4 Qh4# (White is checkmated)
        checkmate_fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
        best_move, updated_fen, mate_flag = EngineService.get_best_move(depth=5, fen=checkmate_fen)
        # In a checkmated position, Stockfish returns (none)
        self.assertEqual(best_move, "(none)")

    def test_get_config_file_path(self):
        cfg_path = get_config_file_path()
        self.assertIsInstance(cfg_path, str)
        self.assertTrue(cfg_path.endswith("engine_config.txt"))


if __name__ == "__main__":
    unittest.main()
