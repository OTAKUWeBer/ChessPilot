def expend_fen_row(row):
    expanded = ""
    for char in row:
        if char.isdigit():
            expanded += " " * int(char)
        else:
            expanded += char
    return expanded
