//! Capture pixels and input coordinates share physical desktop space.
pub mod input;
#[cfg(windows)]
pub mod windows;
use crate::vision::{BoardReader, Predictor, RgbFrame};
use chesspilot_core::{
    board::Point,
    detection::{get_fen_from_position, DetectedBoard},
    Color,
};
use std::{
    sync::atomic::{AtomicBool, Ordering},
    time::Instant,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CaptureBounds {
    pub x: i32,
    pub y: i32,
    pub width: usize,
    pub height: usize,
}
impl CaptureBounds {
    pub fn input_point(self, point: Point) -> Result<Point, String> {
        if !point.x.is_finite()
            || !point.y.is_finite()
            || point.x < 0.0
            || point.y < 0.0
            || point.x >= self.width as f64
            || point.y >= self.height as f64
        {
            return Err("Input point is outside the captured source".into());
        }
        Ok(Point {
            x: point.x + self.x as f64,
            y: point.y + self.y as f64,
        })
    }
}
pub struct CapturedFrame {
    pub image: RgbFrame,
    pub bounds: CaptureBounds,
    pub captured_at: Instant,
}
impl CapturedFrame {
    pub fn new(image: RgbFrame, x: i32, y: i32) -> Self {
        let bounds = CaptureBounds {
            x,
            y,
            width: image.width(),
            height: image.height(),
        };
        Self {
            image,
            bounds,
            captured_at: Instant::now(),
        }
    }
}
pub trait Capture {
    fn capture(&mut self) -> Result<CapturedFrame, String>;
}
pub struct Observation {
    pub board: DetectedBoard,
    pub source: CaptureBounds,
    pub captured_at: Instant,
    pub inference_count: usize,
}
pub fn observe(
    capture: &mut impl Capture,
    reader: &mut BoardReader<impl Predictor>,
    color: Color,
    cancelled: &AtomicBool,
) -> Result<Observation, String> {
    if cancelled.load(Ordering::Acquire) {
        return Err("Board capture cancelled".into());
    }
    let frame = capture.capture()?;
    if frame.bounds.width != frame.image.width() || frame.bounds.height != frame.image.height() {
        return Err("Capture dimensions changed without updating coordinate metadata".into());
    }
    let boxes = reader.get_positions(&frame.image, true, cancelled)?.ok_or(
        "Chessboard detection failed after refined search; check board size and visibility",
    )?;
    let board = get_fen_from_position(color, &boxes)?.ok_or("Chessboard is unreadable")?;
    Ok(Observation {
        board,
        source: frame.bounds,
        captured_at: frame.captured_at,
        inference_count: reader.inference_count,
    })
}
