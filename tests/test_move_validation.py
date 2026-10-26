import sys
from pathlib import Path
import unittest

src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from game.move_validator import MoveValidator
from game.promotion import is_pawn_promotion_move, get_promotion_piece_from_move


class TestMoveValidation(unittest.TestCase):
    def test_normal_pawn_move(self):
        before = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        after = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        self.assertTrue(MoveValidator.did_my_piece_move("w", before, after, "e2e4"))

    def test_piece_move(self):
        before = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        after = "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1"
        self.assertTrue(MoveValidator.did_my_piece_move("w", before, after, "g1f3"))

    def test_en_passant(self):
        before_ep = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
        after_ep = "rnbqkbnr/ppp1pppp/3P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3"
        self.assertTrue(MoveValidator.did_my_piece_move("w", before_ep, after_ep, "e5d6"))

    def test_promotion_move(self):
        before_prom = "8/4P3/8/8/8/8/8/4K2k w - - 0 1"
        after_prom = "4Q3/8/8/8/8/8/8/4K2k b - - 0 1"
        self.assertTrue(MoveValidator.did_my_piece_move("w", before_prom, after_prom, "e7e8q"))

    def test_castling_moves(self):
        before = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        after_wk = "r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1"
        self.assertTrue(MoveValidator.did_castling_move("w", before, after_wk, "e1g1", "h1f1"))

        after_wq = "r3k2r/8/8/8/8/8/8/2KR3R b kq - 1 1"
        self.assertTrue(MoveValidator.did_castling_move("w", before, after_wq, "e1c1", "a1d1"))

    def test_promotion_helpers(self):
        self.assertTrue(is_pawn_promotion_move("e7e8q"))
        self.assertTrue(is_pawn_promotion_move("a2a1r"))
        self.assertFalse(is_pawn_promotion_move("e2e4"))
        self.assertFalse(is_pawn_promotion_move(None))
        self.assertEqual(get_promotion_piece_from_move("e7e8q"), "q")
        self.assertEqual(get_promotion_piece_from_move("e7e8R"), "r")
        self.assertIsNone(get_promotion_piece_from_move("e2e4"))


if __name__ == "__main__":
    unittest.main()
