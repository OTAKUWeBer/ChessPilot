//! Windows gesture order/timing from game/move_execution.py; OS delivery is not board verification.
use chesspilot_core::{board::Point, config::MoveMode};
use std::{
    fmt,
    sync::atomic::{AtomicBool, Ordering},
    thread,
    time::Duration,
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InputError {
    NotDispatched(String),
    Uncertain(String),
    Cancelled { dispatched: bool },
}
impl fmt::Display for InputError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NotDispatched(message) => write!(f, "Input not dispatched: {message}"),
            Self::Uncertain(message) => write!(f, "Input delivery uncertain: {message}"),
            Self::Cancelled { dispatched } => write!(f, "Input stopped (dispatched: {dispatched})"),
        }
    }
}
impl std::error::Error for InputError {}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PixelPoint {
    pub x: i32,
    pub y: i32,
}
impl TryFrom<Point> for PixelPoint {
    type Error = String;
    fn try_from(value: Point) -> Result<Self, String> {
        let x = value.x.round_ties_even();
        let y = value.y.round_ties_even();
        if !x.is_finite()
            || !y.is_finite()
            || x < i32::MIN as f64
            || x > i32::MAX as f64
            || y < i32::MIN as f64
            || y > i32::MAX as f64
        {
            return Err("Pointer coordinates must be finite signed desktop pixels".into());
        }
        Ok(Self {
            x: x as i32,
            y: y as i32,
        })
    }
}
pub trait Pointer {
    fn move_to(&mut self, point: PixelPoint) -> Result<(), String>;
    fn left_button(&mut self, down: bool) -> Result<(), String>;
    fn wait(&mut self, duration: Duration) {
        thread::sleep(duration);
    }
}
struct Gesture<'a, P: Pointer> {
    pointer: &'a mut P,
    cancelled: &'a AtomicBool,
    held: bool,
    dispatched: bool,
}
impl<P: Pointer> Gesture<'_, P> {
    fn check(&self) -> Result<(), InputError> {
        if self.cancelled.load(Ordering::Acquire) {
            Err(InputError::Cancelled {
                dispatched: self.dispatched,
            })
        } else {
            Ok(())
        }
    }
    fn failure(&self, error: String) -> InputError {
        if self.dispatched {
            InputError::Uncertain(error)
        } else {
            InputError::NotDispatched(error)
        }
    }
    fn move_to(&mut self, point: PixelPoint) -> Result<(), InputError> {
        self.check()?;
        self.pointer.move_to(point).map_err(|e| self.failure(e))
    }
    fn button(&mut self, down: bool) -> Result<(), InputError> {
        self.check()?;
        // A failed API call can leave delivery unknown; always attempt cleanup after a press.
        if down {
            self.held = true;
            self.dispatched = true;
        }
        self.pointer
            .left_button(down)
            .map_err(|e| self.failure(e))?;
        self.held = down;
        Ok(())
    }
    fn wait(&mut self, milliseconds: u64) -> Result<(), InputError> {
        for _ in 0..milliseconds / 5 {
            self.check()?;
            self.pointer.wait(Duration::from_millis(5));
        }
        self.check()
    }
    fn release(&mut self) -> Result<(), InputError> {
        if self.held {
            self.pointer
                .left_button(false)
                .map_err(|e| self.failure(e))?;
            self.held = false;
        }
        Ok(())
    }
}
impl<P: Pointer> Drop for Gesture<'_, P> {
    fn drop(&mut self) {
        let _ = self.release();
    }
}
pub fn windows_move(
    pointer: &mut impl Pointer,
    start: Point,
    end: Point,
    mode: MoveMode,
    cancelled: &AtomicBool,
) -> Result<(), InputError> {
    let first = PixelPoint::try_from(start).map_err(InputError::NotDispatched)?;
    let last = PixelPoint::try_from(end).map_err(InputError::NotDispatched)?;
    let middle = PixelPoint::try_from(Point {
        x: (start.x + end.x) / 2.0,
        y: (start.y + end.y) / 2.0,
    })
    .map_err(InputError::NotDispatched)?;
    let mut gesture = Gesture {
        pointer,
        cancelled,
        held: false,
        dispatched: false,
    };
    let result = (|| {
        gesture.move_to(first)?;
        gesture.button(true)?;
        match mode {
            MoveMode::Drag => {
                gesture.wait(40)?;
                gesture.move_to(middle)?;
                gesture.wait(20)?;
                gesture.move_to(last)?;
                gesture.wait(40)?;
                gesture.button(false)?;
            }
            MoveMode::Click => {
                gesture.wait(20)?;
                gesture.button(false)?;
                gesture.move_to(last)?;
                gesture.button(true)?;
                gesture.wait(20)?;
                gesture.button(false)?;
            }
        }
        gesture.check()
    })();
    // Cleanup failure is more serious than the original error: a button may remain held.
    gesture.release()?;
    result
}
