//! X11 uses native protocol requests; wlroots preserves grim + virtual-pointer without Python.
use super::{
    input::{self, InputError, PixelPoint, Pointer},
    unix_socket,
    wayland::VirtualPointer,
    x11_pixels::{self, PixelFormat},
    Capture, CaptureBounds, CapturedFrame,
};
use crate::{controller::Automation, resources};
use chesspilot_core::{board::Point, config::MoveMode};
use std::{
    io::{self, IoSlice},
    net::{TcpStream, ToSocketAddrs},
    os::{fd::AsRawFd, unix::net::UnixStream},
    path::{Path, PathBuf},
    process::Command,
    sync::{atomic::AtomicBool, Arc, Mutex},
    time::{Duration, Instant},
};
use x11rb::{
    connection::Connection,
    protocol::{
        randr::ConnectionExt as _,
        xproto::{self, ConnectionExt as _, ImageFormat, ImageOrder, KeyButMask, VisualClass},
        xtest::ConnectionExt as _,
    },
    reexports::x11rb_protocol::{
        parse_display::{parse_display, ConnectAddress},
        xauth::get_auth,
    },
    rust_connection::{DefaultStream, PollMode, RustConnection, Stream},
    utils::RawFdContainer,
};
const TIMEOUT: Duration = Duration::from_secs(2);
fn text(error: impl std::fmt::Display) -> String {
    error.to_string()
}
struct TimedStream {
    inner: DefaultStream,
    deadline: Mutex<Instant>,
}
impl TimedStream {
    fn budget(&self, duration: Duration) {
        *self.deadline.lock().unwrap_or_else(|e| e.into_inner()) = Instant::now() + duration;
    }
}
impl Stream for TimedStream {
    fn poll(&self, mode: PollMode) -> io::Result<()> {
        let events = (if mode.readable() { libc::POLLIN } else { 0 })
            | (if mode.writable() { libc::POLLOUT } else { 0 });
        unix_socket::poll(
            self.inner.as_raw_fd(),
            events,
            *self.deadline.lock().unwrap_or_else(|e| e.into_inner()),
        )
    }
    fn read(&self, buf: &mut [u8], fds: &mut Vec<RawFdContainer>) -> io::Result<usize> {
        self.inner.read(buf, fds)
    }
    fn write(&self, buf: &[u8], fds: &mut Vec<RawFdContainer>) -> io::Result<usize> {
        self.inner.write(buf, fds)
    }
    fn write_vectored(
        &self,
        buf: &[IoSlice<'_>],
        fds: &mut Vec<RawFdContainer>,
    ) -> io::Result<usize> {
        self.inner.write_vectored(buf, fds)
    }
}
type XConnection = RustConnection<TimedStream>;
fn x_connection() -> Result<(XConnection, usize), String> {
    let display = parse_display(None).map_err(text)?;
    let screen = display.screen as usize;
    let mut last = "No X11 display address".to_owned();
    for address in display.connect_instruction() {
        let connected = match &address {
            ConnectAddress::Socket(path) => unix_socket::connect(Path::new(path), true, TIMEOUT)
                .or_else(|_| unix_socket::connect(Path::new(path), false, TIMEOUT))
                .and_then(DefaultStream::from_unix_stream),
            ConnectAddress::Hostname(host, port) => {
                let deadline = Instant::now() + TIMEOUT;
                let addresses = (*host, *port).to_socket_addrs().map_err(text)?;
                let mut result = Err(io::Error::new(
                    io::ErrorKind::NotConnected,
                    "No X11 server address",
                ));
                for address in addresses {
                    let remaining = deadline.saturating_duration_since(Instant::now());
                    if remaining.is_zero() {
                        break;
                    }
                    result = TcpStream::connect_timeout(&address, remaining)
                        .and_then(DefaultStream::from_tcp_stream);
                    if result.is_ok() {
                        break;
                    }
                }
                result
            }
            _ => return Err("Unsupported X11 transport".into()),
        };
        match connected {
            Ok((stream, (family, address))) => {
                let (auth, data) = get_auth(family, &address, display.display)
                    .unwrap_or(None)
                    .unwrap_or_default();
                return RustConnection::connect_to_stream_with_auth_info(
                    TimedStream {
                        inner: stream,
                        deadline: Mutex::new(Instant::now() + TIMEOUT),
                    },
                    screen,
                    auth,
                    data,
                )
                .map(|conn| (conn, screen))
                .map_err(text);
            }
            Err(error) => last = error.to_string(),
        }
    }
    Err(last)
}
pub struct X11Capture {
    conn: Arc<XConnection>,
    root: u32,
    format: PixelFormat,
    depth: u8,
    visual: u32,
    randr: bool,
}
impl X11Capture {
    fn bounds(&self) -> Result<CaptureBounds, String> {
        self.conn.stream().budget(TIMEOUT);
        if self.randr {
            let monitors = self
                .conn
                .randr_get_monitors(self.root, true)
                .map_err(text)?
                .reply()
                .map_err(text)?
                .monitors;
            let monitor = monitors
                .iter()
                .find(|m| m.primary)
                .or_else(|| monitors.first())
                .ok_or("No active X11 monitor")?;
            Ok(CaptureBounds {
                x: monitor.x as i32,
                y: monitor.y as i32,
                width: monitor.width as usize,
                height: monitor.height as usize,
            })
        } else {
            let geometry = self
                .conn
                .get_geometry(self.root)
                .map_err(text)?
                .reply()
                .map_err(text)?;
            Ok(CaptureBounds {
                x: 0,
                y: 0,
                width: geometry.width as usize,
                height: geometry.height as usize,
            })
        }
    }
}
impl Capture for X11Capture {
    fn capture(&mut self) -> Result<CapturedFrame, String> {
        let bounds = self.bounds()?;
        if bounds
            .width
            .checked_mul(bounds.height)
            .is_none_or(|n| n == 0 || n > 64 * 1024 * 1024)
        {
            return Err("Invalid X11 monitor dimensions".into());
        }
        let started = Instant::now();
        let reply = self
            .conn
            .get_image(
                ImageFormat::Z_PIXMAP,
                self.root,
                i16::try_from(bounds.x).map_err(text)?,
                i16::try_from(bounds.y).map_err(text)?,
                u16::try_from(bounds.width).map_err(text)?,
                u16::try_from(bounds.height).map_err(text)?,
                u32::MAX,
            )
            .map_err(text)?
            .reply()
            .map_err(text)?;
        if reply.depth != self.depth || reply.visual != self.visual {
            return Err("X11 visual/depth changed during capture".into());
        }
        let mut frame = CapturedFrame::new(
            x11_pixels::decode(&reply.data, bounds.width, bounds.height, self.format)?,
            bounds.x,
            bounds.y,
        );
        frame.captured_at = started;
        Ok(frame)
    }
}
pub struct X11Pointer {
    conn: Arc<XConnection>,
    root: u32,
    held: bool,
}
impl Pointer for X11Pointer {
    fn move_to(&mut self, point: PixelPoint) -> Result<(), String> {
        self.conn.stream().budget(TIMEOUT);
        let current = self
            .conn
            .query_pointer(self.root)
            .map_err(text)?
            .reply()
            .map_err(text)?;
        let geometry = self
            .conn
            .get_geometry(self.root)
            .map_err(text)?
            .reply()
            .map_err(text)?;
        if [0, geometry.width as i32 - 1].contains(&(current.root_x as i32))
            && [0, geometry.height as i32 - 1].contains(&(current.root_y as i32))
        {
            return Err("X11 fail-safe: move the pointer away from the screen corner".into());
        }
        self.conn
            .xtest_fake_input(
                xproto::MOTION_NOTIFY_EVENT,
                0,
                0,
                self.root,
                i16::try_from(point.x).map_err(text)?,
                i16::try_from(point.y).map_err(text)?,
                0,
            )
            .map_err(text)?
            .check()
            .map_err(text)?;
        let actual = self
            .conn
            .query_pointer(self.root)
            .map_err(text)?
            .reply()
            .map_err(text)?;
        if actual.root_x as i32 != point.x || actual.root_y as i32 != point.y {
            return Err("X11 pointer was clipped or changed".into());
        }
        Ok(())
    }
    fn left_button(&mut self, down: bool) -> Result<(), String> {
        self.conn.stream().budget(if down {
            TIMEOUT
        } else {
            Duration::from_millis(100)
        });
        if down {
            self.held = true;
        }
        self.conn
            .xtest_fake_input(
                if down {
                    xproto::BUTTON_PRESS_EVENT
                } else {
                    xproto::BUTTON_RELEASE_EVENT
                },
                1,
                0,
                self.root,
                0,
                0,
                0,
            )
            .map_err(text)?
            .check()
            .map_err(text)?;
        self.held = down;
        Ok(())
    }
}
impl Drop for X11Pointer {
    fn drop(&mut self) {
        if self.held {
            self.conn.stream().budget(Duration::from_millis(50));
            let _ =
                self.conn
                    .xtest_fake_input(xproto::BUTTON_RELEASE_EVENT, 1, 0, self.root, 0, 0, 0);
            let _ = self.conn.flush();
        }
    }
}
fn open_x11() -> Result<(LinuxCapture, LinuxInput), String> {
    let (conn, screen) = x_connection()?;
    let conn = Arc::new(conn);
    let root = &conn.setup().roots[screen];
    let visual = root
        .allowed_depths
        .iter()
        .flat_map(|d| &d.visuals)
        .find(|v| v.visual_id == root.root_visual)
        .ok_or("Missing X11 root visual")?;
    if visual.class != VisualClass::TRUE_COLOR {
        return Err("X11 capture requires a TrueColor visual".into());
    }
    let format = conn
        .setup()
        .pixmap_formats
        .iter()
        .find(|f| f.depth == root.root_depth)
        .ok_or("Missing X11 pixmap format")?;
    let pixel_format = PixelFormat {
        bits: format.bits_per_pixel,
        padding: format.scanline_pad,
        lsb_first: conn.setup().image_byte_order == ImageOrder::LSB_FIRST,
        masks: [visual.red_mask, visual.green_mask, visual.blue_mask],
    };
    let version = conn
        .randr_query_version(1, 5)
        .ok()
        .and_then(|c| c.reply().ok());
    let randr = version
        .is_some_and(|v| v.major_version > 1 || v.major_version == 1 && v.minor_version >= 5);
    conn.stream().budget(TIMEOUT);
    conn.xtest_get_version(2, 2)
        .map_err(text)?
        .reply()
        .map_err(text)?;
    let pointer = conn
        .query_pointer(root.root)
        .map_err(text)?
        .reply()
        .map_err(text)?;
    if pointer.mask.contains(KeyButMask::BUTTON1) {
        return Err("Release the mouse button before starting ChessPilot input".into());
    }
    let capture = X11Capture {
        conn: conn.clone(),
        root: root.root,
        format: pixel_format,
        depth: root.root_depth,
        visual: root.root_visual,
        randr,
    };
    let input = X11Pointer {
        conn: conn.clone(),
        root: root.root,
        held: false,
    };
    Ok((LinuxCapture::X11(capture), LinuxInput::X11(input)))
}
pub struct GrimCapture {
    program: PathBuf,
    size: (usize, usize),
    first: Option<CapturedFrame>,
}
impl GrimCapture {
    fn grab(program: &Path) -> Result<CapturedFrame, String> {
        let started = Instant::now();
        let mut command = Command::new(program);
        command.args(["-t", "ppm", "-s", "1", "-"]);
        let image = super::ppm::decode(super::helper::capture(command, TIMEOUT)?)?;
        let mut frame = CapturedFrame::new(image, 0, 0);
        frame.captured_at = started;
        Ok(frame)
    }
}
impl Capture for GrimCapture {
    fn capture(&mut self) -> Result<CapturedFrame, String> {
        if let Some(frame) = self.first.take() {
            return Ok(frame);
        }
        let frame = Self::grab(&self.program)?;
        if (frame.image.width(), frame.image.height()) != self.size {
            return Err(
                "Wayland layout dimensions changed; retry to reconnect capture/input".into(),
            );
        }
        Ok(frame)
    }
}
fn open_wayland() -> Result<(LinuxCapture, LinuxInput), String> {
    // shortcut: this preserves the wlroots path; add portal/PipeWire sessions for other compositors.
    let program = resources::executable_path(
        "grim",
        &resources::native_asset_directories().map_err(text)?,
    )
    .map_err(|e| format!("Install or bundle grim for wlroots capture: {e}"))?;
    let frame = GrimCapture::grab(&program)?;
    let size = (frame.image.width(), frame.image.height());
    let display = std::env::var_os("WAYLAND_DISPLAY").unwrap_or_else(|| "wayland-0".into());
    let name = PathBuf::from(display);
    let path = if name.is_absolute() {
        name
    } else {
        if name
            .components()
            .any(|c| !matches!(c, std::path::Component::Normal(_)))
        {
            return Err("Invalid WAYLAND_DISPLAY socket name".into());
        }
        PathBuf::from(std::env::var_os("XDG_RUNTIME_DIR").ok_or("XDG_RUNTIME_DIR is not set")?)
            .join(name)
    };
    let stream = unix_socket::connect(&path, false, TIMEOUT).map_err(text)?;
    stream
        .set_read_timeout(Some(Duration::from_millis(25)))
        .map_err(text)?;
    stream
        .set_write_timeout(Some(Duration::from_millis(25)))
        .map_err(text)?;
    let pointer = VirtualPointer::connect(
        stream,
        u32::try_from(size.0).map_err(text)?,
        u32::try_from(size.1).map_err(text)?,
        TIMEOUT,
    )
    .map_err(text)?;
    Ok((
        LinuxCapture::Wayland(GrimCapture {
            program,
            size,
            first: Some(frame),
        }),
        LinuxInput::Wayland(pointer),
    ))
}
pub enum LinuxCapture {
    X11(X11Capture),
    Wayland(GrimCapture),
}
pub enum LinuxInput {
    X11(X11Pointer),
    Wayland(VirtualPointer<UnixStream>),
}
impl Capture for LinuxCapture {
    fn capture(&mut self) -> Result<CapturedFrame, String> {
        match self {
            Self::X11(c) => c.capture(),
            Self::Wayland(c) => c.capture(),
        }
    }
}
impl Automation for LinuxInput {
    fn move_piece(
        &mut self,
        start: Point,
        end: Point,
        mode: MoveMode,
        cancelled: &AtomicBool,
    ) -> Result<(), InputError> {
        match self {
            Self::X11(pointer) => input::x11_move(pointer, start, end, mode, cancelled),
            Self::Wayland(pointer) => {
                pointer
                    .synchronize(cancelled)
                    .map_err(|e| InputError::NotDispatched(e.to_string()))?;
                input::wayland_move(pointer, start, end, mode, cancelled)?;
                pointer
                    .synchronize(cancelled)
                    .map_err(|e| InputError::Uncertain(e.to_string()))
            }
        }
    }
    fn tap(&mut self, point: Point, cancelled: &AtomicBool) -> Result<(), InputError> {
        match self {
            Self::X11(pointer) => {
                input::linux_tap(pointer, point, cancelled)?;
                self.wait(Duration::from_millis(100), cancelled)
            }
            Self::Wayland(pointer) => {
                pointer
                    .synchronize(cancelled)
                    .map_err(|e| InputError::NotDispatched(e.to_string()))?;
                input::linux_tap(pointer, point, cancelled)?;
                pointer
                    .synchronize(cancelled)
                    .map_err(|e| InputError::Uncertain(e.to_string()))
            }
        }
    }
}
pub fn open() -> Result<(LinuxCapture, LinuxInput), String> {
    let session = std::env::var("XDG_SESSION_TYPE").unwrap_or_default();
    if session == "wayland" || session.is_empty() && std::env::var_os("WAYLAND_DISPLAY").is_some() {
        open_wayland()
    } else {
        open_x11()
    }
}
