use chesspilot_core::{board::Point, config::MoveMode};
use chesspilot_runtime::desktop::{
    helper,
    input::{self, PixelPoint, Pointer},
    ppm,
    wayland::{self, VirtualPointer},
    x11_pixels::{self, PixelFormat},
};
use serde_json::{json, Value};
use std::{
    io::{Read, Write},
    net::{TcpListener, TcpStream},
    process::Command,
    sync::{atomic::AtomicBool, Arc, Mutex},
    thread,
    time::{Duration, Instant},
};
#[test]
fn ppm_preserves_binary_header_like_pixels_and_validates_dimensions() {
    for header in [
        b"P6\n1 1\n255\n".as_slice(),
        b"P6\r\n1 1\r\n255\r\n",
        b"P6 # image\n1 # width\n1\n255\r",
    ] {
        let mut bytes = header.to_vec();
        bytes.extend_from_slice(&[10, 32, 35]);
        assert_eq!(ppm::decode(bytes).unwrap().pixels(), [10, 32, 35]);
    }
    for bytes in [
        b"P3 1 1 255\nabc".as_slice(),
        b"P6 0 1 255\n",
        b"P6 999999999 99999999 255\n",
        b"P6 1 1 65535\nabcdef",
        b"P6 1 1 255\nab",
        b"P6 1 1 255\nabcd",
        b"P6 #missing newline",
    ] {
        assert!(ppm::decode(bytes.to_vec()).is_err());
    }
}
#[test]
fn x11_pixels_cover_stride_endianness_rgb565_and_bad_masks() {
    let format = PixelFormat {
        bits: 32,
        padding: 32,
        lsb_first: true,
        masks: [0xff0000, 0xff00, 0xff],
    };
    assert_eq!(
        x11_pixels::decode(&[3, 2, 1, 255, 30, 20, 10, 0], 2, 1, format)
            .unwrap()
            .pixels(),
        [1, 2, 3, 10, 20, 30]
    );
    assert_eq!(
        x11_pixels::decode(
            &[0, 1, 2, 3],
            1,
            1,
            PixelFormat {
                lsb_first: false,
                ..format
            }
        )
        .unwrap()
        .pixels(),
        [1, 2, 3]
    );
    assert_eq!(
        x11_pixels::decode(
            &[0, 248, 224, 7],
            2,
            1,
            PixelFormat {
                bits: 16,
                padding: 16,
                lsb_first: true,
                masks: [0xf800, 0x7e0, 0x1f]
            }
        )
        .unwrap()
        .pixels(),
        [255, 0, 0, 0, 255, 0]
    );
    assert_eq!(
        x11_pixels::decode(
            &[3, 2, 1, 0],
            1,
            1,
            PixelFormat {
                bits: 24,
                padding: 8,
                ..format
            }
        )
        .unwrap()
        .pixels(),
        [1, 2, 3]
    );
    for masks in [
        [0, 0xff00, 0xff],
        [0xff, 0xff, 0xff0000],
        [0x550000, 0xff00, 0xff],
    ] {
        assert!(x11_pixels::decode(&[0; 4], 1, 1, PixelFormat { masks, ..format }).is_err());
    }
    assert!(x11_pixels::decode(&[0; 3], 1, 1, format).is_err());
}
#[test]
fn fake_capture() {
    let Ok(mode) = std::env::var("CHESSPILOT_CAPTURE_FIXTURE") else {
        return;
    };
    match mode.as_str() {
        "ok" => {
            std::io::stdout()
                .write_all(b"P6\n1 1\n255\n\0\x20\xff")
                .unwrap();
            std::process::exit(0);
        }
        "error" => {
            eprintln!("capture permission denied");
            std::process::exit(2);
        }
        _ => thread::sleep(Duration::from_secs(5)),
    }
}
fn command(mode: &str) -> Command {
    let mut cmd = Command::new(std::env::current_exe().unwrap());
    cmd.args(["--exact", "fake_capture", "--nocapture"])
        .env("CHESSPILOT_CAPTURE_FIXTURE", mode);
    cmd
}
#[test]
fn capture_helper_returns_binary_errors_and_real_deadlines() {
    assert!(helper::capture(command("ok"), Duration::from_secs(2))
        .unwrap()
        .ends_with(b"P6\n1 1\n255\n\0\x20\xff"));
    assert!(helper::capture(command("error"), Duration::from_secs(2))
        .unwrap_err()
        .contains("permission denied"));
    let start = Instant::now();
    assert!(
        helper::capture(command("silent"), Duration::from_millis(100))
            .unwrap_err()
            .contains("timed out")
    );
    assert!(start.elapsed() < Duration::from_secs(2));
}
type Trace = Arc<Mutex<Vec<(u32, u16, Vec<u8>)>>>;
fn words(values: &[u32]) -> Vec<u8> {
    values.iter().flat_map(|n| n.to_ne_bytes()).collect()
}
fn number(bytes: &[u8], at: usize) -> u32 {
    u32::from_ne_bytes(bytes[at..at + 4].try_into().unwrap())
}
struct Fragmented(TcpStream);
impl Read for Fragmented {
    fn read(&mut self, data: &mut [u8]) -> std::io::Result<usize> {
        let size = data.len().min(1);
        self.0.read(&mut data[..size])
    }
}
impl Write for Fragmented {
    fn write(&mut self, data: &[u8]) -> std::io::Result<usize> {
        self.0.write(&data[..data.len().min(3)])
    }
    fn flush(&mut self) -> std::io::Result<()> {
        self.0.flush()
    }
}
fn compositor(mode: &str) -> (Fragmented, Trace, thread::JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let client = TcpStream::connect(listener.local_addr().unwrap()).unwrap();
    client.set_nodelay(true).unwrap();
    client
        .set_read_timeout(Some(Duration::from_millis(5)))
        .unwrap();
    client
        .set_write_timeout(Some(Duration::from_millis(5)))
        .unwrap();
    let trace: Trace = Arc::new(Mutex::new(vec![]));
    let recorded = trace.clone();
    let mode = mode.to_owned();
    let worker = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        stream
            .set_read_timeout(Some(Duration::from_secs(2)))
            .unwrap();
        stream.set_nodelay(true).unwrap();
        let mut first_sync = true;
        loop {
            let mut header = [0; 8];
            if stream.read_exact(&mut header).is_err() {
                break;
            }
            let object = number(&header, 0);
            let packed = number(&header, 4);
            let opcode = packed as u16;
            let size = (packed >> 16) as usize;
            assert!((8..=65532).contains(&size));
            let mut payload = vec![0; size - 8];
            stream.read_exact(&mut payload).unwrap();
            recorded
                .lock()
                .unwrap()
                .push((object, opcode, payload.clone()));
            if (object, opcode) == (1, 1) {
                if mode == "bad_header" {
                    stream.write_all(&words(&[2, 4 << 16])).unwrap();
                    break;
                }
                if mode != "unsupported" && mode != "silent" {
                    let mut global = words(&[17]);
                    global.extend(wayland::string("zwlr_virtual_pointer_manager_v1").unwrap());
                    global.extend(words(&[7]));
                    stream
                        .write_all(&wayland::message(2, 0, &global).unwrap())
                        .unwrap();
                }
            }
            if (object, opcode) == (1, 0) {
                let id = number(&payload, 0);
                if mode == "silent" {
                    thread::sleep(Duration::from_millis(200));
                    break;
                }
                if mode == "error" {
                    let mut err = words(&[5, 3]);
                    err.extend(wayland::string("input denied").unwrap());
                    stream
                        .write_all(&wayland::message(1, 0, &err).unwrap())
                        .unwrap();
                    break;
                }
                if mode == "removed" && !first_sync {
                    stream
                        .write_all(&wayland::message(2, 1, &words(&[17])).unwrap())
                        .unwrap();
                    break;
                }
                stream
                    .write_all(&wayland::message(id, 0, &words(&[0])).unwrap())
                    .unwrap();
                stream
                    .write_all(&wayland::message(1, 1, &words(&[id])).unwrap())
                    .unwrap();
                first_sync = false;
            }
            if (object, opcode) == (4, 1) {
                break;
            }
        }
    });
    (Fragmented(client), trace, worker)
}
#[test]
fn wire_strings_headers_and_fragmented_roundtrips_match_the_python_pointer_trace() {
    let fixture: Value = serde_json::from_str(include_str!("fixtures/wayland.json")).unwrap();
    for (mode, index) in [(MoveMode::Drag, 0), (MoveMode::Click, 1)] {
        let (stream, trace, server) = compositor("normal");
        let mut pointer =
            VirtualPointer::connect(stream, 1920, 1080, Duration::from_secs(1)).unwrap();
        input::wayland_move(
            &mut pointer,
            Point { x: 100., y: 200. },
            Point { x: 300., y: 400. },
            mode,
            &AtomicBool::new(false),
        )
        .unwrap();
        pointer.synchronize(&AtomicBool::new(false)).unwrap();
        drop(pointer);
        server.join().unwrap();
        let trace = trace.lock().unwrap();
        assert_eq!(trace[0], (1, 1, words(&[2])));
        assert_eq!(trace[1], (1, 0, words(&[3])));
        let bind = &trace
            .iter()
            .find(|(o, op, _)| (*o, *op) == (2, 0))
            .unwrap()
            .2;
        assert_eq!(
            number(bind, bind.len() - 8),
            1,
            "Only implemented v1 is bound"
        );
        let events: Vec<_> = trace
            .iter()
            .filter(|(o, op, _)| *o == 5 && *op != 8)
            .map(|(object, opcode, data)| {
                json!([
                    object,
                    opcode,
                    data.iter().map(|v| format!("{v:02x}")).collect::<String>()
                ])
            })
            .collect();
        assert_eq!(json!(events), fixture["cases"][index]["pointer_requests"]);
    }
    assert!(wayland::string("a\0b").is_err());
    assert!(wayland::message(0, 0, &[]).is_err());
    assert!(wayland::message(1, 0, &[1]).is_err());
}
#[test]
fn unsupported_removed_malformed_silent_and_denied_compositors_are_errors() {
    for mode in ["unsupported", "removed", "bad_header", "silent", "error"] {
        let (stream, _, server) = compositor(mode);
        let start = Instant::now();
        assert!(
            VirtualPointer::connect(stream, 1920, 1080, Duration::from_millis(100)).is_err(),
            "{mode}"
        );
        server.join().unwrap();
        assert!(start.elapsed() < Duration::from_secs(2));
    }
}
#[test]
fn held_wayland_button_is_released_on_drop_and_out_of_bounds_points_are_rejected() {
    let (stream, trace, server) = compositor("normal");
    let mut pointer = VirtualPointer::connect(stream, 1920, 1080, Duration::from_secs(1)).unwrap();
    assert!(pointer.move_to(PixelPoint { x: -1, y: 0 }).is_err());
    pointer.left_button(true).unwrap();
    let stopped = AtomicBool::new(true);
    assert_eq!(
        pointer.synchronize(&stopped).unwrap_err().kind(),
        std::io::ErrorKind::Interrupted
    );
    drop(pointer);
    server.join().unwrap();
    let states: Vec<_> = trace
        .lock()
        .unwrap()
        .iter()
        .filter(|(o, op, _)| (*o, *op) == (5, 2))
        .map(|(_, _, bytes)| number(bytes, 8))
        .collect();
    assert_eq!(states, [1, 0]);
}

