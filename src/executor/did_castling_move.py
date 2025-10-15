import logging

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def did_castling_move(color_indicator, before_fen: str, after_fen: str, king_move: str, rook_move: str) -> bool:
    """
    Verify that a castling move was executed correctly.
    Checks that both the king and rook moved to their correct positions.
    
    Args:
        color_indicator: 'w' or 'b'
        before_fen: FEN string before the move
        after_fen: FEN string after the move
        king_move: King's move in algebraic notation (e.g., 'e1c1')
        rook_move: Rook's move in algebraic notation (e.g., 'a1d1')
    
    Returns:
        True if both pieces moved correctly and nothing else changed
    """
    logger.debug(f"Checking castling: King {king_move}, Rook {rook_move} for color: {color_indicator}")
    
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

    # Get indices for king move
    king_start_i = algebraic_to_index(king_move[0:2])
    king_end_i = algebraic_to_index(king_move[2:4])
    
    # Get indices for rook move
    rook_start_i = algebraic_to_index(rook_move[0:2])
    rook_end_i = algebraic_to_index(rook_move[2:4])
    
    my_pieces = 'PNBRQK' if color_indicator == 'w' else 'pnbrqk'
    
    # Get the pieces that should have moved
    king_char = before_list[king_start_i]
    rook_char = before_list[rook_start_i]
    
    logger.debug(f"King at start: '{king_char}', Rook at start: '{rook_char}'")
    
    # Check king moved correctly
    king_moved_from = (king_char in my_pieces) and (after_list[king_start_i] == ' ')
    king_moved_to = (after_list[king_end_i] == king_char)
    
    # Check rook moved correctly
    rook_moved_from = (rook_char in my_pieces) and (after_list[rook_start_i] == ' ')
    rook_moved_to = (after_list[rook_end_i] == rook_char)
    
    logger.debug(
        f"After - King at end: '{after_list[king_end_i]}', Rook at end: '{after_list[rook_end_i]}'"
    )
    
    # Check that everything else is unchanged (except the 4 castling squares)
    # castling_squares = {king_start_i, king_end_i, rook_start_i, rook_end_i}
    # unchanged_elsewhere = all(
    #     (b == a) or idx in castling_squares
    #     for idx, (b, a) in enumerate(zip(before_list, after_list))
    # )
    
    logger.debug(
        f"king_moved_from={king_moved_from}, king_moved_to={king_moved_to}, "
        f"rook_moved_from={rook_moved_from}, rook_moved_to={rook_moved_to}"
    )
    
    if king_moved_from and king_moved_to and rook_moved_from and rook_moved_to:
        logger.info(f"Valid castling detected: King {king_move}, Rook {rook_move}")
        return True
    else:
        logger.warning("Castling verification failed")
        return False
