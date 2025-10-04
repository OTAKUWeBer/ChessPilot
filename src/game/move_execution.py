import time
import logging
from executor.move_piece import move_piece
from executor.chess_notation_to_index import chess_notation_to_index
from executor.move_cursor_to_button import move_cursor_to_button

logger = logging.getLogger(__name__)

class MoveExecutor:
    @staticmethod
    def execute_move(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode):
        logger.debug(f"Executing move: {move}")
        move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play, move_mode)
        time.sleep(0.1)

    @staticmethod
    def convert_move_to_indices(color_indicator, root, auto_mode_var, move):
        logger.debug(f"Converting move to indices: {move}")
        return chess_notation_to_index(color_indicator, root, auto_mode_var, move)

    @staticmethod
    def relocate_cursor_to_button(root, auto_mode_var, btn_play):
        logger.debug("Relocating cursor to Play button")
        move_cursor_to_button(root, auto_mode_var, btn_play)
