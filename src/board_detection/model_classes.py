"""
Class mappings and detection constants for the chess detection ONNX model.
"""

CHESSBOARD_CLASS_ID = 12.0

# Mapping from neural net class_id to FEN piece character
CLASS_TO_FEN = {
    0: 'p',
    1: 'r',
    2: 'n',
    3: 'b',
    4: 'q',
    5: 'k',
    6: 'P',
    7: 'R',
    8: 'N',
    9: 'B',
    10: 'Q',
    11: 'K',
}

# Promotion piece candidate class IDs (Queen, Rook, Bishop, Knight)
PROMOTION_PIECE_IDS = [10, 7, 9, 8]
PROMOTION_PIECE_IDS_BLACK = [4, 1, 3, 2]
