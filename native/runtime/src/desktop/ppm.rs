//! grim's uncompressed RGB output avoids a PNG codec and preserves binary leading bytes.
use crate::vision::RgbFrame;
pub const MAX_CAPTURE_BYTES: usize = 64 * 1024 * 1024 * 3 + 4096;
pub fn decode(mut bytes: Vec<u8>) -> Result<RgbFrame, String> {
    let mut offset = 0;
    let mut tokens = Vec::new();
    while tokens.len() < 4 {
        while offset < bytes.len() {
            if offset > 4096 {
                return Err("PPM header exceeded limit".into());
            }
            if bytes[offset].is_ascii_whitespace() {
                offset += 1;
            } else if bytes[offset] == b'#' {
                while offset < bytes.len() && bytes[offset] != b'\n' {
                    offset += 1;
                    if offset > 4096 {
                        return Err("PPM header exceeded limit".into());
                    }
                }
            } else {
                break;
            }
        }
        let start = offset;
        while offset < bytes.len() && !bytes[offset].is_ascii_whitespace() && bytes[offset] != b'#'
        {
            offset += 1;
            if offset > 4096 {
                return Err("PPM header exceeded limit".into());
            }
        }
        if start == offset {
            return Err("Truncated PPM header".into());
        }
        tokens.push(
            std::str::from_utf8(&bytes[start..offset])
                .map_err(|_| "Invalid PPM header")?
                .to_owned(),
        );
    }
    if tokens[0] != "P6" || tokens[3] != "255" {
        return Err("Expected P6 RGB8 capture".into());
    }
    let width = tokens[1]
        .parse::<usize>()
        .map_err(|_| "Invalid PPM width")?;
    let height = tokens[2]
        .parse::<usize>()
        .map_err(|_| "Invalid PPM height")?;
    let length = width
        .checked_mul(height)
        .filter(|&n| n > 0 && n <= 64 * 1024 * 1024)
        .and_then(|n| n.checked_mul(3))
        .ok_or("Invalid PPM dimensions")?;
    let delimiter = *bytes.get(offset).ok_or("Missing PPM pixel separator")?;
    if !delimiter.is_ascii_whitespace() {
        return Err("Missing PPM pixel separator".into());
    }
    offset += 1;
    if delimiter == b'\r' && bytes.get(offset) == Some(&b'\n') && bytes.len() - offset == length + 1
    {
        offset += 1;
    }
    if bytes.len() - offset != length {
        return Err("PPM pixel length does not match dimensions".into());
    }
    bytes.drain(..offset);
    RgbFrame::new(width, height, bytes)
}
