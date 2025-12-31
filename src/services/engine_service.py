import logging
from executor.get_best_move import (
    get_best_move,
    initialize_engine_at_startup,
    cleanup_engine
)

logger = logging.getLogger(__name__)

class EngineService:
    @staticmethod
    def initialize():
        logger.info("Initializing engine service")
        return initialize_engine_at_startup()

    @staticmethod
    def cleanup():
        logger.info("Cleaning up engine service")
        cleanup_engine()

    @staticmethod
    def get_best_move(depth: int, fen: str, root=None, auto_mode_var=None):
        logger.debug(f"Querying best move for FEN: {fen} at depth {depth}")
        return get_best_move(depth, fen, root, auto_mode_var)
