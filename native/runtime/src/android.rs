//! MediaProjection frames and callback-confirmed accessibility gestures; no JVM pointers escape JNI.
use crate::{
    controller::Automation,
    desktop::{input::InputError, Capture, CapturedFrame},
    vision::RgbFrame,
};
use chesspilot_core::{
    board::{BoardGeometry, Point},
    config::MoveMode,
};
use serde_json::{json, Value};
use std::{
    sync::{
        atomic::{AtomicBool, AtomicU64, Ordering},
        Arc, Condvar, Mutex, OnceLock,
    },
    time::{Duration, Instant},
};
#[cfg(target_os = "android")]
mod jni_bridge;

const DEADLINE: Duration = Duration::from_secs(3);
const MAX_PIXELS: usize = 64 * 1024 * 1024;
fn intersects(rect: [i32; 4], start: Point, end: Point) -> bool {
    let mut near = 0.0f64;
    let mut far = 1.0f64;
    for (a, b, low, high) in [
        (start.x, end.x, rect[0] as f64, rect[2] as f64),
        (start.y, end.y, rect[1] as f64, rect[3] as f64),
    ] {
        let delta = b - a;
        if delta == 0. {
            if a < low || a > high {
                return false;
            }
        } else {
            let t1 = (low - a) / delta;
            let t2 = (high - a) / delta;
            near = near.max(t1.min(t2));
            far = far.min(t1.max(t2));
            if near > far {
                return false;
            }
        }
    }
    true
}
fn points(width: usize, height: usize, start: Point, end: Point) -> Result<(), InputError> {
    for p in [start, end] {
        if !p.x.is_finite()
            || !p.y.is_finite()
            || p.x < 0.
            || p.y < 0.
            || p.x >= width as f64
            || p.y >= height as f64
        {
            return Err(InputError::NotDispatched(
                "Android gesture outside captured display".into(),
            ));
        }
    }
    Ok(())
}

