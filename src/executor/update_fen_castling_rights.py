import logging
from executor.is_castling_possible import is_castling_possible

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def update_fen_castling_rights(color_indicator, kingside_var, queenside_var, fen):
    """
    Update FEN castling rights based on color indicator and castling variables.
    Complexity reduced by extracting specialized functions.
    """
    logger.debug(f"Original FEN: {fen}")
    
    fen_fields = _validate_and_parse_fen(fen)
    if not fen_fields:
        return fen
    
    new_castling = _build_castling_rights(color_indicator, kingside_var, queenside_var, fen)
    
    return _reconstruct_fen_with_castling(fen_fields, new_castling)


def _validate_and_parse_fen(fen):
    """
    Validate FEN format and return parsed fields.
    """
    fields = fen.split()
    if len(fields) < 6:
        logger.error(f"Malformed FEN: {fen}")
        return None
    return fields


def _build_castling_rights(color_indicator, kingside_var, queenside_var, fen):
    """
    Build the complete castling rights string for both colors.
    """
    white_castling = _get_color_castling_rights("w", color_indicator, kingside_var, queenside_var, fen)
    black_castling = _get_color_castling_rights("b", color_indicator, kingside_var, queenside_var, fen)
    
    combined_castling = white_castling + black_castling
    return combined_castling or "-"


def _get_color_castling_rights(target_color, player_color, kingside_var, queenside_var, fen):
    """
    Get castling rights string for a specific color (white or black).
    """
    castling_symbols = _get_castling_symbols(target_color)
    castling_rights = ""
    
    # Check kingside castling
    if _should_add_castling_right(target_color, "kingside", player_color, kingside_var, fen):
        castling_rights += castling_symbols["kingside"]
    
    # Check queenside castling
    if _should_add_castling_right(target_color, "queenside", player_color, queenside_var, fen):
        castling_rights += castling_symbols["queenside"]
    
    return castling_rights


def _get_castling_symbols(color):
    """
    Get the appropriate castling symbols for the given color.
    """
    if color == "w":
        return {"kingside": "K", "queenside": "Q"}
    else:  # color == "b"
        return {"kingside": "k", "queenside": "q"}


def _should_add_castling_right(target_color, side, player_color, side_var, fen):
    """
    Determine if castling right should be added for the given color and side.
    """
    if not is_castling_possible(fen, target_color, side):
        return False
    
    # If it's the player's color, check if the corresponding variable is set
    if target_color == player_color:
        return _get_var_value(side_var)
    
    # If it's not the player's color, always include if possible
    return True


def _get_var_value(var):
    """
    Safely extract boolean value from various variable types.
    
    Handles:
    - Callables (lambdas/functions) - call them
    - Objects with .get() method (Tkinter variables, Qt checkboxes)
    - Objects with .isChecked() method (Qt checkboxes)
    - Objects with .value attribute
    - Direct boolean values
    """
    # If it's callable, call it to get the value
    if callable(var):
        try:
            result = var()
            # The result might be another object, so recursively check
            if callable(result) or hasattr(result, 'get') or hasattr(result, 'isChecked') or hasattr(result, 'value'):
                return _get_var_value(result)
            return bool(result)
        except Exception as e:
            logger.warning(f"Error calling variable function: {e}")
            return False
    
    # Try .isChecked() method (for PyQt6 checkboxes)
    if hasattr(var, 'isChecked'):
        try:
            return bool(var.isChecked())
        except Exception as e:
            logger.warning(f"Error calling .isChecked() on variable: {e}")
            return False
    
    # Try .get() method (for Tkinter variables, etc.)
    if hasattr(var, 'get'):
        try:
            return bool(var.get())
        except Exception as e:
            logger.warning(f"Error calling .get() on variable: {e}")
            return False
    
    # Try .value attribute
    if hasattr(var, 'value'):
        try:
            return bool(var.value)
        except Exception as e:
            logger.warning(f"Error accessing .value on variable: {e}")
            return False
    
    # Direct boolean value
    return bool(var)


def _reconstruct_fen_with_castling(fen_fields, new_castling):
    """
    Reconstruct the FEN string with updated castling rights.
    """
    logger.debug(f"Updated castling field: {new_castling}")
    
    fen_fields[2] = new_castling
    updated_fen = " ".join(fen_fields)
    
    logger.info(f"Updated FEN: {updated_fen}")
    return updated_fen