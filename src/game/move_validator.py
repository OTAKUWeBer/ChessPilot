import logging
from executor.did_my_piece_move import did_my_piece_move
from executor.verify_move import verify_move

logger = logging.getLogger(__name__)

class MoveValidator:
    @staticmethod
    def check_move_validity(color_indicator, before_fen: str, after_fen: str, move: str):
        logger.debug(f"Verifying move validity: {move}")
        return did_my_piece_move(color_indicator, before_fen, after_fen, move)

    @staticmethod
    def verify_move(color_indicator, before_fen: str, expected_fen: str, attempts_limit: int = 3):
        logger.debug(f"Verifying move; expected FEN: {expected_fen}")
        return verify_move(color_indicator, before_fen, expected_fen, attempts_limit)
