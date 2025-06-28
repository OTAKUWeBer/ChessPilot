import logging

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def did_my_piece_move(color_indicator, before_fen: str, after_fen: str, move: str) -> bool:
    """
    Return True iff the only change between before_fen and after_fen
    is that *your* piece moved from move[0:2] → move[2:4].
    """
    logger.debug(f"Checking move: {move} for color: {color_indicator}")
    
    def expand_row(row):
        out = []
        for ch in row:
            if ch.isdigit():
                out += [' '] * int(ch)
            else:
                out.append(ch)
        return out

    def fen_to_list(fen):
        rows = fen.split()[0].split('/')
        flat = []
        for r in rows:
            flat += expand_row(r)
        return flat  # len=64

    before_list = fen_to_list(before_fen)
    after_list = fen_to_list(after_fen)

    def algebraic_to_index(sq):
        file = ord(sq[0]) - ord('a')         # 0..7
        rank = 8 - int(sq[1])               # '1'→7 down to '8'→0
        return rank * 8 + file

    start_i = algebraic_to_index(move[0:2])
    end_i = algebraic_to_index(move[2:4])
    my_pieces = 'PNBRQK' if color_indicator == 'w' else 'pnbrqk'

    piece_char = before_list[start_i]
    logger.debug(f"Piece at start square: '{piece_char}'")

    moved_from = (piece_char in my_pieces) and (after_list[start_i] == ' ')
    after_char = after_list[end_i]
    moved_to = (after_char == piece_char)
    logger.debug(f"After piece at end square: '{after_char}'")

    unchanged_elsewhere = all(
        (b == a) or idx in (start_i, end_i)
        for idx, (b, a) in enumerate(zip(before_list, after_list))
    )
    logger.debug(
        f"moved_from={moved_from}, moved_to={moved_to}, unchanged_elsewhere={unchanged_elsewhere}"
    )

    if moved_from and moved_to and unchanged_elsewhere:
        logger.info(f"Valid move detected: {move}")
        return True
    else:
        logger.warning("Move check failed")
        return False
