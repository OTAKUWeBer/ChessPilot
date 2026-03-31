import time
import logging
from board_detection import get_positions, get_fen_from_position
from utils.system_interaction import capture_screenshot_in_memory
from core.board_utils import fen_to_list, algebraic_to_index

logger = logging.getLogger(__name__)

class MoveValidator:
    @staticmethod
    def did_my_piece_move(color_indicator, before_fen: str, after_fen: str, move: str) -> bool:
        """
        Return True iff the only change between before_fen and after_fen
        is that *your* piece moved from move[0:2] → move[2:4].
        """
        logger.debug(f"Checking move: {move} for color: {color_indicator}")
        
        before_list = fen_to_list(before_fen)
        after_list = fen_to_list(after_fen)

        start_i = algebraic_to_index(move[0:2])
        end_i = algebraic_to_index(move[2:4])
        my_pieces = 'PNBRQK' if color_indicator == 'w' else 'pnbrqk'

        piece_char = before_list[start_i]
        logger.debug(f"Piece at start square: '{piece_char}'")

        moved_from = (piece_char in my_pieces) and (after_list[start_i] == ' ')
        after_char = after_list[end_i]
        
        is_promotion = len(move) == 5 and piece_char in ('P', 'p')
        if is_promotion:
            promotion_piece = move[4].upper()
            promotion_piece_color = promotion_piece if color_indicator == 'w' else promotion_piece.lower()
            moved_to = (after_char == promotion_piece_color)
            logger.debug(f"Promotion move detected: {piece_char} → {promotion_piece_color}")
        else:
            moved_to = (after_char == piece_char)
        
        logger.debug(f"After piece at end square: '{after_char}'")

        unchanged_elsewhere = all(
            (b == a) or idx in (start_i, end_i)
            for idx, (b, a) in enumerate(zip(before_list, after_list))
        )
        logger.debug(f"moved_from={moved_from}, moved_to={moved_to}, unchanged_elsewhere={unchanged_elsewhere}")

        if moved_from and moved_to and unchanged_elsewhere:
            logger.info(f"Valid move detected: {move}")
            return True
        else:
            logger.warning("Move check failed")
            return False

    @staticmethod
    def did_castling_move(color_indicator, before_fen: str, after_fen: str, king_move: str, rook_move: str) -> bool:
        """
        Verify that a castling move was executed correctly.
        """
        logger.debug(f"Checking castling: King {king_move}, Rook {rook_move} for color: {color_indicator}")
        
        before_list = fen_to_list(before_fen)
        after_list = fen_to_list(after_fen)

        king_start_i = algebraic_to_index(king_move[0:2])
        king_end_i = algebraic_to_index(king_move[2:4])
        
        rook_start_i = algebraic_to_index(rook_move[0:2])
        rook_end_i = algebraic_to_index(rook_move[2:4])
        
        my_pieces = 'PNBRQK' if color_indicator == 'w' else 'pnbrqk'
        
        king_char = before_list[king_start_i]
        rook_char = before_list[rook_start_i]
        
        logger.debug(f"King at start: '{king_char}', Rook at start: '{rook_char}'")
        
        king_moved_from = (king_char in my_pieces) and (after_list[king_start_i] == ' ')
        king_moved_to = (after_list[king_end_i] == king_char)
        
        rook_moved_from = (rook_char in my_pieces) and (after_list[rook_start_i] == ' ')
        rook_moved_to = (after_list[rook_end_i] == rook_char)
        
        logger.debug(f"After - King at end: '{after_list[king_end_i]}', Rook at end: '{after_list[rook_end_i]}'")
        
        if king_moved_from and king_moved_to and rook_moved_from and rook_moved_to:
            logger.info(f"Valid castling detected: King {king_move}, Rook {rook_move}")
            return True
        else:
            logger.warning("Castling verification failed")
            return False

    @staticmethod
    def check_move_validity(color_indicator, before_fen: str, after_fen: str, move: str):
        logger.debug(f"Verifying move validity: {move}")
        return MoveValidator.did_my_piece_move(color_indicator, before_fen, after_fen, move)

    @staticmethod
    def verify_move(color_indicator, _, expected_fen: str, attempts_limit: int = 3):
        """
        Verify that a move was executed successfully by checking the board state.
        Returns (success: bool, attempts_used: int)
        """
        expected_pieces = expected_fen.split()[0]
        logger.debug(f"Starting move verification for color {color_indicator} with expected pieces: {expected_pieces}")
        
        for attempt in range(1, attempts_limit + 1):
            if attempt > 1:
                time.sleep(0.5)
                logger.debug(f"Retrying verification attempt {attempt}/{attempts_limit}")
                
            screenshot = capture_screenshot_in_memory()
            if not screenshot:
                logger.warning(f"Attempt {attempt}: Screenshot capture failed")
                continue
            
            boxes = get_positions(screenshot)
            if not boxes:
                logger.warning(f"Attempt {attempt}: Board detection failed - no objects detected")
                continue
            
            chessboard_detected = any(box[5] == 12.0 for box in boxes)
            if not chessboard_detected:
                logger.warning(f"Attempt {attempt}: No chessboard detected (class_id 12.0 not found)")
                continue
            
            try:
                result = get_fen_from_position(color_indicator, boxes)
                if result is None:
                    logger.warning(f"Attempt {attempt}: FEN extraction returned None")
                    continue
                    
                _, _, _, current_fen = result
                fen_parts = current_fen.split()
                logger.debug(f"Attempt {attempt}: Current FEN = {current_fen}")
                
                if len(fen_parts) > 1 and fen_parts[1] != color_indicator:
                    logger.info(f"Attempt {attempt}: Active color changed, move verified successfully")
                    return True, attempt
                
                if fen_parts[0] == expected_pieces:
                    logger.info(f"Attempt {attempt}: Board position matches expected pieces, move verified successfully")
                    return True, attempt
                    
            except (ValueError, TypeError) as e:
                logger.error(f"Attempt {attempt}: Error parsing FEN - {e}")
            except Exception as e:
                logger.error(f"Attempt {attempt}: Unexpected error - {e}")
        
        logger.error(f"Move verification failed after {attempts_limit} attempts")
        logger.error("This may indicate:")
        logger.error("  1. Board detection model not working properly")
        logger.error("  2. Screenshot not capturing the chess board")
        logger.error("  3. Board animation still in progress")
        return False, attempts_limit
