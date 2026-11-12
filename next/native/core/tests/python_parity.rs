// Expected values captured from the current Python implementation.
use chesspilot_core::{board::*, fen::*, notation::*, Color::*};
#[test]
fn python_coordinates_w() {
    let expected = [
        (0, 7),
        (1, 7),
        (2, 7),
        (3, 7),
        (4, 7),
        (5, 7),
        (6, 7),
        (7, 7),
        (0, 6),
        (1, 6),
        (2, 6),
        (3, 6),
        (4, 6),
        (5, 6),
        (6, 6),
        (7, 6),
        (0, 5),
        (1, 5),
        (2, 5),
        (3, 5),
        (4, 5),
        (5, 5),
        (6, 5),
        (7, 5),
        (0, 4),
        (1, 4),
        (2, 4),
        (3, 4),
        (4, 4),
        (5, 4),
        (6, 4),
        (7, 4),
        (0, 3),
        (1, 3),
        (2, 3),
        (3, 3),
        (4, 3),
        (5, 3),
        (6, 3),
        (7, 3),
        (0, 2),
        (1, 2),
        (2, 2),
        (3, 2),
        (4, 2),
        (5, 2),
        (6, 2),
        (7, 2),
        (0, 1),
        (1, 1),
        (2, 1),
        (3, 1),
        (4, 1),
        (5, 1),
        (6, 1),
        (7, 1),
        (0, 0),
        (1, 0),
        (2, 0),
        (3, 0),
        (4, 0),
        (5, 0),
        (6, 0),
        (7, 0),
    ];
    for (i, &(column, row)) in expected.iter().enumerate() {
        let square = format!("{}{}", (b'a' + (i % 8) as u8) as char, i / 8 + 1);
        assert_eq!(
            chess_notation_to_index(White, &format!("{square}{square}")).unwrap(),
            ((column, row), (column, row))
        );
    }
}
#[test]
fn python_coordinates_b() {
    let expected = [
        (7, 0),
        (6, 0),
        (5, 0),
        (4, 0),
        (3, 0),
        (2, 0),
        (1, 0),
        (0, 0),
        (7, 1),
        (6, 1),
        (5, 1),
        (4, 1),
        (3, 1),
        (2, 1),
        (1, 1),
        (0, 1),
        (7, 2),
        (6, 2),
        (5, 2),
        (4, 2),
        (3, 2),
        (2, 2),
        (1, 2),
        (0, 2),
        (7, 3),
        (6, 3),
        (5, 3),
        (4, 3),
        (3, 3),
        (2, 3),
        (1, 3),
        (0, 3),
        (7, 4),
        (6, 4),
        (5, 4),
        (4, 4),
        (3, 4),
        (2, 4),
        (1, 4),
        (0, 4),
        (7, 5),
        (6, 5),
        (5, 5),
        (4, 5),
        (3, 5),
        (2, 5),
        (1, 5),
        (0, 5),
        (7, 6),
        (6, 6),
        (5, 6),
        (4, 6),
        (3, 6),
        (2, 6),
        (1, 6),
        (0, 6),
        (7, 7),
        (6, 7),
        (5, 7),
        (4, 7),
        (3, 7),
        (2, 7),
        (1, 7),
        (0, 7),
    ];
    for (i, &(column, row)) in expected.iter().enumerate() {
        let square = format!("{}{}", (b'a' + (i % 8) as u8) as char, i / 8 + 1);
        assert_eq!(
            chess_notation_to_index(Black, &format!("{square}{square}")).unwrap(),
            ((column, row), (column, row))
        );
    }
}
#[test]
fn python_castling_flags() {
    assert_eq!(
        update_fen_castling_rights(White, false, false, "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
            .unwrap(),
        "r3k2r/8/8/8/8/8/8/R3K2R w kq - 0 1"
    );
    assert_eq!(
        update_fen_castling_rights(White, false, true, "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
            .unwrap(),
        "r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1"
    );
    assert_eq!(
        update_fen_castling_rights(White, true, false, "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
            .unwrap(),
        "r3k2r/8/8/8/8/8/8/R3K2R w Kkq - 0 1"
    );
    assert_eq!(
        update_fen_castling_rights(White, true, true, "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1").unwrap(),
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    );
    assert_eq!(
        update_fen_castling_rights(Black, false, false, "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
            .unwrap(),
        "r3k2r/8/8/8/8/8/8/R3K2R w KQ - 0 1"
    );
    assert_eq!(
        update_fen_castling_rights(Black, false, true, "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
            .unwrap(),
        "r3k2r/8/8/8/8/8/8/R3K2R w KQq - 0 1"
    );
    assert_eq!(
        update_fen_castling_rights(Black, true, false, "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
            .unwrap(),
        "r3k2r/8/8/8/8/8/8/R3K2R w KQk - 0 1"
    );
    assert_eq!(
        update_fen_castling_rights(Black, true, true, "r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1").unwrap(),
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    );
}
#[test]
fn python_fractional_and_negative_monitor_geometry() {
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(0, 0)
            .unwrap(),
        Point { x: 789.0, y: 254.0 }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(1, 0)
            .unwrap(),
        Point {
            x: 919.875,
            y: 254.0
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(2, 0)
            .unwrap(),
        Point {
            x: 1050.75,
            y: 254.0
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(3, 0)
            .unwrap(),
        Point {
            x: 1181.625,
            y: 254.0
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(4, 0)
            .unwrap(),
        Point {
            x: 1312.5,
            y: 254.0
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(5, 0)
            .unwrap(),
        Point {
            x: 1443.375,
            y: 254.0
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(6, 0)
            .unwrap(),
        Point {
            x: 1574.25,
            y: 254.0
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(7, 0)
            .unwrap(),
        Point {
            x: 1705.125,
            y: 254.0
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(0, 1)
            .unwrap(),
        Point {
            x: 789.0,
            y: 384.875
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(1, 1)
            .unwrap(),
        Point {
            x: 919.875,
            y: 384.875
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(2, 1)
            .unwrap(),
        Point {
            x: 1050.75,
            y: 384.875
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(3, 1)
            .unwrap(),
        Point {
            x: 1181.625,
            y: 384.875
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(4, 1)
            .unwrap(),
        Point {
            x: 1312.5,
            y: 384.875
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(5, 1)
            .unwrap(),
        Point {
            x: 1443.375,
            y: 384.875
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(6, 1)
            .unwrap(),
        Point {
            x: 1574.25,
            y: 384.875
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(7, 1)
            .unwrap(),
        Point {
            x: 1705.125,
            y: 384.875
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(0, 2)
            .unwrap(),
        Point {
            x: 789.0,
            y: 515.75
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(1, 2)
            .unwrap(),
        Point {
            x: 919.875,
            y: 515.75
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(2, 2)
            .unwrap(),
        Point {
            x: 1050.75,
            y: 515.75
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(3, 2)
            .unwrap(),
        Point {
            x: 1181.625,
            y: 515.75
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(4, 2)
            .unwrap(),
        Point {
            x: 1312.5,
            y: 515.75
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(5, 2)
            .unwrap(),
        Point {
            x: 1443.375,
            y: 515.75
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(6, 2)
            .unwrap(),
        Point {
            x: 1574.25,
            y: 515.75
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(7, 2)
            .unwrap(),
        Point {
            x: 1705.125,
            y: 515.75
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(0, 3)
            .unwrap(),
        Point {
            x: 789.0,
            y: 646.625
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(1, 3)
            .unwrap(),
        Point {
            x: 919.875,
            y: 646.625
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(2, 3)
            .unwrap(),
        Point {
            x: 1050.75,
            y: 646.625
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(3, 3)
            .unwrap(),
        Point {
            x: 1181.625,
            y: 646.625
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(4, 3)
            .unwrap(),
        Point {
            x: 1312.5,
            y: 646.625
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(5, 3)
            .unwrap(),
        Point {
            x: 1443.375,
            y: 646.625
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(6, 3)
            .unwrap(),
        Point {
            x: 1574.25,
            y: 646.625
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(7, 3)
            .unwrap(),
        Point {
            x: 1705.125,
            y: 646.625
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(0, 4)
            .unwrap(),
        Point { x: 789.0, y: 777.5 }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(1, 4)
            .unwrap(),
        Point {
            x: 919.875,
            y: 777.5
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(2, 4)
            .unwrap(),
        Point {
            x: 1050.75,
            y: 777.5
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(3, 4)
            .unwrap(),
        Point {
            x: 1181.625,
            y: 777.5
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(4, 4)
            .unwrap(),
        Point {
            x: 1312.5,
            y: 777.5
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(5, 4)
            .unwrap(),
        Point {
            x: 1443.375,
            y: 777.5
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(6, 4)
            .unwrap(),
        Point {
            x: 1574.25,
            y: 777.5
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(7, 4)
            .unwrap(),
        Point {
            x: 1705.125,
            y: 777.5
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(0, 5)
            .unwrap(),
        Point {
            x: 789.0,
            y: 908.375
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(1, 5)
            .unwrap(),
        Point {
            x: 919.875,
            y: 908.375
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(2, 5)
            .unwrap(),
        Point {
            x: 1050.75,
            y: 908.375
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(3, 5)
            .unwrap(),
        Point {
            x: 1181.625,
            y: 908.375
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(4, 5)
            .unwrap(),
        Point {
            x: 1312.5,
            y: 908.375
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(5, 5)
            .unwrap(),
        Point {
            x: 1443.375,
            y: 908.375
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(6, 5)
            .unwrap(),
        Point {
            x: 1574.25,
            y: 908.375
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(7, 5)
            .unwrap(),
        Point {
            x: 1705.125,
            y: 908.375
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(0, 6)
            .unwrap(),
        Point {
            x: 789.0,
            y: 1039.25
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(1, 6)
            .unwrap(),
        Point {
            x: 919.875,
            y: 1039.25
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(2, 6)
            .unwrap(),
        Point {
            x: 1050.75,
            y: 1039.25
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(3, 6)
            .unwrap(),
        Point {
            x: 1181.625,
            y: 1039.25
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(4, 6)
            .unwrap(),
        Point {
            x: 1312.5,
            y: 1039.25
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(5, 6)
            .unwrap(),
        Point {
            x: 1443.375,
            y: 1039.25
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(6, 6)
            .unwrap(),
        Point {
            x: 1574.25,
            y: 1039.25
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(7, 6)
            .unwrap(),
        Point {
            x: 1705.125,
            y: 1039.25
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(0, 7)
            .unwrap(),
        Point {
            x: 789.0,
            y: 1170.125
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(1, 7)
            .unwrap(),
        Point {
            x: 919.875,
            y: 1170.125
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(2, 7)
            .unwrap(),
        Point {
            x: 1050.75,
            y: 1170.125
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(3, 7)
            .unwrap(),
        Point {
            x: 1181.625,
            y: 1170.125
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(4, 7)
            .unwrap(),
        Point {
            x: 1312.5,
            y: 1170.125
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(5, 7)
            .unwrap(),
        Point {
            x: 1443.375,
            y: 1170.125
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(6, 7)
            .unwrap(),
        Point {
            x: 1574.25,
            y: 1170.125
        }
    );
    assert_eq!(
        BoardGeometry::new(724.0, 189.0, 130.875)
            .unwrap()
            .center(7, 7)
            .unwrap(),
        Point {
            x: 1705.125,
            y: 1170.125
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(0, 0)
            .unwrap(),
        Point {
            x: -1476.0,
            y: 74.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(1, 0)
            .unwrap(),
        Point {
            x: -1426.5,
            y: 74.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(2, 0)
            .unwrap(),
        Point {
            x: -1377.0,
            y: 74.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(3, 0)
            .unwrap(),
        Point {
            x: -1327.5,
            y: 74.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(4, 0)
            .unwrap(),
        Point {
            x: -1278.0,
            y: 74.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(5, 0)
            .unwrap(),
        Point {
            x: -1228.5,
            y: 74.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(6, 0)
            .unwrap(),
        Point {
            x: -1179.0,
            y: 74.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(7, 0)
            .unwrap(),
        Point {
            x: -1129.5,
            y: 74.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(0, 1)
            .unwrap(),
        Point {
            x: -1476.0,
            y: 123.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(1, 1)
            .unwrap(),
        Point {
            x: -1426.5,
            y: 123.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(2, 1)
            .unwrap(),
        Point {
            x: -1377.0,
            y: 123.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(3, 1)
            .unwrap(),
        Point {
            x: -1327.5,
            y: 123.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(4, 1)
            .unwrap(),
        Point {
            x: -1278.0,
            y: 123.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(5, 1)
            .unwrap(),
        Point {
            x: -1228.5,
            y: 123.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(6, 1)
            .unwrap(),
        Point {
            x: -1179.0,
            y: 123.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(7, 1)
            .unwrap(),
        Point {
            x: -1129.5,
            y: 123.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(0, 2)
            .unwrap(),
        Point {
            x: -1476.0,
            y: 173.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(1, 2)
            .unwrap(),
        Point {
            x: -1426.5,
            y: 173.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(2, 2)
            .unwrap(),
        Point {
            x: -1377.0,
            y: 173.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(3, 2)
            .unwrap(),
        Point {
            x: -1327.5,
            y: 173.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(4, 2)
            .unwrap(),
        Point {
            x: -1278.0,
            y: 173.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(5, 2)
            .unwrap(),
        Point {
            x: -1228.5,
            y: 173.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(6, 2)
            .unwrap(),
        Point {
            x: -1179.0,
            y: 173.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(7, 2)
            .unwrap(),
        Point {
            x: -1129.5,
            y: 173.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(0, 3)
            .unwrap(),
        Point {
            x: -1476.0,
            y: 222.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(1, 3)
            .unwrap(),
        Point {
            x: -1426.5,
            y: 222.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(2, 3)
            .unwrap(),
        Point {
            x: -1377.0,
            y: 222.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(3, 3)
            .unwrap(),
        Point {
            x: -1327.5,
            y: 222.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(4, 3)
            .unwrap(),
        Point {
            x: -1278.0,
            y: 222.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(5, 3)
            .unwrap(),
        Point {
            x: -1228.5,
            y: 222.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(6, 3)
            .unwrap(),
        Point {
            x: -1179.0,
            y: 222.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(7, 3)
            .unwrap(),
        Point {
            x: -1129.5,
            y: 222.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(0, 4)
            .unwrap(),
        Point {
            x: -1476.0,
            y: 272.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(1, 4)
            .unwrap(),
        Point {
            x: -1426.5,
            y: 272.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(2, 4)
            .unwrap(),
        Point {
            x: -1377.0,
            y: 272.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(3, 4)
            .unwrap(),
        Point {
            x: -1327.5,
            y: 272.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(4, 4)
            .unwrap(),
        Point {
            x: -1278.0,
            y: 272.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(5, 4)
            .unwrap(),
        Point {
            x: -1228.5,
            y: 272.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(6, 4)
            .unwrap(),
        Point {
            x: -1179.0,
            y: 272.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(7, 4)
            .unwrap(),
        Point {
            x: -1129.5,
            y: 272.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(0, 5)
            .unwrap(),
        Point {
            x: -1476.0,
            y: 321.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(1, 5)
            .unwrap(),
        Point {
            x: -1426.5,
            y: 321.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(2, 5)
            .unwrap(),
        Point {
            x: -1377.0,
            y: 321.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(3, 5)
            .unwrap(),
        Point {
            x: -1327.5,
            y: 321.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(4, 5)
            .unwrap(),
        Point {
            x: -1278.0,
            y: 321.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(5, 5)
            .unwrap(),
        Point {
            x: -1228.5,
            y: 321.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(6, 5)
            .unwrap(),
        Point {
            x: -1179.0,
            y: 321.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(7, 5)
            .unwrap(),
        Point {
            x: -1129.5,
            y: 321.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(0, 6)
            .unwrap(),
        Point {
            x: -1476.0,
            y: 371.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(1, 6)
            .unwrap(),
        Point {
            x: -1426.5,
            y: 371.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(2, 6)
            .unwrap(),
        Point {
            x: -1377.0,
            y: 371.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(3, 6)
            .unwrap(),
        Point {
            x: -1327.5,
            y: 371.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(4, 6)
            .unwrap(),
        Point {
            x: -1278.0,
            y: 371.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(5, 6)
            .unwrap(),
        Point {
            x: -1228.5,
            y: 371.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(6, 6)
            .unwrap(),
        Point {
            x: -1179.0,
            y: 371.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(7, 6)
            .unwrap(),
        Point {
            x: -1129.5,
            y: 371.0
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(0, 7)
            .unwrap(),
        Point {
            x: -1476.0,
            y: 420.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(1, 7)
            .unwrap(),
        Point {
            x: -1426.5,
            y: 420.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(2, 7)
            .unwrap(),
        Point {
            x: -1377.0,
            y: 420.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(3, 7)
            .unwrap(),
        Point {
            x: -1327.5,
            y: 420.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(4, 7)
            .unwrap(),
        Point {
            x: -1278.0,
            y: 420.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(5, 7)
            .unwrap(),
        Point {
            x: -1228.5,
            y: 420.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(6, 7)
            .unwrap(),
        Point {
            x: -1179.0,
            y: 420.5
        }
    );
    assert_eq!(
        BoardGeometry::new(-1500.0, 50.0, 49.5)
            .unwrap()
            .center(7, 7)
            .unwrap(),
        Point {
            x: -1129.5,
            y: 420.5
        }
    );
}
