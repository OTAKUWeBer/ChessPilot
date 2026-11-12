use chesspilot_core::{
    detection::{get_fen_from_position, Detection},
    Color,
};
use chesspilot_runtime::vision::{
    decode_boxes, preprocess_image, BoardReader, Letterbox, OnnxPredictor, Predictor, RgbFrame,
};
use serde_json::Value;
use std::{collections::VecDeque, path::PathBuf, sync::atomic::AtomicBool};

fn manifest() -> Value {
    serde_json::from_str(include_str!("fixtures/vision/python.json")).unwrap()
}
fn fnv64(bytes: impl IntoIterator<Item = u8>) -> String {
    bytes
        .into_iter()
        .fold(14695981039346656037u64, |hash, byte| {
            (hash ^ byte as u64).wrapping_mul(1099511628211)
        })
        .to_string()
}

#[test]
fn preprocessing_matches_python_pillow_tensor_bytes() {
    for case in manifest()["patterns"].as_array().unwrap() {
        let w = case["width"].as_u64().unwrap() as usize;
        let h = case["height"].as_u64().unwrap() as usize;
        let frame = RgbFrame::new(
            w,
            h,
            (0..w * h * 3)
                .map(|i| ((i * 37 + 11) % 256) as u8)
                .collect(),
        )
        .unwrap();
        let (tensor, transform) = preprocess_image(&frame).unwrap();
        assert_eq!(transform.x_offset, case["x"].as_u64().unwrap() as usize);
        assert_eq!(transform.y_offset, case["y"].as_u64().unwrap() as usize);
        assert!((transform.scale - case["scale"].as_f64().unwrap()).abs() < 1e-12);
        assert_eq!(
            fnv64(tensor.into_iter().flat_map(f32::to_le_bytes)),
            case["hash"].as_str().unwrap(),
            "{w}x{h}"
        );
    }
}

#[test]
fn frame_boundaries_and_model_output_are_validated() {
    assert!(RgbFrame::new(0, 1, vec![]).is_err());
    assert!(RgbFrame::new(1, 1, vec![0; 2]).is_err());
    let frame = RgbFrame::new(2, 1, vec![1, 2, 3, 4, 5, 6]).unwrap();
    assert_eq!(frame.crop([1, 0, 2, 1]).unwrap().pixels(), [4, 5, 6]);
    assert!(frame.crop([1, 0, 3, 1]).is_err());
    assert!(frame.resize(0, 5).is_err());
    assert!(RgbFrame::new(1, 10000, vec![0; 30000])
        .unwrap()
        .resize(10000, 1)
        .is_err());
    let transform = Letterbox {
        x_offset: 2,
        y_offset: 3,
        scale: 0.5,
    };
    assert!(decode_boxes(&[], &[1, 300, 6], transform).is_err());
    let mut rows = vec![0.; 1800];
    rows[..6].copy_from_slice(&[12., 23., 22., 43., 0.9, 11.]);
    let decoded = decode_boxes(&rows, &[1, 300, 6], transform).unwrap();
    assert_eq!(
        (
            decoded[0].x,
            decoded[0].y,
            decoded[0].width,
            decoded[0].height
        ),
        (20., 40., 20., 40.)
    );
    rows[5] = 99.;
    assert!(decode_boxes(&rows, &[1, 300, 6], transform).is_err());
}

struct Script {
    outputs: VecDeque<Vec<Detection>>,
    sizes: Vec<(usize, usize)>,
}
impl Predictor for Script {
    fn predict(&mut self, frame: &RgbFrame) -> Result<Vec<Detection>, String> {
        self.sizes.push((frame.width(), frame.height()));
        self.outputs
            .pop_front()
            .ok_or("Unexpected inference".into())
    }
}
fn detection(x: f64, y: f64, w: f64, h: f64, class_id: u8) -> Detection {
    Detection {
        x,
        y,
        width: w,
        height: h,
        class_id,
        confidence: 0.95,
    }
}
fn board(x: f64, y: f64) -> Vec<Detection> {
    vec![
        detection(x, y, 800., 800., 12),
        detection(x + 410., y + 10., 80., 80., 5),
        detection(x + 410., y + 710., 80., 80., 11),
    ]
}
fn reader(outputs: Vec<Vec<Detection>>) -> BoardReader<Script> {
    BoardReader::new(Script {
        outputs: outputs.into(),
        sizes: vec![],
    })
}

