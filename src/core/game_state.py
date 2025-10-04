import logging

logger = logging.getLogger(__name__)

class GameState:
    def __init__(self):
        self.color_indicator = None
        self.last_fen = ""
        self.last_fen_by_color = {'w': None, 'b': None}
        self.board_positions = {}
        self.move_mode = "drag"

        self.chessboard_x = None
        self.chessboard_y = None
        self.square_size = None

    def update_last_fen_for_color(self, fen: str):
        parts = fen.split()
        placement, active_color = parts[0], parts[1]
        self.last_fen_by_color[active_color] = placement
        logger.debug(f"Updated last FEN for {active_color}: {placement}")

    def set_color(self, color):
        logger.info(f"Color selected: {'White' if color == 'w' else 'Black'}")
        self.color_indicator = color

    def set_move_mode(self, mode):
        logger.info(f"Move method set to: {mode}")
        self.move_mode = mode

    def store_board_positions(self, x: int, y: int, size: int):
        logger.debug(f"Storing board positions: x={x}, y={y}, size={size}")
        self.chessboard_x = x
        self.chessboard_y = y
        self.square_size = size

        for row in range(8):
            for col in range(8):
                square_index = row * 8 + col
                square_x = x + col * size + size / 2
                square_y = y + row * size + size / 2
                self.board_positions[square_index] = (int(square_x), int(square_y))
