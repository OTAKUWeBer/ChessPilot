//! Port of wayland_capture/wayland.py, restricted to wl_registry/callback and virtual-pointer v1.
use super::input::{PixelPoint, Pointer};
use std::{
    io::{self, Read, Write},
    sync::atomic::{AtomicBool, Ordering},
    time::{Duration, Instant},
};
const INTERFACE: &str = "zwlr_virtual_pointer_manager_v1";
fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}
pub fn string(value: &str) -> io::Result<Vec<u8>> {
    if value.contains('\0') || value.len() > 4095 {
        return Err(invalid("Invalid Wayland string"));
    }
    let mut bytes = ((value.len() + 1) as u32).to_ne_bytes().to_vec();
    bytes.extend_from_slice(value.as_bytes());
    bytes.push(0);
    while !bytes.len().is_multiple_of(4) {
        bytes.push(0);
    }
    Ok(bytes)
}
pub fn message(object: u32, opcode: u16, payload: &[u8]) -> io::Result<Vec<u8>> {
    if object == 0 || !payload.len().is_multiple_of(4) || payload.len() > 65524 {
        return Err(invalid("Invalid Wayland request size/object"));
    }
    let mut bytes = object.to_ne_bytes().to_vec();
    bytes.extend_from_slice(&((((8 + payload.len()) as u32) << 16) | opcode as u32).to_ne_bytes());
    bytes.extend_from_slice(payload);
    Ok(bytes)
}
fn words(values: &[u32]) -> Vec<u8> {
    values.iter().flat_map(|v| v.to_ne_bytes()).collect()
}
fn word(bytes: &[u8], at: usize) -> io::Result<u32> {
    Ok(u32::from_ne_bytes(
        bytes
            .get(at..at + 4)
            .ok_or_else(|| invalid("Truncated Wayland event"))?
            .try_into()
            .unwrap(),
    ))
}
fn read_string(bytes: &[u8], at: usize) -> io::Result<(&str, usize)> {
    let length = word(bytes, at)? as usize;
    if length == 0 || length > 4096 {
        return Err(invalid("Invalid Wayland event string"));
    }
    let end = at
        .checked_add(4 + length)
        .ok_or_else(|| invalid("Wayland string overflow"))?;
    let raw = bytes
        .get(at + 4..end)
        .ok_or_else(|| invalid("Truncated Wayland string"))?;
    if raw.last() != Some(&0) || raw[..raw.len() - 1].contains(&0) {
        return Err(invalid("Invalid Wayland string terminator"));
    }
    let next = (end + 3) & !3;
    if next > bytes.len() {
        return Err(invalid("Truncated Wayland string padding"));
    }
    Ok((
        std::str::from_utf8(&raw[..raw.len() - 1]).map_err(|_| invalid("Invalid Wayland UTF-8"))?,
        next,
    ))
}
pub struct VirtualPointer<S: Read + Write> {
    stream: S,
    extent: (u32, u32),
    timeout: Duration,
    next_id: u32,
    manager_name: Option<u32>,
    pointer: bool,
    held: bool,
    failed: bool,
}
impl<S: Read + Write> VirtualPointer<S> {
    /// The transport must use short read/write timeouts so cancellation/deadlines can be observed.
    pub fn connect(stream: S, width: u32, height: u32, timeout: Duration) -> io::Result<Self> {
        if width == 0 || height == 0 || timeout.is_zero() {
            return Err(invalid("Invalid Wayland capture extent/timeout"));
        }
        let mut client = Self {
            stream,
            extent: (width, height),
            timeout,
            next_id: 6,
            manager_name: None,
            pointer: false,
            held: false,
            failed: false,
        };
        let flag = AtomicBool::new(false);
        let deadline = Instant::now() + timeout;
        client.send(1, 1, &words(&[2]), deadline, &flag)?;
        client.send(1, 0, &words(&[3]), deadline, &flag)?;
        client.until_done(3, deadline, &flag)?;
        let global = client.manager_name.ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::Unsupported,
                "Compositor does not provide wlroots virtual-pointer input; a portal backend is required",
            )
        })?;
        let mut bind = words(&[global]);
        bind.extend(string(INTERFACE)?);
        bind.extend(words(&[1, 4]));
        client.send(2, 0, &bind, deadline, &flag)?;
        client.send(4, 0, &words(&[0, 5]), deadline, &flag)?;
        client.pointer = true;
        client.synchronize(&flag)?;
        Ok(client)
    }
    fn check(deadline: Instant, cancelled: &AtomicBool) -> io::Result<()> {
        if cancelled.load(Ordering::Acquire) {
            return Err(io::ErrorKind::Interrupted.into());
        }
        if Instant::now() >= deadline {
            return Err(io::ErrorKind::TimedOut.into());
        }
        Ok(())
    }
    fn send(
        &mut self,
        object: u32,
        opcode: u16,
        payload: &[u8],
        deadline: Instant,
        cancelled: &AtomicBool,
    ) -> io::Result<()> {
        let bytes = message(object, opcode, payload)?;
        let mut offset = 0;
        while offset < bytes.len() {
            Self::check(deadline, cancelled)?;
            match self.stream.write(&bytes[offset..]) {
                Ok(0) => return Err(io::ErrorKind::WriteZero.into()),
                Ok(n) => offset += n,
                Err(e)
                    if matches!(
                        e.kind(),
                        io::ErrorKind::Interrupted
                            | io::ErrorKind::WouldBlock
                            | io::ErrorKind::TimedOut
                    ) => {}
                Err(e) => return Err(e),
            }
        }
        Ok(())
    }
    fn receive_exact(
        &mut self,
        bytes: &mut [u8],
        deadline: Instant,
        cancelled: &AtomicBool,
    ) -> io::Result<()> {
        let mut offset = 0;
        while offset < bytes.len() {
            Self::check(deadline, cancelled)?;
            match self.stream.read(&mut bytes[offset..]) {
                Ok(0) => return Err(io::ErrorKind::UnexpectedEof.into()),
                Ok(n) => offset += n,
                Err(e)
                    if matches!(
                        e.kind(),
                        io::ErrorKind::Interrupted
                            | io::ErrorKind::WouldBlock
                            | io::ErrorKind::TimedOut
                    ) => {}
                Err(e) => return Err(e),
            }
        }
        Ok(())
    }
    fn until_done(
        &mut self,
        callback: u32,
        deadline: Instant,
        cancelled: &AtomicBool,
    ) -> io::Result<()> {
        for _ in 0..2048 {
            let mut header = [0; 8];
            self.receive_exact(&mut header, deadline, cancelled)?;
            let object = word(&header, 0)?;
            let packed = word(&header, 4)?;
            let size = (packed >> 16) as usize;
            let opcode = packed as u16;
            if object == 0 || size < 8 || !size.is_multiple_of(4) {
                return Err(invalid("Invalid Wayland event header"));
            }
            let mut data = vec![0; size - 8];
            self.receive_exact(&mut data, deadline, cancelled)?;
            match (object, opcode) {
                (1, 0) => {
                    let failed = word(&data, 0)?;
                    let code = word(&data, 4)?;
                    let (text, end) = read_string(&data, 8)?;
                    if end != data.len() {
                        return Err(invalid("Invalid display error"));
                    }
                    return Err(io::Error::other(format!(
                        "Wayland object {failed}, error {code}: {text}"
                    )));
                }
                (1, 1) => {
                    if data.len() != 4 {
                        return Err(invalid("Invalid delete_id event"));
                    }
                }
                (2, 0) => {
                    let name = word(&data, 0)?;
                    let (interface, next) = read_string(&data, 4)?;
                    let version = word(&data, next)?;
                    if next + 4 != data.len() {
                        return Err(invalid("Invalid registry global event"));
                    }
                    if interface == INTERFACE && version >= 1 && self.manager_name.is_none() {
                        self.manager_name = Some(name);
                    }
                }
                (2, 1) => {
                    if data.len() != 4 {
                        return Err(invalid("Invalid global_remove event"));
                    }
                    if self.manager_name == Some(word(&data, 0)?) {
                        return Err(io::Error::new(
                            io::ErrorKind::NotConnected,
                            "Wayland virtual-pointer capability was removed",
                        ));
                    }
                }
                (id, 0) if id == callback => {
                    if data.len() != 4 {
                        return Err(invalid("Invalid sync callback"));
                    }
                    return Ok(());
                }
                _ => return Err(invalid("Unexpected Wayland event object/opcode")),
            }
        }
        Err(invalid("Wayland event limit exceeded"))
    }
    pub fn synchronize(&mut self, cancelled: &AtomicBool) -> io::Result<()> {
        if self.failed {
            return Err(io::ErrorKind::NotConnected.into());
        }
        let id = self.next_id;
        self.next_id = self
            .next_id
            .checked_add(1)
            .ok_or_else(|| invalid("Reconnect Wayland input before object IDs overflow"))?;
        let deadline = Instant::now() + self.timeout;
        let result = self
            .send(1, 0, &words(&[id]), deadline, cancelled)
            .and_then(|_| self.until_done(id, deadline, cancelled));
        if result.is_err() {
            self.failed = true;
        }
        result
    }
    fn event(&mut self, opcode: u16, payload: &[u8]) -> io::Result<()> {
        if self.failed {
            return Err(io::ErrorKind::NotConnected.into());
        }
        let flag = AtomicBool::new(false);
        let deadline = Instant::now() + self.timeout;
        let result = self
            .send(5, opcode, payload, deadline, &flag)
            .and_then(|_| self.send(5, 4, &[], deadline, &flag));
        if result.is_err() {
            self.failed = true;
        }
        result
    }
}
impl<S: Read + Write> Pointer for VirtualPointer<S> {
    fn sequence_complete(&mut self) -> Result<(), String> {
        self.synchronize(&AtomicBool::new(false))
            .map_err(|e| e.to_string())
    }
    fn move_to(&mut self, point: PixelPoint) -> Result<(), String> {
        if point.x < 0
            || point.y < 0
            || point.x as u32 >= self.extent.0
            || point.y as u32 >= self.extent.1
        {
            return Err("Wayland point is outside the captured layout".into());
        }
        self.event(
            1,
            &words(&[
                0,
                point.x as u32,
                point.y as u32,
                self.extent.0,
                self.extent.1,
            ]),
        )
        .map_err(|e| e.to_string())
    }
    fn left_button(&mut self, down: bool) -> Result<(), String> {
        if down {
            self.held = true;
        }
        self.event(2, &words(&[0, 0x110, u32::from(down)]))
            .map_err(|e| e.to_string())?;
        self.held = down;
        Ok(())
    }
}
impl<S: Read + Write> Drop for VirtualPointer<S> {
    fn drop(&mut self) {
        if self.pointer {
            let flag = AtomicBool::new(false);
            let deadline = Instant::now() + Duration::from_millis(50);
            if self.held {
                let _ = self.send(5, 2, &words(&[0, 0x110, 0]), deadline, &flag);
                let _ = self.send(5, 4, &[], deadline, &flag);
            }
            let _ = self.send(5, 8, &[], deadline, &flag);
            let _ = self.send(4, 1, &[], deadline, &flag);
        }
    }
}
