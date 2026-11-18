//! Primary-monitor GDI capture and physical-pixel Windows pointer input.
use super::{
    input::{PixelPoint, Pointer},
    Capture, CapturedFrame,
};
use crate::vision::RgbFrame;
use std::{ffi::c_void, mem::size_of, ptr::null_mut, time::Instant};
use windows_sys::Win32::{
    Foundation::{POINT, RECT},
    Graphics::Gdi::*,
    UI::{
        HiDpi::*,
        Input::KeyboardAndMouse::*,
        WindowsAndMessaging::{
            GetClientRect, GetCursorPos, GetWindowThreadProcessId, IsChild, IsWindowVisible,
            SetCursorPos, WindowFromPoint,
        },
    },
};
fn failure(operation: &str) -> String {
    format!("{operation} failed: {}", std::io::Error::last_os_error())
}
struct DpiContext(DPI_AWARENESS_CONTEXT);
impl DpiContext {
    fn physical() -> Result<Self, String> {
        let previous =
            unsafe { SetThreadDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2) };
        if previous.is_null() {
            Err(failure("Physical-pixel DPI context"))
        } else {
            Ok(Self(previous))
        }
    }
}
impl Drop for DpiContext {
    fn drop(&mut self) {
        unsafe {
            SetThreadDpiAwarenessContext(self.0);
        }
    }
}
struct CaptureHandles {
    screen: HDC,
    memory: HDC,
    bitmap: HBITMAP,
    previous: HGDIOBJ,
}
impl Drop for CaptureHandles {
    fn drop(&mut self) {
        unsafe {
            if !self.previous.is_null() {
                SelectObject(self.memory, self.previous);
            }
            if !self.bitmap.is_null() {
                DeleteObject(self.bitmap);
            }
            if !self.memory.is_null() {
                DeleteDC(self.memory);
            }
            if !self.screen.is_null() {
                ReleaseDC(null_mut(), self.screen);
            }
        }
    }
}
pub struct WindowsCapture;
impl Capture for WindowsCapture {
    fn capture(&mut self) -> Result<CapturedFrame, String> {
        let _dpi = DpiContext::physical()?;
        unsafe {
            let monitor = MonitorFromPoint(POINT { x: 0, y: 0 }, MONITOR_DEFAULTTOPRIMARY);
            let mut info = MONITORINFO {
                cbSize: size_of::<MONITORINFO>() as u32,
                ..std::mem::zeroed()
            };
            if GetMonitorInfoW(monitor, &mut info) == 0 {
                return Err(failure("Primary monitor query"));
            }
            let rect = info.rcMonitor;
            let width = (rect.right as i64 - rect.left as i64) as usize;
            let height = (rect.bottom as i64 - rect.top as i64) as usize;
            let count = width
                .checked_mul(height)
                .filter(|&n| n > 0 && n <= 64 * 1024 * 1024)
                .ok_or("Invalid monitor dimensions")?;
            if width > i32::MAX as usize || height > i32::MAX as usize {
                return Err("Monitor dimensions exceed GDI limits".into());
            }
            let mut handles = CaptureHandles {
                screen: GetDC(null_mut()),
                memory: null_mut(),
                bitmap: null_mut(),
                previous: null_mut(),
            };
            if handles.screen.is_null() {
                return Err(failure("Desktop DC"));
            }
            handles.memory = CreateCompatibleDC(handles.screen);
            if handles.memory.is_null() {
                return Err(failure("Capture DC"));
            }
            let bitmap_info = BITMAPINFO {
                bmiHeader: BITMAPINFOHEADER {
                    biSize: size_of::<BITMAPINFOHEADER>() as u32,
                    biWidth: width as i32,
                    biHeight: -(height as i32),
                    biPlanes: 1,
                    biBitCount: 32,
                    biCompression: BI_RGB,
                    ..std::mem::zeroed()
                },
                ..std::mem::zeroed()
            };
            let mut pixels: *mut c_void = null_mut();
            handles.bitmap = CreateDIBSection(
                handles.screen,
                &bitmap_info,
                DIB_RGB_COLORS,
                &mut pixels,
                null_mut(),
                0,
            );
            if handles.bitmap.is_null() || pixels.is_null() {
                return Err(failure("Capture bitmap"));
            }
            let previous = SelectObject(handles.memory, handles.bitmap);
            if previous.is_null() || previous as isize == -1 {
                return Err(failure("Select capture bitmap"));
            }
            handles.previous = previous;
            let captured_at = Instant::now();
            if BitBlt(
                handles.memory,
                0,
                0,
                width as i32,
                height as i32,
                handles.screen,
                rect.left,
                rect.top,
                SRCCOPY | CAPTUREBLT,
            ) == 0
            {
                return Err(failure("Desktop capture"));
            }
            if GdiFlush() == 0 {
                return Err(failure("Capture flush"));
            }
            // A top-down 32bpp DIB has BGRA bytes and no per-row padding.
            let bytes = std::slice::from_raw_parts(pixels.cast::<u8>(), count * 4);
            let mut rgb = Vec::with_capacity(count * 3);
            for pixel in bytes.as_chunks::<4>().0 {
                rgb.extend_from_slice(&[pixel[2], pixel[1], pixel[0]]);
            }
            let mut frame =
                CapturedFrame::new(RgbFrame::new(width, height, rgb)?, rect.left, rect.top);
            frame.captured_at = captured_at;
            Ok(frame)
        }
    }
}
pub struct WindowsPointer {
    held: bool,
}
impl WindowsPointer {
    pub fn return_to_window(
        &mut self,
        target: super::return_target::ReturnTarget,
        cancelled: &std::sync::atomic::AtomicBool,
    ) -> Result<(), String> {
        use std::sync::atomic::Ordering;
        if cancelled.load(Ordering::Acquire) {
            return Err("Pointer return stopped".into());
        }
        if self.held || unsafe { GetAsyncKeyState(VK_LBUTTON as i32) } < 0 {
            return Err("Cannot return a held pointer".into());
        }
        let _dpi = DpiContext::physical()?;
        let window = target.window as windows_sys::Win32::Foundation::HWND;
        let mut process = 0;
        let mut rect = RECT {
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
        };
        let mut point = POINT {
            x: target.x,
            y: target.y,
        };
        unsafe {
            GetWindowThreadProcessId(window, &mut process);
            if process != std::process::id()
                || IsWindowVisible(window) == 0
                || GetClientRect(window, &mut rect) == 0
                || target.x < 0
                || target.y < 0
                || target.x >= rect.right
                || target.y >= rect.bottom
                || ClientToScreen(window, &mut point) == 0
            {
                return Err(
                    "Return window is hidden, resized or no longer owned by this app".into(),
                );
            }
            let hit = WindowFromPoint(point);
            if hit != window && IsChild(window, hit) == 0 {
                return Err("Return target is covered by another window".into());
            }
        }
        if cancelled.load(Ordering::Acquire) {
            return Err("Pointer return stopped".into());
        }
        self.move_to(PixelPoint {
            x: point.x,
            y: point.y,
        })
    }
    pub fn new() -> Result<Self, String> {
        if unsafe { GetAsyncKeyState(VK_LBUTTON as i32) } < 0 {
            return Err("Release the mouse button before starting a move".into());
        }
        Ok(Self { held: false })
    }
}
impl Pointer for WindowsPointer {
    fn move_to(&mut self, point: PixelPoint) -> Result<(), String> {
        let _dpi = DpiContext::physical()?;
        unsafe {
            if SetCursorPos(point.x, point.y) == 0 {
                return Err(failure("Move pointer"));
            }
            let mut actual = POINT { x: 0, y: 0 };
            if GetCursorPos(&mut actual) == 0 {
                return Err(failure("Read pointer"));
            }
            if actual.x != point.x || actual.y != point.y {
                return Err("Pointer position was clipped or changed".into());
            }
        }
        Ok(())
    }
    fn left_button(&mut self, down: bool) -> Result<(), String> {
        let input = INPUT {
            r#type: INPUT_MOUSE,
            Anonymous: INPUT_0 {
                mi: MOUSEINPUT {
                    dwFlags: if down {
                        MOUSEEVENTF_LEFTDOWN
                    } else {
                        MOUSEEVENTF_LEFTUP
                    },
                    ..unsafe { std::mem::zeroed() }
                },
            },
        };
        if down {
            self.held = true;
        }
        if unsafe { SendInput(1, &input, size_of::<INPUT>() as i32) } != 1 {
            return Err(failure("Mouse input (may be blocked by desktop permissions or application integrity level)"));
        }
        self.held = down;
        Ok(())
    }
}
impl Drop for WindowsPointer {
    fn drop(&mut self) {
        if self.held {
            let _ = self.left_button(false);
        }
    }
}
