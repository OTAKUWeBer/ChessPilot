from tkinter import messagebox
import logging

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def chess_notation_to_index(color_indicator, root, auto_mode_var, move):
    logger.debug(f"Translating move: {move} for color: {color_indicator}")
    if color_indicator == "w":
        col_map = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7}
        row_map = {'1': 7, '2': 6, '3': 5, '4': 4, '5': 3, '6': 2, '7': 1, '8': 0}
    else:
        col_map = {'a': 7, 'b': 6, 'c': 5, 'd': 4, 'e': 3, 'f': 2, 'g': 1, 'h': 0}
        row_map = {'1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6, '8': 7}

    try:
        start_col = col_map[move[0]]
        start_row = row_map[move[1]]
        end_col = col_map[move[2]]
        end_row = row_map[move[3]]
        logger.info(f"Parsed move: {move} -> ({start_col}, {start_row}) to ({end_col}, {end_row})")
        return (start_col, start_row), (end_col, end_row)

    except (KeyError, IndexError) as e:
        logger.error(f"Invalid move notation: {move}, Error: {e}")
        root.after(
            0,
            lambda: messagebox.showerror(
                "Error", f"Invalid move notation: {move}"
            )
        )
        auto_mode_var.set(False)
        return None, None
