//! Checked TrueColor ZPixmap conversion, independent of the X11 connection.
use crate::vision::RgbFrame;
#[derive(Clone, Copy)]
pub struct PixelFormat {
    pub bits: u8,
    pub padding: u8,
    pub lsb_first: bool,
    pub masks: [u32; 3],
}
pub fn decode(
    bytes: &[u8],
    width: usize,
    height: usize,
    format: PixelFormat,
) -> Result<RgbFrame, String> {
    if ![16, 24, 32].contains(&format.bits) || ![8, 16, 32].contains(&format.padding) {
        return Err("Unsupported X11 pixel format".into());
    }
    let count = width
        .checked_mul(height)
        .filter(|&n| n > 0 && n <= 64 * 1024 * 1024)
        .ok_or("Invalid X11 frame dimensions")?;
    let stride = width
        .checked_mul(format.bits as usize)
        .and_then(|n| n.checked_add(format.padding as usize - 1))
        .map(|n| n / format.padding as usize * format.padding as usize / 8)
        .ok_or("X11 stride overflow")?;
    let expected = stride
        .checked_mul(height)
        .ok_or("X11 frame size overflow")?;
    if bytes.len() != expected && bytes.len() != expected.div_ceil(4) * 4 {
        return Err("X11 pixel length does not match stride/dimensions".into());
    }
    let mut occupied = 0;
    for mask in format.masks {
        let normalized = mask >> mask.trailing_zeros().min(31);
        if mask == 0
            || mask & occupied != 0
            || mask as u64 >= (1u64 << format.bits)
            || !normalized.checked_add(1).is_some_and(u32::is_power_of_two)
        {
            return Err("Unsupported X11 color masks".into());
        }
        occupied |= mask;
    }
    let size = format.bits as usize / 8;
    let mut rgb = Vec::with_capacity(count * 3);
    for row in bytes[..expected].chunks_exact(stride) {
        for pixel in row[..width * size].chunks_exact(size) {
            let mut value = 0u32;
            for (i, &byte) in pixel.iter().enumerate() {
                let shift = if format.lsb_first {
                    i * 8
                } else {
                    (size - 1 - i) * 8
                };
                value |= (byte as u32) << shift;
            }
            for mask in format.masks {
                let shift = mask.trailing_zeros();
                let max = (mask >> shift) as u64;
                let channel = ((value & mask) >> shift) as u64;
                rgb.push(((channel * 255 + max / 2) / max) as u8);
            }
        }
    }
    RgbFrame::new(width, height, rgb)
}
