//! Pillow-compatible RGB Lanczos/letterbox contract; see third_party/Pillow-LICENSE.txt.
use std::f64::consts::PI;
const INPUT_SIZE: usize = 640;
const PRECISION: i64 = 1 << 22;

#[derive(Debug, Clone)]
pub struct RgbFrame {
    width: usize,
    height: usize,
    pixels: Vec<u8>,
}
impl RgbFrame {
    pub fn new(width: usize, height: usize, pixels: Vec<u8>) -> Result<Self, String> {
        let count = width
            .checked_mul(height)
            .filter(|&n| n > 0 && n <= 64 * 1024 * 1024)
            .ok_or("Invalid frame dimensions")?;
        if count.checked_mul(3) != Some(pixels.len()) {
            return Err("RGB frame length does not match dimensions".into());
        }
        Ok(Self {
            width,
            height,
            pixels,
        })
    }
    pub fn width(&self) -> usize {
        self.width
    }
    pub fn height(&self) -> usize {
        self.height
    }
    pub fn pixels(&self) -> &[u8] {
        &self.pixels
    }
    pub fn mask(&mut self, rect: [usize; 4], value: u8) -> Result<(), String> {
        let [left, top, right, bottom] = rect;
        if left >= right || top >= bottom || right > self.width || bottom > self.height {
            return Err("Mask is outside the frame".into());
        }
        for y in top..bottom {
            self.pixels[(y * self.width + left) * 3..(y * self.width + right) * 3].fill(value);
        }
        Ok(())
    }
    pub fn crop(&self, rect: [usize; 4]) -> Result<Self, String> {
        let [left, top, right, bottom] = rect;
        if left >= right || top >= bottom || right > self.width || bottom > self.height {
            return Err("Crop is outside the frame".into());
        }
        let mut pixels = Vec::with_capacity((right - left) * (bottom - top) * 3);
        for y in top..bottom {
            pixels.extend_from_slice(
                &self.pixels[(y * self.width + left) * 3..(y * self.width + right) * 3],
            );
        }
        Self::new(right - left, bottom - top, pixels)
    }
    pub fn resize(&self, width: usize, height: usize) -> Result<Self, String> {
        if width == 0
            || height == 0
            || width
                .checked_mul(height)
                .is_none_or(|n| n > 64 * 1024 * 1024)
        {
            return Err("Invalid resize dimensions".into());
        }
        let intermediate = width
            .checked_mul(self.height)
            .filter(|&n| n <= 64 * 1024 * 1024)
            .ok_or("Resize intermediate exceeds frame limit")?;
        let mut horizontal = vec![0; intermediate * 3];
        if width == self.width {
            horizontal.copy_from_slice(&self.pixels);
        } else {
            for (x, (start, weights)) in coefficients(self.width, width).into_iter().enumerate() {
                for y in 0..self.height {
                    for channel in 0..3 {
                        let sum = weights
                            .iter()
                            .enumerate()
                            .fold(PRECISION / 2, |sum, (i, w)| {
                                sum + self.pixels[(y * self.width + start + i) * 3 + channel] as i64
                                    * w
                            });
                        horizontal[(y * width + x) * 3 + channel] = (sum >> 22).clamp(0, 255) as u8;
                    }
                }
            }
        }
        if height == self.height {
            return Self::new(width, height, horizontal);
        }
        let mut pixels = vec![0; width * height * 3];
        for (y, (start, weights)) in coefficients(self.height, height).into_iter().enumerate() {
            for x in 0..width {
                for channel in 0..3 {
                    let sum = weights
                        .iter()
                        .enumerate()
                        .fold(PRECISION / 2, |sum, (i, w)| {
                            sum + horizontal[((start + i) * width + x) * 3 + channel] as i64 * w
                        });
                    pixels[(y * width + x) * 3 + channel] = (sum >> 22).clamp(0, 255) as u8;
                }
            }
        }
        Self::new(width, height, pixels)
    }
}
fn coefficients(input: usize, output: usize) -> Vec<(usize, Vec<i64>)> {
    let scale = input as f64 / output as f64;
    let filter_scale = scale.max(1.0);
    let support = 3.0 * filter_scale;
    (0..output)
        .map(|x| {
            let center = (x as f64 + 0.5) * scale;
            let start = ((center - support + 0.5) as i64).max(0) as usize;
            let end = ((center + support + 0.5) as usize).min(input);
            let raw: Vec<_> = (start..end)
                .map(|i| {
                    let distance = (i as f64 - center + 0.5) / filter_scale;
                    if !(-3.0..3.0).contains(&distance) {
                        0.0
                    } else {
                        sinc(distance) * sinc(distance / 3.0)
                    }
                })
                .collect();
            let total: f64 = raw.iter().sum();
            let weights = raw
                .into_iter()
                .map(|w| {
                    if total == 0.0 {
                        0
                    } else {
                        (w / total * PRECISION as f64).round() as i64
                    }
                })
                .collect();
            (start, weights)
        })
        .collect()
}
fn sinc(x: f64) -> f64 {
    if x == 0.0 {
        1.0
    } else {
        (x * PI).sin() / (x * PI)
    }
}

#[derive(Debug, Clone, Copy)]
pub struct Letterbox {
    pub x_offset: usize,
    pub y_offset: usize,
    pub scale: f64,
}
pub fn preprocess_image(frame: &RgbFrame) -> Result<(Vec<f32>, Letterbox), String> {
    let scale =
        (INPUT_SIZE as f64 / frame.width as f64).min(INPUT_SIZE as f64 / frame.height as f64);
    let width = (frame.width as f64 * scale) as usize;
    let height = (frame.height as f64 * scale) as usize;
    let resized = frame.resize(width, height)?;
    let x_offset = (INPUT_SIZE - width) / 2;
    let y_offset = (INPUT_SIZE - height) / 2;
    let plane = INPUT_SIZE * INPUT_SIZE;
    let mut tensor = vec![0.0; 3 * plane];
    for y in 0..height {
        for x in 0..width {
            for channel in 0..3 {
                tensor[channel * plane + (y + y_offset) * INPUT_SIZE + x + x_offset] =
                    resized.pixels[(y * width + x) * 3 + channel] as f32 / 255.0;
            }
        }
    }
    Ok((
        tensor,
        Letterbox {
            x_offset,
            y_offset,
            scale,
        },
    ))
}
