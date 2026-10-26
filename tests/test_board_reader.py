import sys
from pathlib import Path
import unittest

src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from board_detection.model_classes import (
    CLASS_TO_FEN,
    CHESSBOARD_CLASS_ID,
    PROMOTION_PIECE_IDS,
    PROMOTION_PIECE_IDS_BLACK,
)
from board_detection.get_positions import get_session


class TestBoardDetectionAndModelClasses(unittest.TestCase):
    def test_model_constants(self):
        self.assertEqual(CHESSBOARD_CLASS_ID, 12.0)
        self.assertEqual(CLASS_TO_FEN[0], 'p')
        self.assertEqual(CLASS_TO_FEN[10], 'Q')
        self.assertEqual(CLASS_TO_FEN[11], 'K')
        self.assertIn(10, PROMOTION_PIECE_IDS)  # White Queen
        self.assertIn(4, PROMOTION_PIECE_IDS_BLACK)  # Black Queen

    def test_onnx_session_lazily_loads(self):
        onnx_model_path = src_dir / "chess_detection.onnx"
        if not onnx_model_path.exists():
            self.skipTest("chess_detection.onnx not found in src/")

        session, input_name, output_name = get_session()
        self.assertIsNotNone(session)
        self.assertIsNotNone(input_name)
        self.assertIsNotNone(output_name)


if __name__ == "__main__":
    unittest.main()
