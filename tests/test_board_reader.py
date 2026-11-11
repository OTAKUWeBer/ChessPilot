import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from PIL import Image

src_dir = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_dir))

from board_detection.model_classes import (
    CLASS_TO_FEN,
    CHESSBOARD_CLASS_ID,
    PROMOTION_PIECE_IDS,
    PROMOTION_PIECE_IDS_BLACK,
)
from board_detection.get_positions import get_positions, get_session
from board_detection.fen_extractor import get_fen_from_position
from game.move_processor import _extract_board_position


class TestFenExtraction(unittest.TestCase):
    def setUp(self):
        self.board = [0, 0, 800, 800, 0.99, CHESSBOARD_CLASS_ID]
        self.black_king = [410, 10, 80, 80, 0.95, 5]
        self.white_king = [410, 710, 80, 80, 0.95, 11]
        self.valid_boxes = [self.board, self.black_king, self.white_king]

    def test_accepts_endgame_in_both_orientations(self):
        for color, expected in (
            ('w', '4k3/8/8/8/8/8/8/4K3 w - - 0 1'),
            ('b', '3K4/8/8/8/8/8/8/3k4 b - - 0 1'),
        ):
            with self.subTest(color=color):
                self.assertEqual(
                    get_fen_from_position(color, self.valid_boxes),
                    (0, 0, 100, expected),
                )

    def test_rejects_missing_duplicate_kings_and_unknown_pieces(self):
        for boxes in (
            [self.board],
            [self.board, self.black_king],
            [self.board, self.white_king],
            self.valid_boxes + [[510, 10, 80, 80, 0.95, 5]],
            self.valid_boxes + [[510, 710, 80, 80, 0.95, 11]],
            self.valid_boxes + [[10, 110, 80, 80, 0.95, 99]],
            # A higher-confidence piece can overwrite a detected king's square.
            self.valid_boxes + [[410, 10, 80, 80, 0.99, 4]],
        ):
            for color in ('w', 'b'):
                with self.subTest(boxes=boxes, color=color):
                    self.assertIsNone(get_fen_from_position(color, boxes))

    def test_board_read_retries_invalid_detections(self):
        invalid_boxes = [self.board, [10, 110, 80, 80, 0.95, 0]]
        for detections, succeeds in (
            ([invalid_boxes, self.valid_boxes], True),
            ([invalid_boxes] * 3, False),
        ):
            with self.subTest(succeeds=succeeds), \
                    patch('game.move_processor.capture_screenshot_in_memory', return_value=object()) as capture, \
                    patch('game.move_processor.get_positions', side_effect=detections), \
                    patch('game.move_processor.time.sleep'), \
                    patch('game.move_processor.QTimer.singleShot', side_effect=lambda _, callback: callback()):
                status = Mock()
                result = _extract_board_position(None, False, 'b', status)
                self.assertEqual(capture.call_count, len(detections))
                if succeeds:
                    self.assertEqual(result['fen'], '3K4/8/8/8/8/8/8/3k4 b - - 0 1')
                else:
                    self.assertIsNone(result)
                    self.assertIn('both kings visible', status.call_args.args[0])

    def test_successful_detection_skips_refined_search(self):
        with patch('board_detection.get_positions.predict', return_value=self.valid_boxes) as predict:
            self.assertEqual(get_positions(Image.new('RGB', (800, 800))), self.valid_boxes)
            predict.assert_called_once()

    def test_promotion_detection_can_read_raw_boxes(self):
        with patch('board_detection.get_positions.predict', return_value=[self.board]) as predict:
            self.assertEqual(
                get_positions(Image.new('RGB', (800, 800)), refined_search=False),
                [self.board],
            )
            predict.assert_called_once()

    def test_refined_search_preserves_screen_coordinates(self):
        image = Image.new('RGB', (2400, 1600))
        for tiled in (False, True):
            with self.subTest(tiled=tiled):
                local_boxes = [[box[0] + 40, box[1] + 40, *box[2:]] for box in self.valid_boxes]
                if tiled:
                    # The second tile starts at x=600; its board starts at x=200.
                    outputs = [[], [], [[200, 100, 800, 800, 0.99, 12]], local_boxes]
                else:
                    outputs = [[[800, 100, 800, 800, 0.99, 12]], local_boxes]
                with patch('board_detection.get_positions.predict', side_effect=outputs) as predict:
                    result = get_positions(image)
                    self.assertEqual(result[0][:4], [800, 100, 800, 800])
                    self.assertEqual(result[1][:2], [1210, 110])
                    self.assertEqual(result[2][:2], [1210, 810])
                    self.assertIsNotNone(get_fen_from_position('b', result))
                    self.assertEqual(predict.call_args.args[0].size, (880, 880))
                    self.assertEqual(predict.call_count, len(outputs))

    def test_failed_refined_search_returns_detection_error(self):
        with patch('board_detection.get_positions.predict', return_value=[]) as predict:
            with self.assertLogs('board_detection.get_positions', level='WARNING') as logs:
                self.assertIsNone(get_positions(Image.new('RGB', (2400, 1600))))
            self.assertEqual(predict.call_count, 10)  # One full image and nine tiles.
            self.assertIn('normal and refined search', logs.output[-1])


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