#[test]
fn normal_raw_refined_and_tiled_search_preserve_screen_coordinates() {
    let image = RgbFrame::new(2400, 1600, vec![0; 2400 * 1600 * 3]).unwrap();
    let cancelled = AtomicBool::new(false);
    let mut normal = reader(vec![board(0., 0.)]);
    assert_eq!(
        normal
            .get_positions(&image, true, &cancelled)
            .unwrap()
            .unwrap()
            .len(),
        3
    );
    assert_eq!(normal.inference_count, 1);
    let mut raw = reader(vec![vec![detection(0., 0., 800., 800., 12)]]);
    assert_eq!(
        raw.get_positions(&image, false, &cancelled)
            .unwrap()
            .unwrap()
            .len(),
        1
    );
    for tiled in [false, true] {
        let outputs = if tiled {
            vec![
                vec![],
                vec![],
                vec![detection(200., 100., 800., 800., 12)],
                board(40., 40.),
            ]
        } else {
            vec![vec![detection(800., 100., 800., 800., 12)], board(40., 40.)]
        };
        let mut reader = reader(outputs);
        let boxes = reader
            .get_positions(&image, true, &cancelled)
            .unwrap()
            .unwrap();
        assert_eq!((boxes[0].x, boxes[0].y), (800., 100.));
        assert_eq!((boxes[1].x, boxes[1].y), (1210., 110.));
        assert_eq!(reader.predictor.sizes.last(), Some(&(880, 880)));
    }
    let mut missing = reader(vec![vec![]; 10]);
    assert!(missing
        .get_positions(&image, true, &cancelled)
        .unwrap()
        .is_none());
    assert_eq!(missing.inference_count, 10);
    assert!(missing
        .get_positions(&image, true, &AtomicBool::new(true))
        .is_err());
    let candidates = vec![detection(0., 0., 16., 16., 12); 300];
    let mut crowded = reader(vec![candidates; 64]);
    assert!(crowded
        .get_positions(&image, true, &cancelled)
        .unwrap_err()
        .contains("inference limit"));
    assert_eq!(crowded.inference_count, 64);
}

#[test]
#[ignore = "Requires CHESSPILOT_MODEL and CHESSPILOT_ORT native runtime"]
fn actual_onnx_inference_and_zoom_search_match_python() {
    let model = PathBuf::from(std::env::var_os("CHESSPILOT_MODEL").unwrap());
    let runtime = PathBuf::from(std::env::var_os("CHESSPILOT_ORT").unwrap());
    let mut reader = BoardReader::new(OnnxPredictor::load(&model, &runtime).unwrap());
    let manifest = manifest();
    let w = manifest["source"][0].as_u64().unwrap() as usize;
    let h = manifest["source"][1].as_u64().unwrap() as usize;
    let source = RgbFrame::new(w, h, include_bytes!("fixtures/vision/demo.rgb").to_vec()).unwrap();
    let mut recovered = false;
    for case in manifest["scenes"].as_array().unwrap() {
        let width = case["width"].as_u64().unwrap() as usize;
        let resized = source
            .resize(
                width,
                (source.height() as f64 * width as f64 / source.width() as f64).round() as usize,
            )
            .unwrap();
        let cw = case["canvas"][0].as_u64().unwrap() as usize;
        let ch = case["canvas"][1].as_u64().unwrap() as usize;
        let x = case["offset"][0].as_u64().unwrap() as usize;
        let y = case["offset"][1].as_u64().unwrap() as usize;
        let mut pixels = vec![32; cw * ch * 3];
        for row in 0..resized.height() {
            pixels[((row + y) * cw + x) * 3..((row + y) * cw + x + width) * 3]
                .copy_from_slice(&resized.pixels()[row * width * 3..(row + 1) * width * 3]);
        }
        let frame = RgbFrame::new(cw, ch, pixels).unwrap();
        let boxes = reader
            .get_positions(&frame, true, &AtomicBool::new(false))
            .unwrap();
        let fen = boxes
            .as_ref()
            .and_then(|b| get_fen_from_position(Color::White, b).unwrap())
            .map(|b| b.fen);
        assert_eq!(
            fen.as_deref(),
            case["fen"].as_str(),
            "Scene width {width}, {cw}x{ch}"
        );
        let expected = case["boxes"].as_array().unwrap();
        let boxes = boxes.unwrap_or_default();
        assert_eq!(boxes.len(), expected.len());
        for (b, expected) in boxes.iter().zip(expected) {
            let coordinates = [b.x, b.y, b.width, b.height];
            for i in 0..4 {
                assert_eq!(
                    coordinates[i],
                    expected[i].as_f64().unwrap(),
                    "Scene {width}, box {expected}"
                );
            }
            assert!((b.confidence - expected[4].as_f64().unwrap()).abs() < 1e-5);
            assert_eq!(b.class_id, expected[5].as_f64().unwrap() as u8);
        }
        if cw > width && case["normal_count"] == 0 && !boxes.is_empty() {
            recovered = true;
            assert!(reader.inference_count > 1);
        }
    }
    assert!(recovered, "Fixture must exercise a real zoom recovery");
    assert!(OnnxPredictor::load(&model.with_extension("missing"), &runtime).is_err());
}
