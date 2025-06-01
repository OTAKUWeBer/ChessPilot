import logging
from engine.is_castling_possible import is_castling_possible

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def update_fen_castling_rights(color_indicator, kingside_var, queenside_var, fen):
    fields = fen.split()
    if len(fields) < 6:
        logger.error(f"Malformed FEN: {fen}")
        return fen  # return as-is if FEN is malformed

    logger.debug(f"Original FEN: {fen}")

    white_castling = ""
    black_castling = ""

    # White castling rights
    if is_castling_possible(fen, "w", "kingside"):
        if color_indicator == "w" and kingside_var.get():
            white_castling += "K"
        elif color_indicator != "w":
            white_castling += "K"
    if is_castling_possible(fen, "w", "queenside"):
        if color_indicator == "w" and queenside_var.get():
            white_castling += "Q"
        elif color_indicator != "w":
            white_castling += "Q"

    # Black castling rights
    if is_castling_possible(fen, "b", "kingside"):
        if color_indicator == "b" and kingside_var.get():
            black_castling += "k"
        elif color_indicator != "b":
            black_castling += "k"
    if is_castling_possible(fen, "b", "queenside"):
        if color_indicator == "b" and queenside_var.get():
            black_castling += "q"
        elif color_indicator != "b":
            black_castling += "q"

    new_castling = white_castling + black_castling or "-"
    logger.debug(f"Updated castling field: {new_castling}")

    fields[2] = new_castling
    updated_fen = " ".join(fields)
    logger.info(f"Updated FEN: {updated_fen}")
    return updated_fen
