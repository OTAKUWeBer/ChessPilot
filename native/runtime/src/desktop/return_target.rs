use serde_json::Value;

/// App-owned native window and physical client pixels, never a click destination.
#[derive(Clone, Copy, Debug)]
pub struct ReturnTarget {
    pub window: u64,
    pub x: i32,
    pub y: i32,
}
impl ReturnTarget {
    pub fn parse(value: &Value) -> Result<Self, String> {
        let window = value
            .get("window")
            .and_then(Value::as_u64)
            .filter(|n| *n != 0 && *n <= usize::MAX as u64)
            .ok_or("Invalid return window")?;
        let coordinate = |name| {
            value
                .get(name)
                .and_then(Value::as_i64)
                .and_then(|n| i32::try_from(n).ok())
                .filter(|n| *n >= 0)
                .ok_or_else(|| format!("Invalid return {name}"))
        };
        Ok(Self {
            window,
            x: coordinate("x")?,
            y: coordinate("y")?,
        })
    }
}
