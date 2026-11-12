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
    fn sequence_complete(&mut self) -> Result<(), String> {
        Ok(())
    }
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
        if !down {
            self.pointer
                .sequence_complete()
                .map_err(|e| self.failure(e))?;
        }
        Ok(())
    }
    fn wait(&mut self, milliseconds: u64) -> Result<(), InputError> {
        self.wait_for(Duration::from_millis(milliseconds))
    }
    fn wait_for(&mut self, mut duration: Duration) -> Result<(), InputError> {
        while !duration.is_zero() {
            self.check()?;
            let slice = duration.min(Duration::from_millis(5));
            self.pointer.wait(slice);
            duration -= slice;
        }
        self.check()
    }
    fn release(&mut self) -> Result<(), InputError> {
        if self.held {
            self.pointer
                .left_button(false)
                .map_err(|e| self.failure(e))?;
            self.held = false;
            self.pointer
                .sequence_complete()
                .map_err(|e| self.failure(e))?;
        }
        Ok(())
    }
}

pub fn wayland_move(
    pointer: &mut impl Pointer,
    start: Point,
    end: Point,
    mode: MoveMode,
    cancelled: &AtomicBool,
) -> Result<(), InputError> {
    let first = PixelPoint::try_from(start).map_err(InputError::NotDispatched)?;
    let last = PixelPoint::try_from(end).map_err(InputError::NotDispatched)?;
    let mut gesture = Gesture {
        pointer,
        cancelled,
        held: false,
        dispatched: false,
    };
    let result = (|| {
        gesture.move_to(first)?;
        gesture.button(true)?;
        if mode == MoveMode::Drag {
            for step in 1..=20 {
                let x = first.x as f64 + (last.x as f64 - first.x as f64) * step as f64 / 20.;
                let y = first.y as f64 + (last.y as f64 - first.y as f64) * step as f64 / 20.;
                gesture.move_to(PixelPoint {
                    x: x as i32,
                    y: y as i32,
                })?;
                gesture.wait_for(Duration::from_micros(50))?;
            }
            gesture.button(false)?;
        } else {
            gesture.button(false)?;
            gesture.wait(20)?;
            gesture.move_to(last)?;
            gesture.button(true)?;
            gesture.button(false)?;
            gesture.wait(20)?;
        }
        gesture.check()
    })();
    gesture.release()?;
    result
}
pub fn x11_move(
    pointer: &mut impl Pointer,
    start: Point,
    end: Point,
    mode: MoveMode,
    cancelled: &AtomicBool,
) -> Result<(), InputError> {
    let first = PixelPoint::try_from(start).map_err(InputError::NotDispatched)?;
    let last = PixelPoint::try_from(end).map_err(InputError::NotDispatched)?;
    let mut gesture = Gesture {
        pointer,
        cancelled,
        held: false,
        dispatched: false,
    };
    let result = (|| {
        gesture.move_to(first)?;
        gesture.button(true)?;
        if mode == MoveMode::Drag {
            gesture.wait(100)?;
            gesture.move_to(last)?;
            gesture.wait(100)?;
            gesture.button(false)?;
            gesture.wait(100)?;
        } else {
            gesture.button(false)?;
            gesture.wait(120)?;
            gesture.move_to(last)?;
            gesture.button(true)?;
            gesture.button(false)?;
            gesture.wait(120)?;
        }
        gesture.check()
    })();
    gesture.release()?;
    result
}
pub fn linux_tap(
    pointer: &mut impl Pointer,
    point: Point,
    cancelled: &AtomicBool,
) -> Result<(), InputError> {
    let point = PixelPoint::try_from(point).map_err(InputError::NotDispatched)?;
    let mut gesture = Gesture {
        pointer,
        cancelled,
        held: false,
        dispatched: false,
    };
    let result = (|| {
        gesture.move_to(point)?;
        gesture.button(true)?;
        gesture.button(false)?;
        gesture.check()
    })();
    gesture.release()?;
    result
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

pub fn windows_tap(
    pointer: &mut impl Pointer,
    point: Point,
    cancelled: &AtomicBool,
) -> Result<(), InputError> {
    let point = PixelPoint::try_from(point).map_err(InputError::NotDispatched)?;
    let mut gesture = Gesture {
        pointer,
        cancelled,
        held: false,
        dispatched: false,
    };
    let result = (|| {
        gesture.move_to(point)?;
        gesture.button(true)?;
        gesture.wait(50)?;
        gesture.button(false)?;
        gesture.check()
    })();
    gesture.release()?;
    result
}
