import logging
from .get_positions import get_positions

# Setup Logger
# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_fen_from_position(color, boxes):
    # Find the chessboard (class_id 12.0)
    chessboard_boxes = [box for box in boxes if box[5] == 12.0]
    if not chessboard_boxes:
        logger.warning("Error: Bad Screenshot")
        return None
    chessboard_box = chessboard_boxes[0]
    chessboard_x = chessboard_box[0]
    chessboard_y = chessboard_box[1]
    square_size = chessboard_box[2] / 8.0  # Calculate square size based on chessboard width

    # Mapping from class_id to FEN characters
    class_to_fen = {
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

    # Filter out the chessboard and process other detections
    filtered_boxes = [box for box in boxes if box[5] != 12.0]

    # Initialize an 8x8 grid to represent the board
    grid = [[None for _ in range(8)] for _ in range(8)]

    for box in filtered_boxes:
        x, y, w, h, confidence, class_id = box
        # Calculate center coordinates of the piece
        center_x = x + w / 2
        center_y = y + h / 2
        # Convert to chessboard-relative coordinates
        rel_x = center_x - chessboard_x
        rel_y = center_y - chessboard_y
        # Determine file and rank indices
        file_index = int(rel_x // square_size)
        row_index = int(rel_y // square_size)
        # Check if indices are within bounds
        if 0 <= file_index < 8 and 0 <= row_index < 8:
            fen_char = class_to_fen.get(int(class_id), '?')  # Use '?' if class_id is unknown
            # Place the piece in the grid (row_index corresponds to chess rank)
            grid[row_index][file_index] = fen_char

    # Convert the grid to FEN notation
    fen_rows = []
    for row in grid:
        fen_part = []
        empty = 0
        for cell in row:
            if cell is None:
                empty += 1
            else:
                if empty > 0:
                    fen_part.append(str(empty))
                    empty = 0
                fen_part.append(cell)
        if empty > 0:
            fen_part.append(str(empty))
        fen_rows.append(''.join(fen_part))

    # FEN starts with rank 8, which is the first row in our grid
    fen_piece_placement = '/'.join(fen_rows)
    # Complete FEN string with default values for other fields
    fen = f"{fen_piece_placement} {color} - - 0 1"

    # Flip the board if color is black
    if color == 'b':
        fen = flip_board(fen)

    return (chessboard_x, chessboard_y, square_size, fen)

def flip_board(fen):
    """Flip the chessboard FEN notation for the opposite perspective."""
    rows = fen.split()[0].split('/')
    flipped_rows = [''.join(reversed(row)) for row in reversed(rows)]
    return "/".join(flipped_rows) + " " + ' '.join(fen.split()[1:])

if __name__ == "__main__":
    # Ask for the color (w or b)
    image_path = "chess-screenshot.png"
    boxes = get_positions(image_path)
    color = input("Enter the color you are playing as (w or b): ").strip().lower()
    
    # Ensure valid input
    while color not in ['w', 'b']:
        print("Invalid input. Please enter 'w' for white or 'b' for black.")
        color = input("Enter the color you are playing as (w or b): ").strip().lower()

    # Get FEN for the board and print it
    try:
        fen = get_fen_from_position(color, boxes)
        print(fen)
    except ValueError as e:
        print(f"Error: {e}")