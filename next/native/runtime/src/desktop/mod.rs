//! Pair frame coordinates with their native input adapter (physical or layout-normalized).
pub mod helper;
pub mod input;
#[cfg(target_os = "linux")]
pub mod linux;
pub mod ppm;
#[cfg(target_os = "linux")]
mod unix_socket;
pub mod wayland;
#[cfg(windows)]
pub mod windows;
pub const SUPPORTED: bool = cfg!(any(windows, target_os = "linux", target_os = "android"));
#[cfg(target_os = "android")]
pub fn open() -> Result<(crate::android::AndroidCapture, crate::android::AndroidInput), String> {
    crate::android::bridge().open()
}
#[cfg(windows)]
pub fn open() -> Result<(windows::WindowsCapture, windows::WindowsPointer), String> {
    Ok((windows::WindowsCapture, windows::WindowsPointer::new()?))
}
#[cfg(target_os = "linux")]
pub use linux::open;
pub mod x11_pixels;
use crate::vision::{BoardReader, Predictor, RgbFrame};
use chesspilot_core::{
    board::{BoardGeometry, Point},
    detection::{get_fen_from_position, DetectedBoard, Detection},
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
    fn validate_board(&self, _geometry: BoardGeometry) -> Result<(), String> {
        Ok(())
    }
}
#[derive(Clone)]
pub struct Observation {
    pub board: DetectedBoard,
    pub source: CaptureBounds,
    pub captured_at: Instant,
    pub inference_count: usize,
}
pub struct RawObservation {
    pub boxes: Vec<Detection>,
    pub source: CaptureBounds,
    pub captured_at: Instant,
    pub inference_count: usize,
}
pub fn capture_positions(
    capture: &mut impl Capture,
    reader: &mut BoardReader<impl Predictor>,
    refined: bool,
    cancelled: &AtomicBool,
) -> Result<RawObservation, String> {
    if cancelled.load(Ordering::Acquire) {
        return Err("Board capture cancelled".into());
    }
    let frame = capture.capture()?;
    if frame.bounds.width != frame.image.width() || frame.bounds.height != frame.image.height() {
        return Err("Capture dimensions changed without updating coordinate metadata".into());
    }
    let boxes = reader
        .get_positions(&frame.image, refined, cancelled)?
        .unwrap_or_default();
    Ok(RawObservation {
        boxes,
        source: frame.bounds,
        captured_at: frame.captured_at,
        inference_count: reader.inference_count,
    })
}
pub fn observe(
    capture: &mut impl Capture,
    reader: &mut BoardReader<impl Predictor>,
    color: Color,
    cancelled: &AtomicBool,
) -> Result<Observation, String> {
    let raw = capture_positions(capture, reader, true, cancelled)?;
    let board = get_fen_from_position(color, &raw.boxes)?.ok_or(
        "Chessboard detection failed after refined search; check board size and visibility",
    )?;
    capture.validate_board(board.geometry)?;
    Ok(Observation {
        board,
        source: raw.source,
        captured_at: raw.captured_at,
        inference_count: raw.inference_count,
    })
}
