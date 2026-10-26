import logging
import time
import os
import pyautogui
import random
from board_detection import get_positions, get_fen_from_position
from utils.system_interaction import capture_screenshot_in_memory, is_wayland

if os.name == 'nt':
    import win32api
    import win32con

logger = logging.getLogger(__name__)

PIECE_CLASS_IDS = {
    0: 'p', 1: 'r', 2: 'n', 3: 'b', 4: 'q', 5: 'k',
    6: 'P', 7: 'R', 8: 'N', 9: 'B', 10: 'Q', 11: 'K',
    12: 'board',
}

PROMOTION_PIECE_IDS = [10, 7, 9, 8]
PROMOTION_PIECE_IDS_BLACK = [4, 1, 3, 2]

def detect_promotion_pieces(boxes, chessboard_box, color_indicator):
    try:
        chessboard_x = chessboard_box[0]
        chessboard_y = chessboard_box[1]
        chessboard_width = chessboard_box[2]
        square_size = chessboard_width / 8.0
        
        promotion_boxes = []
        target_promotion_ids = PROMOTION_PIECE_IDS if color_indicator == 'w' else PROMOTION_PIECE_IDS_BLACK
        
        for box in boxes:
            x, y, w, h, confidence, class_id = box
            
            if int(class_id) in target_promotion_ids and confidence > 0.4:
                center_x = x + w / 2
                center_y = y + h / 2
                rel_x = center_x - chessboard_x
                rel_y = center_y - chessboard_y
                
                if -square_size < rel_x < (chessboard_width + square_size) and \
                   -square_size < rel_y < (chessboard_width + square_size):
                    
                    file_index = int(rel_x // square_size)
                    row_index = int(rel_y // square_size)
                    
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
        return promotion_boxes
    except Exception as e:
        logger.error(f"Error detecting promotion pieces: {e}", exc_info=True)
        return []

def find_promotion_dialog_pieces(boxes, chessboard_box, color_indicator):
    promotion_pieces = detect_promotion_pieces(boxes, chessboard_box, color_indicator)
    promotion_pieces.sort(key=lambda p: (p['position'][1], p['position'][0]))
    return promotion_pieces[:4]

def select_promotion_piece(piece_position, move_mode="drag", humanize=True, offset_range=(-8, 8), root=None, auto_mode_var=None):
    try:
        x, y = piece_position
        if humanize and offset_range:
            min_off, max_off = offset_range
            if min_off > max_off:
                min_off, max_off = max_off, min_off
            x += random.uniform(min_off, max_off)
            y += random.uniform(min_off, max_off)
        
        if os.name == 'nt':
            win32api.SetCursorPos((int(round(x)), int(round(y))))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif is_wayland():
            from wayland_capture.wayland import WaylandInput
            client = WaylandInput()
            client.click(int(round(x)), int(round(y)), button="left")
        else:
            pyautogui.click(x, y)
        
        time.sleep(0.1)
        return True
    
    except Exception as e:
        logger.error(f"Failed to select promotion piece: {e}")
        return False

def is_pawn_promotion_move(move_notation):
    if move_notation and len(move_notation) == 5 and move_notation[4] in ['q', 'r', 'b', 'n', 'Q', 'R', 'B', 'N']:
        return True
    return False

def get_promotion_piece_from_move(move_notation):
    if move_notation and len(move_notation) == 5:
        return move_notation[4].lower()
    return None

def is_promotion_dialog_visible(boxes, chessboard_box, color_indicator, min_pieces=4):
    promotion_pieces = detect_promotion_pieces(boxes, chessboard_box, color_indicator)
    return len(promotion_pieces) >= min_pieces

def wait_for_promotion_dialog(color_indicator, max_wait_time=1.5, check_interval=0.15):
    elapsed = 0
    while elapsed < max_wait_time:
        try:
            img = capture_screenshot_in_memory()
            if not img:
                time.sleep(check_interval)
                elapsed += check_interval
                continue
            
            boxes = get_positions(img)
            if not boxes:
                time.sleep(check_interval)
                elapsed += check_interval
                continue
            
            chessboard_boxes = [box for box in boxes if box[5] == 12.0]
            if not chessboard_boxes:
                time.sleep(check_interval)
                elapsed += check_interval
                continue
            
            chessboard_box = chessboard_boxes[0]
            if is_promotion_dialog_visible(boxes, chessboard_box, color_indicator, min_pieces=4):
                return boxes, chessboard_box
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        except Exception as e:
            time.sleep(check_interval)
            elapsed += check_interval
    
    return None

def handle_pawn_promotion(
    color_indicator, move, board_positions, chessboard_data=None,
    auto_mode_var=None, root=None, move_mode="drag", humanize=True, max_retries=2
):
    if not is_pawn_promotion_move(move):
        return False
    
    promotion_piece = get_promotion_piece_from_move(move)
    dialog_result = wait_for_promotion_dialog(color_indicator, max_wait_time=1.5, check_interval=0.15)
    
    if not dialog_result:
        return False
    
    boxes, chessboard_box = dialog_result
    
    for attempt in range(max_retries):
        try:
            promotion_pieces = find_promotion_dialog_pieces(boxes, chessboard_box, color_indicator)
            if len(promotion_pieces) < 4:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    dialog_result = wait_for_promotion_dialog(color_indicator, max_wait_time=0.5, check_interval=0.1)
                    if dialog_result:
                        boxes, chessboard_box = dialog_result
                    continue
                else:
                    break
            
            selected_piece = None
            for piece in promotion_pieces:
                if piece['piece_char'].lower() == promotion_piece:
                    selected_piece = piece
                    break
            
            if not selected_piece:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
                    continue
                else:
                    break
            
            if select_promotion_piece(
                selected_piece['position'],
                move_mode=move_mode,
                humanize=humanize,
                offset_range=(-8, 8),
                root=root,
                auto_mode_var=auto_mode_var
            ):
                return True
            time.sleep(0.2)
        except Exception as e:
            time.sleep(0.2)
    return False
