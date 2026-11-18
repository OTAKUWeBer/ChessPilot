//! Port of board_detection/get_positions.py. Capture supplies packed RGB frames.
mod onnx;
mod preprocess;
use chesspilot_core::{
    config::BOARD_DETECTION_CONFIDENCE,
    detection::{get_fen_from_position, Detection, CHESSBOARD_CLASS_ID},
    Color,
};
pub use onnx::OnnxPredictor;
pub use preprocess::{preprocess_image, Letterbox, RgbFrame};
use std::sync::atomic::{AtomicBool, Ordering};

pub trait Predictor {
    fn predict(&mut self, frame: &RgbFrame) -> Result<Vec<Detection>, String>;
}
pub struct BoardReader<P> {
    pub predictor: P,
    pub inference_count: usize,
}
impl<P: Predictor> BoardReader<P> {
    pub fn new(predictor: P) -> Self {
        Self {
            predictor,
            inference_count: 0,
        }
    }
    fn predict(
        &mut self,
        frame: &RgbFrame,
        cancelled: &AtomicBool,
    ) -> Result<Vec<Detection>, String> {
        if cancelled.load(Ordering::Acquire) {
            return Err("Board detection cancelled".into());
        }
        if self.inference_count >= 64 {
            return Err("Refined search exceeded the inference limit".into());
        }
        self.inference_count += 1;
        let boxes = self.predictor.predict(frame)?;
        if cancelled.load(Ordering::Acquire) {
            return Err("Board detection cancelled".into());
        }
        Ok(boxes)
    }
    fn predict_region(
        &mut self,
        frame: &RgbFrame,
        rect: [usize; 4],
        cancelled: &AtomicBool,
    ) -> Result<Vec<Detection>, String> {
        let crop = frame.crop(rect)?;
        let mut boxes = self.predict(&crop, cancelled)?;
        for b in &mut boxes {
            b.x += rect[0] as f64;
            b.y += rect[1] as f64;
        }
        Ok(boxes)
    }
    fn refine_board(
        &mut self,
        frame: &RgbFrame,
        boxes: &[Detection],
        cancelled: &AtomicBool,
    ) -> Result<Option<Vec<Detection>>, String> {
        for b in boxes.iter().filter(|b| b.class_id == CHESSBOARD_CLASS_ID) {
            let padding = b.width.max(b.height) * 0.05;
            let rect = [
                (b.x - padding).max(0.0) as usize,
                (b.y - padding).max(0.0) as usize,
                (b.x + b.width + padding).min(frame.width() as f64).max(0.0) as usize,
                (b.y + b.height + padding)
                    .min(frame.height() as f64)
                    .max(0.0) as usize,
            ];
            if rect[2] <= rect[0] || rect[3] <= rect[1] {
                continue;
            }
            let refined = self.predict_region(frame, rect, cancelled)?;
            if valid(&refined)? {
                return Ok(Some(refined));
            }
        }
        Ok(None)
    }
    pub fn get_positions(
        &mut self,
        frame: &RgbFrame,
        refined_search: bool,
        cancelled: &AtomicBool,
    ) -> Result<Option<Vec<Detection>>, String> {
        self.inference_count = 0;
        let boxes = self.predict(frame, cancelled)?;
        if !refined_search || valid(&boxes)? {
            return Ok((!boxes.is_empty()).then_some(boxes));
        }
        if let Some(refined) = self.refine_board(frame, &boxes, cancelled)? {
            return Ok(Some(refined));
        }
        let size = frame
            .width()
            .min(frame.height())
            .min(frame.width().max(frame.height()) / 2)
            .max(1);
        let mut xs = vec![0, (frame.width() - size) / 2, frame.width() - size];
        xs.sort_unstable();
        xs.dedup();
        let mut ys = vec![0, (frame.height() - size) / 2, frame.height() - size];
        ys.sort_unstable();
        ys.dedup();
        for top in ys {
            for &left in &xs {
                let boxes =
                    self.predict_region(frame, [left, top, left + size, top + size], cancelled)?;
                if let Some(refined) = self.refine_board(frame, &boxes, cancelled)? {
                    return Ok(Some(refined));
                }
                if valid(&boxes)? {
                    return Ok(Some(boxes));
                }
            }
        }
        Ok(None)
    }
}
fn valid(boxes: &[Detection]) -> Result<bool, String> {
    Ok(!boxes.is_empty() && get_fen_from_position(Color::White, boxes)?.is_some())
}

/// The model emits x1,y1,x2,y2,confidence,class. NumPy stores/scales these as f32.
pub fn decode_boxes(
    rows: &[f32],
    shape: &[i64],
    transform: Letterbox,
) -> Result<Vec<Detection>, String> {
    if shape != [1, 300, 6] || rows.len() != 1800 {
        return Err("Expected model output [1,300,6]".into());
    }
    let mut boxes = Vec::new();
    for r in rows.as_chunks::<6>().0 {
        if r.iter().any(|v| !v.is_finite()) {
            return Err("Model emitted non-finite values".into());
        }
        if r[4] <= BOARD_DETECTION_CONFIDENCE {
            continue;
        }
        if !(0.0..=12.0).contains(&r[5]) || r[5].fract() != 0.0 || r[2] < r[0] || r[3] < r[1] {
            return Err("Model emitted an invalid box/class".into());
        }
        let scale = transform.scale as f32;
        boxes.push(Detection {
            x: ((r[0] - transform.x_offset as f32) / scale).trunc() as f64,
            y: ((r[1] - transform.y_offset as f32) / scale).trunc() as f64,
            width: ((r[2] - r[0]) / scale).trunc() as f64,
            height: ((r[3] - r[1]) / scale).trunc() as f64,
            confidence: r[4] as f64,
            class_id: r[5] as u8,
        });
    }
    Ok(boxes)
}