struct Timing<'a> {
    waits: Vec<Duration>,
    moves: Vec<PixelPoint>,
    buttons: Vec<bool>,
    stop: bool,
    flag: &'a AtomicBool,
}
impl Pointer for Timing<'_> {
    fn move_to(&mut self, p: PixelPoint) -> Result<(), String> {
        self.moves.push(p);
        Ok(())
    }
    fn left_button(&mut self, b: bool) -> Result<(), String> {
        self.buttons.push(b);
        Ok(())
    }
    fn wait(&mut self, d: Duration) {
        self.waits.push(d);
        if self.stop {
            self.flag.store(true, std::sync::atomic::Ordering::Release);
        }
    }
}
#[test]
fn linux_gesture_timing_and_cancelled_drag_match_existing_paths() {
    for wayland in [false, true] {
        for mode in [MoveMode::Drag, MoveMode::Click] {
            for stop in [false, true] {
                let flag = AtomicBool::new(false);
                let mut pointer = Timing {
                    waits: vec![],
                    moves: vec![],
                    buttons: vec![],
                    stop,
                    flag: &flag,
                };
                let (start, end) = (Point { x: 100., y: 200. }, Point { x: 300., y: 400. });
                let result = if wayland {
                    input::wayland_move(&mut pointer, start, end, mode, &flag)
                } else {
                    input::x11_move(&mut pointer, start, end, mode, &flag)
                };
                assert_eq!(pointer.buttons.last(), Some(&false));
                if stop {
                    assert!(result.is_err());
                } else {
                    result.unwrap();
                    let micros: u128 = pointer.waits.iter().map(Duration::as_micros).sum();
                    assert_eq!(
                        micros,
                        match (wayland, mode) {
                            (true, MoveMode::Drag) => 1000,
                            (true, MoveMode::Click) => 40000,
                            (false, MoveMode::Drag) => 300000,
                            (false, MoveMode::Click) => 240000,
                        }
                    );
                    assert_eq!(
                        pointer.moves.len(),
                        if wayland && mode == MoveMode::Drag {
                            21
                        } else {
                            2
                        }
                    );
                }
            }
        }
    }
}
