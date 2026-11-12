#![cfg(windows)]
//! Controlled local board: real capture, ONNX, Stockfish, OS mouse delivery and visual verification.
use chesspilot_core::{board::fen_to_list, detection::CLASS_TO_FEN, Color};
use chesspilot_runtime::{ffi::request, vision::RgbFrame};
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    mem::size_of,
    ptr::{null, null_mut},
    sync::Mutex,
    time::{Duration, Instant},
};
use windows_sys::Win32::{
    Foundation::*,
    Graphics::Gdi::*,
    System::LibraryLoader::GetModuleHandleW,
    UI::{
        HiDpi::*,
        Input::KeyboardAndMouse::{GetAsyncKeyState, VK_LBUTTON},
        WindowsAndMessaging::*,
    },
};
const START: &str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1";
const TILE: usize = 64;
const SIDE: usize = TILE * 8;
struct Board {
    color: Color,
    pieces: [char; 64],
    sprites: HashMap<char, Vec<Option<[u8; 3]>>>,
    selected: Option<usize>,
    down: Option<usize>,
    moves: Vec<(usize, usize)>,
    display_side: i32,
}
impl Board {
    fn new(display_side: i32) -> Self {
        let source = RgbFrame::new(
            568,
            318,
            include_bytes!("fixtures/vision/demo.rgb").to_vec(),
        )
        .unwrap();
        let pieces = fen_to_list(START).unwrap();
        let mut sprites = HashMap::new();
        for (index, &piece) in pieces.iter().enumerate().filter(|(_, p)| **p != ' ') {
            if sprites.contains_key(&piece) {
                continue;
            }
            let col = index % 8;
            let row = index / 8;
            let rect = [
                82 + col * 210 / 8,
                50 + row * 210 / 8,
                82 + (col + 1) * 210 / 8,
                50 + (row + 1) * 210 / 8,
            ];
            let tile = source.crop(rect).unwrap().resize(TILE, TILE).unwrap();
            // Use an empty square of the same color; a king can occupy most of its tile.
            let sample_col = if (col + row) % 2 == 0 { 1 } else { 0 };
            let at = ((50 + 3 * 210 / 8 + 13) * 568 + 82 + sample_col * 210 / 8 + 13) * 3;
            let background = &source.pixels()[at..at + 3];
            let pixels = tile
                .pixels()
                .as_chunks::<3>()
                .0
                .iter()
                .enumerate()
                .map(|(i, pixel)| {
                    let x = i % TILE;
                    let y = i / TILE;
                    if !(4..TILE - 4).contains(&x)
                        || !(2..TILE - 2).contains(&y)
                        || (0..3)
                            .map(|c| pixel[c].abs_diff(background[c]) as u32)
                            .sum::<u32>()
                            < 60
                    {
                        None
                    } else {
                        Some(*pixel)
                    }
                })
                .collect();
            sprites.insert(piece, pixels);
        }
        assert!(CLASS_TO_FEN.iter().all(|p| sprites.contains_key(p)));
        Self {
            color: Color::White,
            pieces,
            sprites,
            selected: None,
            down: None,
            moves: vec![],
            display_side,
        }
    }
    fn pixels(&self) -> Vec<u8> {
        let mut pixels = vec![0; SIDE * SIDE * 4];
        for index in 0..64 {
            let piece = self.pieces[if self.color == Color::White {
                index
            } else {
                63 - index
            }];
            let col = index % 8;
            let row = index / 8;
            let background = if (col + row) % 2 == 0 {
                [238, 238, 210]
            } else {
                [118, 150, 86]
            };
            for y in 0..TILE {
                for x in 0..TILE {
                    let color = self
                        .sprites
                        .get(&piece)
                        .and_then(|s| s[y * TILE + x])
                        .unwrap_or(background);
                    let at = ((row * TILE + y) * SIDE + col * TILE + x) * 4;
                    pixels[at..at + 4].copy_from_slice(&[color[2], color[1], color[0], 0]);
                }
            }
        }
        pixels
    }
    fn square(&self, lparam: LPARAM) -> Option<usize> {
        let x = (lparam & 0xffff) as i16 as i32 - 50;
        let y = ((lparam >> 16) & 0xffff) as i16 as i32 - 50;
        if x < 0 || y < 0 || x >= self.display_side || y >= self.display_side {
            return None;
        }
        let square = (y * 8 / self.display_side * 8 + x * 8 / self.display_side) as usize;
        Some(if self.color == Color::White {
            square
        } else {
            63 - square
        })
    }
    fn release(&mut self, to: Option<usize>) {
        let Some(to) = to else {
            self.down = None;
            self.selected = None;
            return;
        };
        let from = self.selected.or(self.down);
        if let Some(from) = from {
            if from != to && self.pieces[from] != ' ' {
                self.pieces[to] = self.pieces[from];
                self.pieces[from] = ' ';
                self.moves.push((from, to));
                self.selected = None;
            } else {
                self.selected = Some(from);
            }
        }
        self.down = None;
    }
}
static BOARD: Mutex<Option<Board>> = Mutex::new(None);
unsafe extern "system" fn window_proc(
    hwnd: HWND,
    message: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    match message {
        WM_LBUTTONDOWN => {
            let mut board = BOARD.lock().unwrap();
            if let Some(board) = board.as_mut() {
                board.down = board.square(lparam);
            }
            0
        }
        WM_LBUTTONUP => {
            {
                let mut board = BOARD.lock().unwrap();
                if let Some(board) = board.as_mut() {
                    let square = board.square(lparam);
                    board.release(square);
                }
            }
            unsafe {
                InvalidateRect(hwnd, null(), 1);
                UpdateWindow(hwnd);
            }
            0
        }
        WM_PAINT => {
            unsafe {
                let mut paint: PAINTSTRUCT = std::mem::zeroed();
                let dc = BeginPaint(hwnd, &mut paint);
                let brush = CreateSolidBrush(0x002d2d2d);
                FillRect(dc, &paint.rcPaint, brush);
                DeleteObject(brush);
                if let Some(board) = BOARD.lock().unwrap().as_ref() {
                    let pixels = board.pixels();
                    let info = BITMAPINFO {
                        bmiHeader: BITMAPINFOHEADER {
                            biSize: size_of::<BITMAPINFOHEADER>() as u32,
                            biWidth: SIDE as i32,
                            biHeight: -(SIDE as i32),
                            biPlanes: 1,
                            biBitCount: 32,
                            biCompression: BI_RGB,
                            ..std::mem::zeroed()
                        },
                        ..std::mem::zeroed()
                    };
                    StretchDIBits(
                        dc,
                        50,
                        50,
                        board.display_side,
                        board.display_side,
                        0,
                        0,
                        SIDE as i32,
                        SIDE as i32,
                        pixels.as_ptr().cast(),
                        &info,
                        DIB_RGB_COLORS,
                        SRCCOPY,
                    );
                }
                EndPaint(hwnd, &paint);
            }
            0
        }
        _ => unsafe { DefWindowProcW(hwnd, message, wparam, lparam) },
    }
}
struct Target {
    hwnd: HWND,
    name: Vec<u16>,
    cursor: POINT,
    dpi: DPI_AWARENESS_CONTEXT,
}
impl Target {
    fn new() -> Self {
        unsafe {
            let dpi = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
            assert!(!dpi.is_null());
            let mut cursor = POINT { x: 0, y: 0 };
            assert_ne!(GetCursorPos(&mut cursor), 0);
            let width = GetSystemMetrics(SM_CXSCREEN);
            let height = GetSystemMetrics(SM_CYSCREEN);
            let side = ((height - 100).min(width - 100).min(960) / 8) * 8;
            assert!(side >= 400);
            *BOARD.lock().unwrap() = Some(Board::new(side));
            let name: Vec<_> = "ChessPilot controlled pipeline test\0"
                .encode_utf16()
                .collect();
            let class = WNDCLASSW {
                lpfnWndProc: Some(window_proc),
                hInstance: GetModuleHandleW(null()),
                lpszClassName: name.as_ptr(),
                ..std::mem::zeroed()
            };
            assert_ne!(RegisterClassW(&class), 0);
            let hwnd = CreateWindowExW(
                WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
                name.as_ptr(),
                name.as_ptr(),
                WS_POPUP | WS_VISIBLE,
                0,
                0,
                width,
                height,
                null_mut(),
                null_mut(),
                class.hInstance,
                null(),
            );
            assert!(!hwnd.is_null());
            UpdateWindow(hwnd);
            Self {
                hwnd,
                name,
                cursor,
                dpi,
            }
        }
    }
    fn pump(&self) {
        unsafe {
            let mut msg: MSG = std::mem::zeroed();
            while PeekMessageW(&mut msg, null_mut(), 0, 0, PM_REMOVE) != 0 {
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
        }
    }
    fn wait_idle(&self, id: u64) -> Value {
        let deadline = Instant::now() + Duration::from_secs(45);
        loop {
            self.pump();
            let state = request(json!({"command":"status","session":id})).unwrap()["state"].clone();
            if state["busy"] == false {
                return state;
            }
            assert!(
                Instant::now() < deadline,
                "Pipeline did not finish: {state}"
            );
            std::thread::sleep(Duration::from_millis(5));
        }
    }
    fn reset(&self, color: Color) {
        let mut board = BOARD.lock().unwrap();
        let board = board.as_mut().unwrap();
        board.pieces = fen_to_list(START).unwrap();
        board.moves.clear();
        board.down = None;
        board.selected = None;
        board.color = color;
        unsafe {
            InvalidateRect(self.hwnd, null(), 1);
        }
    }
}
impl Drop for Target {
    fn drop(&mut self) {
        unsafe {
            DestroyWindow(self.hwnd);
            UnregisterClassW(self.name.as_ptr(), GetModuleHandleW(null()));
            SetCursorPos(self.cursor.x, self.cursor.y);
            SetThreadDpiAwarenessContext(self.dpi);
        }
        *BOARD.lock().unwrap() = None;
    }
}
#[test]
#[ignore = "Requires CHESSPILOT_MODEL and CHESSPILOT_ORT"]
fn controlled_renderer_is_readable_by_the_real_model() {
    use chesspilot_runtime::vision::{OnnxPredictor, Predictor};
    let mut board = Board::new(512);
    for color in [Color::White, Color::Black] {
        board.color = color;
        let pixels = board.pixels();
        let rgb = pixels
            .as_chunks::<4>()
            .0
            .iter()
            .flat_map(|p| [p[2], p[1], p[0]])
            .collect();
        let frame = RgbFrame::new(512, 512, rgb).unwrap();
        let mut model = OnnxPredictor::load(
            std::path::Path::new(&std::env::var("CHESSPILOT_MODEL").unwrap()),
            std::path::Path::new(&std::env::var("CHESSPILOT_ORT").unwrap()),
        )
        .unwrap();
        let boxes = model.predict(&frame).unwrap();
        let detected = chesspilot_core::detection::get_fen_from_position(color, &boxes).unwrap();
        assert_eq!(
            detected.map(|b| b.fen).as_deref(),
            Some(if color == Color::White {
                START
            } else {
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b - - 0 1"
            })
        );
    }
}
#[test]
#[ignore = "Requires CHESSPILOT_DESKTOP_TEST=1, native engine/model/runtime and interactive Windows; owns a temporary full-screen board"]
fn real_session_plays_and_visually_confirms_one_move_in_drag_and_click_modes() {
    assert_eq!(std::env::var("CHESSPILOT_DESKTOP_TEST").as_deref(), Ok("1"));
    assert!(unsafe { GetAsyncKeyState(VK_LBUTTON as i32) } >= 0);
    let target = Target::new();
    let id = request(json!({"command":"open"})).unwrap()["session"]
        .as_u64()
        .unwrap();
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        request(json!({"command":"initialize","session":id,"engine_path":std::env::var("CHESSPILOT_STOCKFISH").unwrap(),"model_path":std::env::var("CHESSPILOT_MODEL").unwrap(),"runtime_path":std::env::var("CHESSPILOT_ORT").unwrap()})).unwrap();
        let ready = target.wait_idle(id);
        assert!(ready["error"].is_null(), "{ready}");
        assert_eq!(ready["automation_ready"], true);
        for color in [Color::White, Color::Black] {
            for mode in ["drag", "click"] {
                target.reset(color);
                target.pump();
                let side = BOARD.lock().unwrap().as_ref().unwrap().display_side;
                for point in [
                    POINT { x: 55, y: 55 },
                    POINT {
                        x: 45 + side,
                        y: 45 + side,
                    },
                ] {
                    assert_eq!(
                        unsafe { WindowFromPoint(point) },
                        target.hwnd,
                        "Target covered; refusing input"
                    );
                }
                request(json!({"command":"configure","session":id,"color":color.fen(),"depth":10,"mode":mode}))
                .unwrap();
                request(json!({"command":"play","session":id})).unwrap();
                assert!(
                    request(json!({"command":"play","session":id})).is_err(),
                    "Duplicate play must be rejected"
                );
                let played = target.wait_idle(id);
                assert!(played["error"].is_null(), "{mode}: {played}");
                let confirmed = played["confirmed_fen"]
                    .as_str()
                    .expect("Visual confirmation missing");
                let (pieces, moves) = {
                    let guard = BOARD.lock().unwrap();
                    let board = guard.as_ref().unwrap();
                    (board.pieces, board.moves.len())
                };
                assert_eq!(moves, 1, "Exactly one delivered move");
                assert_eq!(
                    fen_to_list(confirmed).unwrap(),
                    pieces,
                    "Predicted FEN must match received pointer events and actual rendered board"
                );
                assert!(played["status"].as_str().unwrap().contains("Move Played:"));
            }
        }
    }));
    request(json!({"command":"close","session":id})).unwrap();
    if let Err(error) = result {
        std::panic::resume_unwind(error);
    }
}
