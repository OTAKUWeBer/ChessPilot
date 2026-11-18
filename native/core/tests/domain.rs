use chesspilot_core::{
    board::*, config::*, fen::*, notation::*, state::*, validation::*, Color::*,
};
const START: &str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

#[test]
fn coordinates_geometry_and_invalid_inputs() {
    assert_eq!(
        chess_notation_to_index(White, "e2e4").unwrap(),
        ((4, 6), (4, 4))
    );
    assert_eq!(
        chess_notation_to_index(Black, "e7e5").unwrap(),
        ((3, 6), (3, 4))
    );
    assert!(Move::parse("(none)").is_err());
    assert!(algebraic_to_index("i9").is_err());
    let geometry = BoardGeometry::new(-800.0, 30.0, 49.5).unwrap();
    assert_eq!(geometry.center(0, 0).unwrap(), Point { x: -776.0, y: 54.0 });
    assert_eq!(geometry.positions()[7][7], geometry.center(7, 7).unwrap());
    assert!(BoardGeometry::new(0.0, 0.0, 0.0).is_err());
}

#[test]
fn fen_castling_and_state() {
    assert_eq!(fen_to_list(START).unwrap()[0], 'r');
    assert_eq!(flip_board(&flip_board(START).unwrap()).unwrap(), START);
    assert_eq!(
        update_fen_castling_rights(White, false, true, START)
            .unwrap()
            .split_whitespace()
            .nth(2),
        Some("Qkq")
    );
    let castle = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1";
    assert_eq!(
        is_two_square_king_move("e1g1", castle, White).unwrap(),
        Some(CastleSide::Kingside)
    );
    let mut state = GameState::default();
    state.set_color(Black);
    state.set_move_mode(MoveMode::Click);
    state.update_last_fen_for_color(START).unwrap();
    assert_eq!(
        state.last_fen_by_color[0].as_deref(),
        START.split_whitespace().next()
    );
    assert!(state.last_fen_by_color[1].is_none());
    assert!(fen_to_list("8/8").is_err());
}

#[test]
fn move_verification_special_moves_and_failure() {
    let after = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1";
    assert!(did_my_piece_move(White, START, after, "e2e4").unwrap());
    assert!(!did_my_piece_move(White, START, START, "e2e4").unwrap());
    assert!(did_my_piece_move(
        White,
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3",
        "rnbqkbnr/ppp1pppp/3P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3",
        "e5d6"
    )
    .unwrap());
    for (suffix, piece) in [('q', 'Q'), ('r', 'R'), ('b', 'B'), ('n', 'N')] {
        assert!(did_my_piece_move(
            White,
            "8/4P3/8/8/8/8/8/4K2k w - - 0 1",
            &format!("4{piece}3/8/8/8/8/8/8/4K2k b - - 0 1"),
            &format!("e7e8{suffix}")
        )
        .unwrap());
    }
    assert!(did_castling_move(
        White,
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1",
        "e1g1",
        "h1f1"
    )
    .unwrap());
}
