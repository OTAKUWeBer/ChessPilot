import logging
from typing import Tuple
from board_detection import get_positions, get_fen_from_position
from utils.system_interaction import capture_screenshot_in_memory

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def expand_fen_row(row: str) -> str:
    expanded = ""
    for char in row:
        if char.isdigit():
            expanded += " " * int(char)
        else:
            expanded += char
    return expanded


def get_current_fen(color_indicator):
    try:
        screenshot = capture_screenshot_in_memory()
        boxes = get_positions(screenshot)
        if boxes:
            _, _, _, fen = get_fen_from_position(color_indicator, boxes)          
            return fen
    except Exception:
        logging.error("Failed to get current FEN", exc_info=True)
        return None


def is_castling_possible(fen: str, color: str, side: str) -> bool:
    board = fen.split()[0]
    rows = board.split('/')
    if color == "w":
        last_row = expand_fen_row(rows[-1])
        if len(last_row) != 8 or last_row[4] != 'K':
            logger.debug(f"Invalid last row for white castling: {last_row}")
            return False
        if side == 'kingside':
            logger.debug(f"Checking kingside castling for white: {last_row[7]}")
            return last_row[7] == 'R'
        elif side == 'queenside':
            logger.debug(f"Checking queenside castling for white: {last_row[0]}")
            return last_row[0] == 'R'
    else:
        first_row = expand_fen_row(rows[0])
        if len(first_row) != 8 or first_row[4] != 'k':
            logger.debug(f"Invalid first row for black castling: {first_row}")
            return False
        if side == 'kingside':
            logger.debug(f"Checking kingside castling for black: {first_row[7]}")
            return first_row[7] == 'r'
        elif side == 'queenside':
            logger.debug(f"Checking queenside castling for black: {first_row[0]}")
            return first_row[0] == 'r'
    return False


def is_two_square_king_move(move_str: str, current_fen: str, color: str) -> Tuple[bool, str]:
    """
    Return (True, side) if `move_str` is a legal castling-style king move
    from current_fen for this color.  side is either 'kingside' or 'queenside'.
    Otherwise returns (False, "").
    """
    f_file, f_rank, t_file, t_rank = move_str[0], move_str[1], move_str[2], move_str[3]
    if f_rank != t_rank:
        return False, ""
    col_diff = abs(ord(f_file) - ord(t_file))
    if col_diff != 2:
        return False, ""
    placement = current_fen.split()[0]
    rows = placement.split("/")
    try:
        rank_idx = 8 - int(f_rank)
    except ValueError:
        logger.debug(f"Invalid rank in move: {move_str}")
        return False, ""
    row_str = rows[rank_idx]
    
    expanded = []
    for ch in row_str:
        if ch.isdigit():
            expanded += [""] * int(ch)
        else:
            expanded.append(ch)
            
    file_idx = ord(f_file) - ord("a")
    if file_idx < 0 or file_idx > 7:
        return False, ""
        
    piece_at_source = expanded[file_idx]
    if color == "w" and piece_at_source != "K":
        return False, ""
    if color == "b" and piece_at_source != "k":
        return False, ""
        
    side_choice = "kingside" if (ord(t_file) > ord(f_file)) else "queenside"
    return True, side_choice


def update_fen_castling_rights(color_indicator, kingside_var, queenside_var, fen):
    """
    Update FEN castling rights based on color indicator and castling variables.
    """
    logger.debug(f"Original FEN: {fen}")
    
    fen_fields = _validate_and_parse_fen(fen)
    if not fen_fields:
        return fen
    
    new_castling = _build_castling_rights(color_indicator, kingside_var, queenside_var, fen)
    
    return _reconstruct_fen_with_castling(fen_fields, new_castling)


def _validate_and_parse_fen(fen):
    fields = fen.split()
    if len(fields) < 6:
        logger.error(f"Malformed FEN: {fen}")
        return None
    return fields


def _build_castling_rights(color_indicator, kingside_var, queenside_var, fen):
    white_castling = _get_color_castling_rights("w", color_indicator, kingside_var, queenside_var, fen)
    black_castling = _get_color_castling_rights("b", color_indicator, kingside_var, queenside_var, fen)
    
    combined_castling = white_castling + black_castling
    return combined_castling or "-"


def _get_color_castling_rights(target_color, player_color, kingside_var, queenside_var, fen):
    castling_symbols = _get_castling_symbols(target_color)
    castling_rights = ""
    
    if _should_add_castling_right(target_color, "kingside", player_color, kingside_var, fen):
        castling_rights += castling_symbols["kingside"]
    
    if _should_add_castling_right(target_color, "queenside", player_color, queenside_var, fen):
        castling_rights += castling_symbols["queenside"]
    
    return castling_rights


def _get_castling_symbols(color):
    if color == "w":
        return {"kingside": "K", "queenside": "Q"}
    else:
        return {"kingside": "k", "queenside": "q"}


def _should_add_castling_right(target_color, side, player_color, side_var, fen):
    if not is_castling_possible(fen, target_color, side):
        return False
    
    if target_color == player_color:
        return _get_var_value(side_var)
    
    return True


def _get_var_value(var):
    if callable(var):
        try:
            result = var()
            if callable(result) or hasattr(result, 'get') or hasattr(result, 'isChecked') or hasattr(result, 'value'):
                return _get_var_value(result)
            return bool(result)
        except Exception as e:
            logger.warning(f"Error calling variable function: {e}")
            return False
            
    if hasattr(var, 'isChecked'):
        try:
            return bool(var.isChecked())
        except Exception as e:
            logger.warning(f"Error calling .isChecked() on variable: {e}")
            return False
            
    if hasattr(var, 'get'):
        try:
            return bool(var.get())
        except Exception as e:
            logger.warning(f"Error calling .get() on variable: {e}")
            return False
            
    if hasattr(var, 'value'):
        try:
            return bool(var.value)
        except Exception as e:
            logger.warning(f"Error accessing .value on variable: {e}")
            return False
            
    return bool(var)


def _reconstruct_fen_with_castling(fen_fields, new_castling):
    logger.debug(f"Updated castling field: {new_castling}")
    fen_fields[2] = new_castling
    updated_fen = " ".join(fen_fields)
    logger.info(f"Updated FEN: {updated_fen}")
    return updated_fen
