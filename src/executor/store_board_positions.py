def store_board_positions(board_positions, x, y, size):
    chessboard_x = x
    chessboard_y = y
    square_size = size
    board_positions.clear()
    for row in range(8):
        for col in range(8):
            pos_x = x + col * size + (size // 2)
            pos_y = y + row * size + (size // 2)
            board_positions[(col, row)] = (pos_x, pos_y)
