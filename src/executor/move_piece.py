from .move_piece_methods import drag_piece, click_piece
from executor.chess_notation_to_index import chess_notation_to_index
from executor.move_cursor_to_button import move_cursor_to_button
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer

def move_piece(color_indicator, move, board_positions, auto_mode_var, root, btn_play, mode,
               humanize=True, offset_range=(-16, 16)):
    print(f"Moving piece: {move} in mode: {mode}")
    start_idx, end_idx = chess_notation_to_index(color_indicator, root, auto_mode_var, move)
    if not start_idx or not end_idx:
        return

    try:
        start_pos = board_positions[start_idx]
        end_pos = board_positions[end_idx]
    except KeyError:
        QTimer.singleShot(0, lambda: QMessageBox.critical(root, "Error", "Could not map move to board positions"))
        if callable(auto_mode_var):
            root.auto_mode_var = False
            root.auto_mode_check.setChecked(False)
        return

    if mode == "drag":
        drag_piece(start_pos, end_pos, humanize, offset_range, root, auto_mode_var)
    elif mode == "click":
        click_piece(start_pos, end_pos, humanize, offset_range, root, auto_mode_var)

    auto_val = auto_mode_var() if callable(auto_mode_var) else auto_mode_var
    if not auto_val:
        move_cursor_to_button(root, auto_mode_var, btn_play)
