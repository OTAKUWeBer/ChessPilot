import logging
import time
import os
import pyautogui
import random
from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from .is_wayland import is_wayland
from wayland_capture.wayland import WaylandInput

if os.name == 'nt':
    import win32api
    import win32con

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Piece class IDs from ONNX model
PIECE_CLASS_IDS = {
    0: 'p',   # black pawn
    1: 'r',   # black rook
    2: 'n',   # black knight
    3: 'b',   # black bishop
    4: 'q',   # black queen
    5: 'k',   # black king
    6: 'P',   # white pawn
    7: 'R',   # white rook
    8: 'N',   # white knight
    9: 'B',   # white bishop
    10: 'Q',  # white queen
    11: 'K',  # white king
    12: 'board',  # chessboard
}

# Promotion piece class IDs (Queen, Rook, Bishop, Knight)
PROMOTION_PIECE_IDS = [10, 7, 9, 8]  # Q, R, B, N (uppercase - white pieces)
PROMOTION_PIECE_IDS_BLACK = [4, 1, 3, 2]  # q, r, b, n (lowercase - black pieces)

def detect_promotion_pieces(boxes, chessboard_box, color_indicator):
    """
    Detect promotion pieces on the board.
    Returns list of detected promotion pieces with their positions and class info.
    """
    try:
        chessboard_x = chessboard_box[0]
        chessboard_y = chessboard_box[1]
        chessboard_width = chessboard_box[2]
        square_size = chessboard_width / 8.0
        
        # Filter boxes to find promotion pieces
        # Promotion pieces are typically displayed on or near the promotion rank
        promotion_boxes = []
        
        # Determine which piece IDs to look for based on color
        if color_indicator == 'w':
            target_promotion_ids = PROMOTION_PIECE_IDS
        else:
            target_promotion_ids = PROMOTION_PIECE_IDS_BLACK
        
        for box in boxes:
            x, y, w, h, confidence, class_id = box
            
            # Look for promotion pieces with reasonable confidence
            if int(class_id) in target_promotion_ids and confidence > 0.4:
                # Check if piece is on the board or near promotion rank
                center_x = x + w / 2
                center_y = y + h / 2
                
                # Calculate relative position to chessboard
                rel_x = center_x - chessboard_x
                rel_y = center_y - chessboard_y
                
                # Check if within board bounds
                if -square_size < rel_x < (chessboard_width + square_size) and \
                   -square_size < rel_y < (chessboard_width + square_size):
                    
                    file_index = int(rel_x // square_size)
                    row_index = int(rel_y // square_size)
                    
                    # Check if it's in valid promotion area
                    # White promotes on rank 8 (row_index 0), Black on rank 1 (row_index 7)
                    is_promotion_rank = (color_indicator == 'w' and row_index == 0) or \
                                       (color_indicator == 'b' and row_index == 7)
                    
                    promotion_boxes.append({
                        'box': box,
                        'class_id': int(class_id),
                        'confidence': confidence,
                        'position': (center_x, center_y),
                        'file': file_index if 0 <= file_index < 8 else None,
                        'rank': row_index if 0 <= row_index < 8 else None,
                        'is_promotion_rank': is_promotion_rank,
                        'piece_char': PIECE_CLASS_IDS.get(int(class_id), '?')
                    })
        
        logger.debug(f"Detected {len(promotion_boxes)} potential promotion pieces for {color_indicator}")
        return promotion_boxes
    
    except Exception as e:
        logger.error(f"Error detecting promotion pieces: {e}", exc_info=True)
        return []


def find_promotion_dialog_pieces(boxes, chessboard_box, color_indicator):
    """
    Find promotion pieces in a promotion dialog (typically 4 pieces shown).
    Returns the 4 pieces (Queen, Rook, Bishop, Knight) in order by their position.
    """
    promotion_pieces = detect_promotion_pieces(boxes, chessboard_box, color_indicator)
    
    if len(promotion_pieces) < 4:
        logger.warning(f"Expected 4 promotion pieces, found {len(promotion_pieces)}")
    
    # Sort by position (left to right, top to bottom)
    promotion_pieces.sort(key=lambda p: (p['position'][1], p['position'][0]))
    
    logger.debug(f"Sorted promotion pieces: {[p['piece_char'] for p in promotion_pieces]}")
    return promotion_pieces[:4]  # Return up to 4 pieces


def select_promotion_piece(piece_position, move_mode="drag", humanize=True, offset_range=(-8, 8), root=None, auto_mode_var=None):
    """
    Click on a promotion piece to select it.
    """
    try:
        x, y = piece_position
        
        # Apply humanize offsets
        if humanize and offset_range:
            min_off, max_off = offset_range
            if min_off > max_off:
                min_off, max_off = max_off, min_off
            x += random.uniform(min_off, max_off)
            y += random.uniform(min_off, max_off)
        
        logger.debug(f"Clicking promotion piece at ({x}, {y})")
        
        if os.name == 'nt':
            win32api.SetCursorPos((int(round(x)), int(round(y))))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif is_wayland():
            client = WaylandInput()
            client.click(int(round(x)), int(round(y)), button="left")
        else:
            pyautogui.click(x, y)
        
        time.sleep(0.1)  # Wait for selection to register
        logger.info("Promotion piece selected successfully")
        return True
    
    except Exception as e:
        logger.error(f"Failed to select promotion piece: {e}")
        return False


def is_pawn_promotion_move(move_notation):
    """
    Check if a move is a pawn promotion move.
    Promotion moves have format like 'e7e8q' or 'a2a1r'
    """
    # Pawn promotion moves in UCI format have 5 characters: source (2) + dest (2) + promotion piece (1)
    if len(move_notation) == 5 and move_notation[4] in ['q', 'r', 'b', 'n', 'Q', 'R', 'B', 'N']:
        return True
    return False


def get_promotion_piece_from_move(move_notation):
    """
    Extract the promotion piece from move notation.
    """
    if len(move_notation) == 5:
        return move_notation[4].lower()  # q, r, b, n
    return None


def is_promotion_dialog_visible(boxes, chessboard_box, color_indicator, min_pieces=4):
    """
    Check if promotion dialog is visible by detecting if at least min_pieces promotion pieces are present.
    New function to confirm promotion dialog appeared before selecting piece.
    """
    promotion_pieces = detect_promotion_pieces(boxes, chessboard_box, color_indicator)
    return len(promotion_pieces) >= min_pieces


def wait_for_promotion_dialog(color_indicator, max_wait_time=1.5, check_interval=0.15):
    """
    Wait for promotion dialog to appear after a pawn reaches promotion rank.
    New function to wait and confirm promotion dialog is visible.
    
    Args:
        color_indicator: 'w' for white, 'b' for black
        max_wait_time: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
    
    Returns:
        Tuple of (boxes, chessboard_box) if dialog found, None otherwise
    """
    elapsed = 0
    
    while elapsed < max_wait_time:
        try:
            img = capture_screenshot_in_memory()
            if not img:
                logger.debug(f"Screenshot failed, waiting... ({elapsed:.2f}s)")
                time.sleep(check_interval)
                elapsed += check_interval
                continue
            
            boxes = get_positions(img)
            if not boxes:
                logger.debug(f"Board detection failed, waiting... ({elapsed:.2f}s)")
                time.sleep(check_interval)
                elapsed += check_interval
                continue
            
            # Find chessboard
            chessboard_boxes = [box for box in boxes if box[5] == 12.0]
            if not chessboard_boxes:
                logger.debug(f"Chessboard not detected, waiting... ({elapsed:.2f}s)")
                time.sleep(check_interval)
                elapsed += check_interval
                continue
            
            chessboard_box = chessboard_boxes[0]
            
            # Check if promotion dialog is visible
            if is_promotion_dialog_visible(boxes, chessboard_box, color_indicator, min_pieces=4):
                logger.info(f"Promotion dialog detected after {elapsed:.2f}s")
                return boxes, chessboard_box
            
            logger.debug(f"Promotion dialog not yet visible, waiting... ({elapsed:.2f}s)")
            time.sleep(check_interval)
            elapsed += check_interval
        
        except Exception as e:
            logger.debug(f"Error checking for promotion dialog: {e}")
            time.sleep(check_interval)
            elapsed += check_interval
    
    logger.warning(f"Promotion dialog did not appear within {max_wait_time}s")
    return None


def handle_pawn_promotion(
    color_indicator, move, board_positions, chessboard_data,
    auto_mode_var, root, move_mode, humanize=True, max_retries=2
):
    """
    Handle pawn promotion by detecting promotion pieces and selecting the appropriate one.
    Updated to wait for promotion dialog to appear before selecting piece.
    
    Args:
        color_indicator: 'w' for white, 'b' for black
        move: Move in UCI format (e.g., 'e7e8q')
        board_positions: Dictionary of board square positions
        chessboard_data: Dictionary containing chessboard_x, chessboard_y, square_size, fen
        auto_mode_var: Auto mode variable
        root: Root window
        move_mode: 'drag' or 'click'
        humanize: Whether to add random offsets
        max_retries: Maximum number of retry attempts
    
    Returns:
        True if promotion was successful, False otherwise
    """
    
    if not is_pawn_promotion_move(move):
        logger.debug(f"Move {move} is not a promotion move")
        return False
    
    promotion_piece = get_promotion_piece_from_move(move)
    logger.info(f"Handling pawn promotion to {promotion_piece.upper()} for move {move}")
    
    logger.info("Waiting for promotion dialog to appear...")
    dialog_result = wait_for_promotion_dialog(color_indicator, max_wait_time=1.5, check_interval=0.15)
    
    if not dialog_result:
        logger.error("Promotion dialog did not appear within timeout")
        return False
    
    boxes, chessboard_box = dialog_result
    
    # Now that we've confirmed the dialog is visible, select the piece
    for attempt in range(max_retries):
        try:
            # Find promotion pieces
            promotion_pieces = find_promotion_dialog_pieces(boxes, chessboard_box, color_indicator)
            if len(promotion_pieces) < 4:
                logger.warning(f"Could not find all 4 promotion pieces (found {len(promotion_pieces)})")
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    # Re-capture and try again
                    dialog_result = wait_for_promotion_dialog(color_indicator, max_wait_time=0.5, check_interval=0.1)
                    if dialog_result:
                        boxes, chessboard_box = dialog_result
                    continue
                else:
                    break
            
            # Find the piece matching our promotion choice
            selected_piece = None
            for piece in promotion_pieces:
                if piece['piece_char'].lower() == promotion_piece:
                    selected_piece = piece
                    break
            
            if not selected_piece:
                logger.warning(f"Could not find promotion piece '{promotion_piece}' in detected pieces")
                logger.debug(f"Available pieces: {[p['piece_char'] for p in promotion_pieces]}")
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                else:
                    break
            
            logger.debug(f"Selected promotion piece: {selected_piece['piece_char']} at position {selected_piece['position']}")
            
            # Click on the promotion piece
            if select_promotion_piece(
                selected_piece['position'],
                move_mode=move_mode,
                humanize=humanize,
                offset_range=(-8, 8),
                root=root,
                auto_mode_var=auto_mode_var
            ):
                logger.info(f"Promotion piece selected successfully on attempt {attempt + 1}")
                return True
            
            time.sleep(0.2)
        
        except Exception as e:
            logger.error(f"Error handling pawn promotion on attempt {attempt + 1}: {e}", exc_info=True)
            time.sleep(0.2)
    
    logger.error(f"Failed to handle pawn promotion after {max_retries} attempts")
    return False
