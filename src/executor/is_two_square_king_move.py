import logging
from typing import Tuple

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def is_two_square_king_move(move_str: str, current_fen: str, color: str) -> Tuple[(bool, str)]:
    """
    Return (True, side) if `move_str` is a legal castling-style king move
    from current_fen for this color.  side is either 'kingside' or 'queenside'.
    Otherwise returns (False, "").
    """
    # move_str is always four characters, e.g. 'e8c8'.
    f_file, f_rank, t_file, t_rank = move_str[0], move_str[1], move_str[2], move_str[3]
    if f_rank != t_rank:
        return False, ""
    col_diff = abs(ord(f_file) - ord(t_file))
    if col_diff != 2:
        return False, ""
    placement = current_fen.split()[0]
    rows = placement.split("/")
    try:
        rank_idx = 8 - int(f_rank)  # rank '8' → index 0, rank '1' → index 7.
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
