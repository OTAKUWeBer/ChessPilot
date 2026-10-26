import sys
from pathlib import Path
import unittest

src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from core.notation import chess_notation_to_index
from core.board_utils import algebraic_to_index, fen_to_list, expand_row
from core.fen_utils import is_two_square_king_move, expand_fen_row, is_castling_possible


class TestFENAndNotation(unittest.TestCase):
    def test_notation_white(self):
        start, end = chess_notation_to_index("w", None, None, "e2e4")
        self.assertEqual(start, (4, 6))
        self.assertEqual(end, (4, 4))

    def test_notation_black(self):
        start, end = chess_notation_to_index("b", None, None, "e7e5")
        self.assertEqual(start, (3, 6))
        self.assertEqual(end, (3, 4))

    def test_notation_invalid(self):
        self.assertEqual(chess_notation_to_index("w", None, None, ""), (None, None))
        self.assertEqual(chess_notation_to_index("w", None, None, "e2"), (None, None))
        self.assertEqual(chess_notation_to_index("w", None, None, "(none)"), (None, None))

    def test_algebraic_to_index(self):
        self.assertEqual(algebraic_to_index("a8"), 0)
        self.assertEqual(algebraic_to_index("h1"), 63)
        self.assertEqual(algebraic_to_index("e4"), 36)
        self.assertEqual(algebraic_to_index(""), 0)
        self.assertEqual(algebraic_to_index(None), 0)

    def test_fen_to_list(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        board = fen_to_list(fen)
        self.assertEqual(len(board), 64)
        self.assertEqual(board[0], 'r')
        self.assertEqual(board[63], 'R')
        self.assertEqual(board[28], ' ')

    def test_two_square_king_move(self):
        fen_white = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        is_castle, side = is_two_square_king_move("e1g1", fen_white, "w")
        self.assertTrue(is_castle)
        self.assertEqual(side, "kingside")

        is_castle_q, side_q = is_two_square_king_move("e1c1", fen_white, "w")
        self.assertTrue(is_castle_q)
        self.assertEqual(side_q, "queenside")

        is_castle_none, _ = is_two_square_king_move("(none)", fen_white, "w")
        self.assertFalse(is_castle_none)


if __name__ == "__main__":
    unittest.main()
