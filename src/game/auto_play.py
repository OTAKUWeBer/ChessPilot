import logging
from executor.auto_move import auto_move_loop

logger = logging.getLogger(__name__)

class AutoPlayController:
    @staticmethod
    def start_auto_play(
        root, color_indicator, auto_mode_var, btn_play, move_mode,
        board_positions, last_fen_by_color, screenshot_delay_var,
        update_status_callback, kingside_var, queenside_var, update_last_fen_for_color
    ):
        logger.info("Starting auto play controller")
        auto_move_loop(
            root, color_indicator, auto_mode_var, btn_play, move_mode,
            board_positions, last_fen_by_color, screenshot_delay_var,
            update_status_callback, kingside_var, queenside_var, update_last_fen_for_color
        )
