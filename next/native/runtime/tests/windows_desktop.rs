#![cfg(windows)]
//! Real API test owns its target window; it never clicks an existing application.
use chesspilot_core::{board::Point, config::MoveMode};
use chesspilot_runtime::desktop::{
    input::windows_move,
    windows::{WindowsCapture, WindowsPointer},
    Capture,
};
use std::{
    ptr::{null, null_mut},
    sync::{atomic::AtomicBool, Mutex},
    time::{Duration, Instant},
};
use windows_sys::Win32::{
    Foundation::*,
    Graphics::Gdi::*,
    System::{
        LibraryLoader::GetModuleHandleW,
        Threading::{GetCurrentProcess, GetGuiResources, GR_GDIOBJECTS},
    },
    UI::{
        HiDpi::{
            GetThreadDpiAwarenessContext, SetThreadDpiAwarenessContext,
            DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2,
        },
        Input::KeyboardAndMouse::{GetAsyncKeyState, VK_LBUTTON},
        WindowsAndMessaging::*,
    },
};

static EVENTS: Mutex<Vec<(u32, i32, i32)>> = Mutex::new(Vec::new());
unsafe extern "system" fn window_proc(
    hwnd: HWND,
    message: u32,
    wparam: WPARAM,
    lparam: LPARAM,
) -> LRESULT {
    match message {
        WM_LBUTTONDOWN | WM_LBUTTONUP => {
            EVENTS.lock().unwrap().push((
                message,
                (lparam & 0xffff) as i16 as i32,
                ((lparam >> 16) & 0xffff) as i16 as i32,
            ));
            0
        }
        WM_PAINT => {
            unsafe {
                let mut paint: PAINTSTRUCT = std::mem::zeroed();
                let dc = BeginPaint(hwnd, &mut paint);
                let top = CreateSolidBrush(0x00332211);
                let bottom = CreateSolidBrush(0x0011aacc);
                FillRect(
                    dc,
                    &RECT {
                        left: 0,
                        top: 0,
                        right: 400,
                        bottom: 150,
                    },
                    top,
                );
                FillRect(
                    dc,
                    &RECT {
                        left: 0,
                        top: 150,
                        right: 400,
                        bottom: 300,
                    },
                    bottom,
                );
                DeleteObject(top);
                DeleteObject(bottom);
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
}
impl Target {
    fn new() -> Self {
        unsafe {
            let mut cursor = POINT { x: 0, y: 0 };
            assert_ne!(GetCursorPos(&mut cursor), 0);
            let name: Vec<_> = "ChessPilot native adapter test\0".encode_utf16().collect();
            let class = WNDCLASSW {
                lpfnWndProc: Some(window_proc),
                hInstance: GetModuleHandleW(null()),
                lpszClassName: name.as_ptr(),
                ..std::mem::zeroed()
            };
            assert_ne!(RegisterClassW(&class), 0);
            let old_dpi = SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
            assert!(!old_dpi.is_null());
            let hwnd = CreateWindowExW(
                WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
                name.as_ptr(),
                name.as_ptr(),
                WS_POPUP | WS_VISIBLE,
                100,
                100,
                400,
                300,
                null_mut(),
                null_mut(),
                class.hInstance,
                null(),
            );
            SetThreadDpiAwarenessContext(old_dpi);
            assert!(!hwnd.is_null(), "{}", std::io::Error::last_os_error());
            UpdateWindow(hwnd);
            Self { hwnd, name, cursor }
        }
    }
    fn pump(&self) {
        unsafe {
            let mut message: MSG = std::mem::zeroed();
            while PeekMessageW(&mut message, null_mut(), 0, 0, PM_REMOVE) != 0 {
                TranslateMessage(&message);
                DispatchMessageW(&message);
            }
        }
    }
    fn button_events(&self, count: usize) -> Vec<(u32, i32, i32)> {
        let deadline = Instant::now() + Duration::from_secs(2);
        loop {
            self.pump();
            let events = EVENTS.lock().unwrap().clone();
            if events.len() >= count {
                return events;
            }
            assert!(
                Instant::now() < deadline,
                "Input was not received by target: {events:?}"
            );
            std::thread::sleep(Duration::from_millis(5));
        }
    }
}
impl Drop for Target {
    fn drop(&mut self) {
        unsafe {
            DestroyWindow(self.hwnd);
            UnregisterClassW(self.name.as_ptr(), GetModuleHandleW(null()));
            SetCursorPos(self.cursor.x, self.cursor.y);
        }
    }
}
#[test]
#[ignore = "Requires CHESSPILOT_DESKTOP_TEST=1 and an interactive Windows desktop; creates its own test window"]
fn real_primary_capture_and_pointer_delivery_to_owned_window() {
    assert_eq!(std::env::var("CHESSPILOT_DESKTOP_TEST").as_deref(), Ok("1"));
    assert!(
        unsafe { GetAsyncKeyState(VK_LBUTTON as i32) } >= 0,
        "Release the physical mouse before the test"
    );
    let target = Target::new();
    target.pump();
    let dpi = unsafe { GetThreadDpiAwarenessContext() };
    let mut capture = WindowsCapture;
    let mut image = capture.capture().unwrap();
    // UpdateWindow paints synchronously, but desktop composition can present it later.
    let presented = Instant::now() + Duration::from_secs(2);
    while Instant::now() < presented {
        let top = (120 * image.image.width() + 120) * 3;
        let bottom = (370 * image.image.width() + 120) * 3;
        if image.image.pixels().get(top..top + 3) == Some(&[0x11, 0x22, 0x33])
            && image.image.pixels().get(bottom..bottom + 3) == Some(&[0xcc, 0xaa, 0x11])
        {
            break;
        }
        target.pump();
        std::thread::sleep(Duration::from_millis(5));
        image = capture.capture().unwrap();
    }
    assert_eq!(
        unsafe { GetThreadDpiAwarenessContext() },
        dpi,
        "Thread DPI context leaked"
    );
    assert_eq!((image.bounds.x, image.bounds.y), (0, 0));
    assert!(image.image.width() >= 500 && image.image.height() >= 400);
    let pixel = |x: usize, y: usize| {
        &image.image.pixels()
            [(y * image.image.width() + x) * 3..(y * image.image.width() + x) * 3 + 3]
    };
    assert_eq!(
        pixel(120, 120),
        [0x11, 0x22, 0x33],
        "RGB channel order/top-down rows"
    );
    assert_eq!(pixel(120, 370), [0xcc, 0xaa, 0x11], "Lower half of target");
    let objects = unsafe { GetGuiResources(GetCurrentProcess(), GR_GDIOBJECTS) };
    for _ in 0..10 {
        capture.capture().unwrap();
    }
    assert!(
        unsafe { GetGuiResources(GetCurrentProcess(), GR_GDIOBJECTS) } <= objects + 1,
        "Capture leaked GDI handles"
    );
    for mode in [MoveMode::Drag, MoveMode::Click] {
        target.pump();
        EVENTS.lock().unwrap().clear();
        let start = Point { x: 140., y: 140. };
        let end = Point { x: 440., y: 340. };
        for point in [start, end] {
            let hit = unsafe {
                let previous =
                    SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
                let hit = WindowFromPoint(POINT {
                    x: point.x as i32,
                    y: point.y as i32,
                });
                SetThreadDpiAwarenessContext(previous);
                hit
            };
            assert_eq!(hit, target.hwnd, "Target is covered; refusing input");
        }
        let mut pointer = WindowsPointer::new().unwrap();
        windows_move(&mut pointer, start, end, mode, &AtomicBool::new(false)).unwrap();
        let expected = if mode == MoveMode::Drag {
            vec![(WM_LBUTTONDOWN, 40, 40), (WM_LBUTTONUP, 340, 240)]
        } else {
            vec![
                (WM_LBUTTONDOWN, 40, 40),
                (WM_LBUTTONUP, 40, 40),
                (WM_LBUTTONDOWN, 340, 240),
                (WM_LBUTTONUP, 340, 240),
            ]
        };
        assert_eq!(target.button_events(expected.len()), expected);
        assert!(
            unsafe { GetAsyncKeyState(VK_LBUTTON as i32) } >= 0,
            "Mouse remained held"
        );
        assert_eq!(unsafe { GetThreadDpiAwarenessContext() }, dpi);
    }
}
