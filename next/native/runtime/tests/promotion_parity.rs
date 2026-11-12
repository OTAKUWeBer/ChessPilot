use chesspilot_core::{
    board::BoardGeometry,
    detection::Detection,
    promotion::{detect_promotion_pieces, find_promotion_dialog_pieces, PromotionPiece},
    Color,
};
use serde_json::{json, Value};
fn as_json(pieces: Vec<PromotionPiece>) -> Value {
    json!(pieces.into_iter().map(|p|json!({"class_id":p.class_id,"confidence":p.confidence,"position":[p.position.x,p.position.y],"file":p.file,"rank":p.rank,"is_promotion_rank":p.is_promotion_rank,"piece_char":p.piece_char})).collect::<Vec<_>>())
}
#[test]
fn promotion_candidates_match_frozen_python_in_both_colors_and_fractional_geometry() {
    let fixture: Value = serde_json::from_str(include_str!("fixtures/promotion.json")).unwrap();
    for case in fixture["cases"].as_array().unwrap() {
        let b = &case["board"];
        let board = BoardGeometry::new(
            b[0].as_f64().unwrap(),
            b[1].as_f64().unwrap(),
            b[2].as_f64().unwrap() / 8.,
        )
        .unwrap();
        let color = Color::parse(case["color"].as_str().unwrap()).unwrap();
        let boxes = case["boxes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|b| Detection {
                x: b[0].as_f64().unwrap(),
                y: b[1].as_f64().unwrap(),
                width: b[2].as_f64().unwrap(),
                height: b[3].as_f64().unwrap(),
                confidence: b[4].as_f64().unwrap(),
                class_id: b[5].as_u64().unwrap() as u8,
            })
            .collect::<Vec<_>>();
        assert_eq!(
            as_json(detect_promotion_pieces(&boxes, board, color).unwrap()),
            case["detected"]
        );
        assert_eq!(
            as_json(find_promotion_dialog_pieces(&boxes, board, color).unwrap()),
            case["first_four"]
        );
    }
}