pub fn rgba_frame(
    bytes: &[u8],
    width: usize,
    height: usize,
    row_stride: usize,
    pixel_stride: usize,
) -> Result<RgbFrame, String> {
    let count = width
        .checked_mul(height)
        .filter(|&n| n > 0 && n <= MAX_PIXELS)
        .ok_or("Invalid Android frame dimensions")?;
    if !(4..=64).contains(&pixel_stride) {
        return Err("Unsupported Android pixel stride".into());
    }
    let row = (width - 1)
        .checked_mul(pixel_stride)
        .and_then(|n| n.checked_add(4))
        .ok_or("Android row overflow")?;
    let required = (height - 1)
        .checked_mul(row_stride)
        .and_then(|n| n.checked_add(row))
        .ok_or("Android buffer overflow")?;
    if row_stride < row || bytes.len() < required {
        return Err("Truncated Android RGBA buffer".into());
    }
    let mut rgb = Vec::with_capacity(count * 3);
    for y in 0..height {
        for x in 0..width {
            let i = y * row_stride + x * pixel_stride;
            rgb.extend_from_slice(&bytes[i..i + 3]);
        }
    }
    RgbFrame::new(width, height, rgb)
}
struct Frame {
    image: RgbFrame,
    at: Instant,
}
struct Action {
    id: u64,
    start: Point,
    end: Point,
    milliseconds: u64,
    sent: bool,
    abandoned: bool,
    outcome: Option<i32>,
    overlay_revision: u64,
}
#[derive(Default)]
struct State {
    epoch: u64,
    size: Option<(usize, usize)>,
    input: bool,
    frame: Option<Arc<Frame>>,
    next_action: u64,
    action: Option<Action>,
    cancellations: u64,
    frame_requested: bool,
    overlay: Option<[i32; 4]>,
    overlay_changed: Option<Instant>,
    overlay_revision: u64,
    error: Option<String>,
}
#[derive(Default)]
pub struct Bridge {
    state: Mutex<State>,
    changed: Condvar,
}
static BRIDGE: OnceLock<Arc<Bridge>> = OnceLock::new();
pub fn bridge() -> &'static Arc<Bridge> {
    BRIDGE.get_or_init(|| Arc::new(Bridge::default()))
}
impl Bridge {
    pub fn cancel_pending(&self) {
        if let Ok(mut s) = self.state.lock() {
            s.cancellations = s.cancellations.wrapping_add(1);
            if let Some(action) = s.action.as_mut() {
                action.abandoned = true;
            }
            self.changed.notify_all();
        }
    }
    pub fn begin(&self, width: usize, height: usize) -> Result<u64, String> {
        width
            .checked_mul(height)
            .filter(|&n| n > 0 && n <= MAX_PIXELS)
            .ok_or("Invalid capture dimensions")?;
        let mut s = self
            .state
            .lock()
            .map_err(|_| "Android bridge unavailable")?;
        s.epoch = s
            .epoch
            .checked_add(1)
            .ok_or("Capture generation exhausted")?;
        s.size = Some((width, height));
        s.frame = None;
        s.action = None;
        s.error = None;
        s.overlay = None;
        s.overlay_changed = None;
        s.frame_requested = false;
        self.changed.notify_all();
        Ok(s.epoch)
    }
    pub fn invalidate(&self, epoch: u64, reason: &str) {
        if let Ok(mut s) = self.state.lock() {
            if epoch != s.epoch {
                return;
            }
            s.size = None;
            s.frame = None;
            s.error = Some(reason.chars().take(512).collect());
            self.changed.notify_all();
        }
    }
    pub fn input_connected(&self, connected: bool) {
        if let Ok(mut s) = self.state.lock() {
            s.input = connected;
            if !connected {
                s.size = None;
                s.frame = None;
                s.error = Some("Accessibility input disconnected; restart capture".into());
            }
            self.changed.notify_all();
        }
    }
    pub fn frame(&self, epoch: u64, mut image: RgbFrame, age: Duration) -> Result<(), String> {
        let mut s = self
            .state
            .lock()
            .map_err(|_| "Android bridge unavailable")?;
        if s.epoch != epoch || s.size != Some((image.width(), image.height())) {
            return Err("Android capture generation or dimensions changed".into());
        }
        let at = Instant::now().checked_sub(age).ok_or("Invalid frame age")?;
        if s.overlay_changed.is_some_and(|changed| at < changed) {
            return Ok(());
        }
        if let Some(rect) = s.overlay {
            image.mask(rect.map(|n| n as usize), 45)?;
        }
        s.frame = Some(Arc::new(Frame { image, at }));
        s.frame_requested = false;
        self.changed.notify_all();
        Ok(())
    }
    pub fn overlay(&self, epoch: u64, rect: Option<[i32; 4]>) -> Result<(), String> {
        let mut s = self
            .state
            .lock()
            .map_err(|_| "Android bridge unavailable")?;
        let (width, height) = Self::check(&s, epoch)?;
        let rect = if let Some([left, top, right, bottom]) = rect {
            if left >= right || top >= bottom {
                return Err("Invalid overlay bounds".into());
            }
            let clipped = [
                left.clamp(0, width as i32),
                top.clamp(0, height as i32),
                right.clamp(0, width as i32),
                bottom.clamp(0, height as i32),
            ];
            (clipped[0] < clipped[2] && clipped[1] < clipped[3]).then_some(clipped)
        } else {
            None
        };
        if s.overlay != rect {
            s.overlay_revision = s.overlay_revision.wrapping_add(1);
            s.overlay = rect;
            s.overlay_changed = Some(Instant::now());
            s.frame = None;
            s.frame_requested = true;
            self.changed.notify_all();
        }
        Ok(())
    }
    pub fn take_frame_request(&self, epoch: u64) -> bool {
        let Ok(mut s) = self.state.lock() else {
            return false;
        };
        if Self::check(&s, epoch).is_err() {
            return false;
        }
        std::mem::take(&mut s.frame_requested)
    }
    fn check(s: &State, epoch: u64) -> Result<(usize, usize), String> {
        if epoch != s.epoch {
            return Err("Android capture generation changed".into());
        }
        if !s.input {
            return Err("Enable ChessPilot's accessibility service".into());
        }
        s.size.ok_or_else(|| {
            s.error
                .clone()
                .unwrap_or_else(|| "Start full-display capture first".into())
        })
    }
    pub fn open(self: &Arc<Self>) -> Result<(AndroidCapture, AndroidInput), String> {
        let s = self
            .state
            .lock()
            .map_err(|_| "Android bridge unavailable")?;
        Self::check(&s, s.epoch)?;
        let revision = Arc::new(AtomicU64::new(s.overlay_revision));
        Ok((
            AndroidCapture {
                bridge: self.clone(),
                epoch: s.epoch,
                revision: revision.clone(),
            },
            AndroidInput {
                bridge: self.clone(),
                epoch: s.epoch,
                revision,
            },
        ))
    }
    /// Called on Android's main handler. The request is claimed once; callbacks carry IDs only.
    pub fn take_action(&self, epoch: u64) -> Option<Value> {
        let mut s = self.state.lock().ok()?;
        Self::check(&s, epoch).ok()?;
        let overlay = s.overlay;
        let revision = s.overlay_revision;
        let a = s.action.as_mut()?;
        if a.sent || a.abandoned || a.outcome.is_some() {
            return None;
        }
        if a.overlay_revision != revision
            || overlay.is_some_and(|rect| intersects(rect, a.start, a.end))
        {
            a.outcome = Some(1);
            self.changed.notify_all();
            return None;
        }
        a.sent = true;
        Some(
            json!({"epoch":epoch,"id":a.id,"x1":a.start.x,"y1":a.start.y,"x2":a.end.x,"y2":a.end.y,"duration":a.milliseconds}),
        )
    }
    pub fn gesture_current(&self, epoch: u64, id: u64) -> bool {
        let Ok(s) = self.state.lock() else {
            return false;
        };
        Self::check(&s, epoch).is_ok()
            && s.action.as_ref().is_some_and(|a| {
                a.id == id
                    && a.sent
                    && !a.abandoned
                    && a.outcome.is_none()
                    && a.overlay_revision == s.overlay_revision
                    && !s
                        .overlay
                        .is_some_and(|rect| intersects(rect, a.start, a.end))
            })
    }
    /// 0=completed, 1=rejected before dispatch, 2=cancelled/uncertain after dispatch.
    pub fn complete(&self, epoch: u64, id: u64, outcome: i32) {
        if let Ok(mut s) = self.state.lock() {
            if s.epoch != epoch {
                return;
            }
            if let Some(a) = s.action.as_mut() {
                if a.id != id || !a.sent || a.outcome.is_some() {
                    return;
                }
                if a.abandoned {
                    s.action = None;
                } else {
                    a.outcome = Some(if (0..=2).contains(&outcome) {
                        outcome
                    } else {
                        2
                    });
                }
                self.changed.notify_all();
            }
        }
    }
    fn stroke(
        &self,
        epoch: u64,
        revision: u64,
        start: Point,
        end: Point,
        milliseconds: u64,
        cancelled: &AtomicBool,
    ) -> Result<(), InputError> {
        let fail = |e: String| InputError::NotDispatched(e);
        let mut s = self
            .state
            .lock()
            .map_err(|_| fail("Android bridge unavailable".into()))?;
        let (width, height) = Self::check(&s, epoch).map_err(fail)?;
        if s.overlay_revision != revision {
            return Err(fail(
                "Floating controls changed after observation; capture again".into(),
            ));
        }
        points(width, height, start, end)?;
        if s.overlay.is_some_and(|rect| intersects(rect, start, end)) {
            return Err(fail(
                "Move floating controls away from the gesture path".into(),
            ));
        }
        if cancelled.load(Ordering::Acquire) {
            return Err(InputError::Cancelled { dispatched: false });
        }
        if s.action.is_some() {
            return Err(fail(
                "Previous Android gesture is awaiting its callback".into(),
            ));
        }
        if s.frame.as_ref().is_none_or(|f| f.at.elapsed() > DEADLINE) {
            return Err(fail("Android capture is stale".into()));
        }
        s.next_action = s
            .next_action
            .checked_add(1)
            .ok_or_else(|| fail("Android action IDs exhausted".into()))?;
        let id = s.next_action;
        let cancellation = s.cancellations;
        s.action = Some(Action {
            id,
            start,
            end,
            milliseconds,
            sent: false,
            abandoned: false,
            outcome: None,
            overlay_revision: revision,
        });
        let deadline = Instant::now() + DEADLINE;
        loop {
            let sent = s
                .action
                .as_ref()
                .filter(|a| a.id == id)
                .map(|a| a.sent)
                .unwrap_or(true);
            if let Err(e) = Self::check(&s, epoch) {
                if let Some(a) = s.action.as_mut().filter(|a| a.id == id) {
                    a.abandoned = true;
                }
                return Err(if sent {
                    InputError::Uncertain(e)
                } else {
                    fail(e)
                });
            }
            let stopped = cancelled.load(Ordering::Acquire) || s.cancellations != cancellation;
            if stopped || Instant::now() >= deadline {
                if sent {
                    if let Some(action) = s.action.as_mut().filter(|a| a.id == id) {
                        action.abandoned = true;
                    }
                } else {
                    s.action = None;
                }
                return if stopped {
                    Err(InputError::Cancelled { dispatched: sent })
                } else if sent {
                    Err(InputError::Uncertain(
                        "Android gesture callback timed out".into(),
                    ))
                } else {
                    Err(fail(
                        "Android input handler timed out before dispatch".into(),
                    ))
                };
            }
            if let Some(outcome) = s
                .action
                .as_ref()
                .filter(|a| a.id == id)
                .and_then(|a| a.outcome)
            {
                s.action = None;
                return match outcome {
                    0 => Ok(()),
                    1 => Err(fail("Android rejected the gesture".into())),
                    _ => Err(InputError::Uncertain(
                        "Android cancelled the gesture".into(),
                    )),
                };
            }
            s = self
                .changed
                .wait_timeout(s, Duration::from_millis(10))
                .map_err(|_| InputError::Uncertain("Android bridge unavailable".into()))?
                .0;
        }
    }
}
pub struct AndroidCapture {
    bridge: Arc<Bridge>,
    epoch: u64,
    revision: Arc<AtomicU64>,
}
impl Capture for AndroidCapture {
    fn validate_board(&self, geometry: BoardGeometry) -> Result<(), String> {
        let s = self
            .bridge
            .state
            .lock()
            .map_err(|_| "Android bridge unavailable")?;
        Bridge::check(&s, self.epoch)?;
        if s.overlay_revision != self.revision.load(Ordering::Acquire) {
            return Err("Floating controls changed during observation".into());
        }
        if s.overlay.is_some_and(|[l, t, r, b]| {
            geometry.x < r as f64
                && geometry.y < b as f64
                && geometry.x + geometry.square_size * 8. > l as f64
                && geometry.y + geometry.square_size * 8. > t as f64
        }) {
            return Err("Move floating controls outside the chessboard".into());
        }
        Ok(())
    }
    fn capture(&mut self) -> Result<CapturedFrame, String> {
        let deadline = Instant::now() + DEADLINE;
        let mut s = self
            .bridge
            .state
            .lock()
            .map_err(|_| "Android bridge unavailable")?;
        loop {
            Bridge::check(&s, self.epoch)?;
            if let Some(frame) = &s.frame {
                if frame.at.elapsed() <= Duration::from_millis(500) {
                    self.revision.store(s.overlay_revision, Ordering::Release);
                    let image = RgbFrame::new(
                        frame.image.width(),
                        frame.image.height(),
                        frame.image.pixels().to_vec(),
                    )?;
                    let mut captured = CapturedFrame::new(image, 0, 0);
                    captured.captured_at = frame.at;
                    return Ok(captured);
                }
            }
            s.frame_requested = true;
            if Instant::now() >= deadline {
                return Err("No Android capture frame received".into());
            }
            s = self
                .bridge
                .changed
                .wait_timeout(s, Duration::from_millis(20))
                .map_err(|_| "Android bridge unavailable")?
                .0;
        }
    }
}
pub struct AndroidInput {
    bridge: Arc<Bridge>,
    epoch: u64,
    revision: Arc<AtomicU64>,
}
impl Automation for AndroidInput {
    fn move_piece(
        &mut self,
        start: Point,
        end: Point,
        mode: MoveMode,
        cancelled: &AtomicBool,
    ) -> Result<(), InputError> {
        {
            let s = self
                .bridge
                .state
                .lock()
                .map_err(|_| InputError::NotDispatched("Android bridge unavailable".into()))?;
            let (width, height) =
                Bridge::check(&s, self.epoch).map_err(InputError::NotDispatched)?;
            points(width, height, start, end)?;
        }
        if mode == MoveMode::Drag {
            self.bridge.stroke(
                self.epoch,
                self.revision.load(Ordering::Acquire),
                start,
                end,
                200,
                cancelled,
            )
        } else {
            self.tap(start, cancelled)?;
            let after_dispatch = |error: InputError| match error {
                InputError::Cancelled { .. } => InputError::Cancelled { dispatched: true },
                InputError::Uncertain(_) => error,
                _ => InputError::Uncertain(error.to_string()),
            };
            self.wait(Duration::from_millis(40), cancelled)
                .map_err(after_dispatch)?;
            self.tap(end, cancelled).map_err(after_dispatch)
        }
    }
    fn tap(&mut self, point: Point, cancelled: &AtomicBool) -> Result<(), InputError> {
        self.bridge.stroke(
            self.epoch,
            self.revision.load(Ordering::Acquire),
            point,
            point,
            50,
            cancelled,
        )
    }
}
