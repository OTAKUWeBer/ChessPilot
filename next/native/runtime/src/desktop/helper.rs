//! Bounded native-helper execution; no shell, with output limits and process cleanup.
use std::{
    io::Read,
    process::{Child, Command, Stdio},
    sync::atomic::{AtomicBool, Ordering},
    sync::mpsc,
    thread,
    time::{Duration, Instant},
};
struct Process(Child);
impl Drop for Process {
    fn drop(&mut self) {
        #[cfg(target_os = "linux")]
        unsafe {
            libc::kill(-(self.0.id() as i32), libc::SIGKILL);
        }
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}
pub fn capture(command: Command, timeout: Duration) -> Result<Vec<u8>, String> {
    run(
        command,
        timeout,
        super::ppm::MAX_CAPTURE_BYTES,
        &AtomicBool::new(false),
        || Ok(()),
    )
    .map_err(|e| format!("Capture {e}"))
}
pub fn run(
    mut command: Command,
    timeout: Duration,
    limit: usize,
    cancelled: &AtomicBool,
    mut tick: impl FnMut() -> Result<(), String>,
) -> Result<Vec<u8>, String> {
    if cancelled.load(Ordering::Acquire) {
        return Err("Helper cancelled".into());
    }
    command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000);
    }
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    let mut process = Process(
        command
            .spawn()
            .map_err(|e| format!("Helper could not start: {e}"))?,
    );
    let stdout = process.0.stdout.take().ok_or("Missing helper output")?;
    let stderr = process
        .0
        .stderr
        .take()
        .ok_or("Missing helper diagnostics")?;
    let (tx, rx) = mpsc::sync_channel(1);
    let output = thread::spawn(move || {
        let mut bytes = Vec::new();
        let result = stdout
            .take(limit as u64 + 1)
            .read_to_end(&mut bytes)
            .map(|_| bytes);
        let _ = tx.send(result);
    });
    let errors = thread::spawn(move || {
        let mut bytes = Vec::new();
        let mut reader = stderr;
        let mut buffer = [0; 4096];
        while let Ok(n) = reader.read(&mut buffer) {
            if n == 0 {
                break;
            }
            let keep = (64 * 1024usize).saturating_sub(bytes.len()).min(n);
            bytes.extend_from_slice(&buffer[..keep]);
        }
        bytes
    });
    let deadline = Instant::now() + timeout;
    let mut data = None;
    let result = (|| loop {
        if cancelled.load(Ordering::Acquire) {
            return Err("Helper cancelled".into());
        }
        tick()?;
        if let Ok(value) = rx.try_recv() {
            let bytes = value.map_err(|e| e.to_string())?;
            if bytes.len() > limit {
                return Err("Helper output exceeded limit".into());
            }
            data = Some(bytes);
        }
        if let Some(status) = process.0.try_wait().map_err(|e| e.to_string())? {
            if status.success() {
                return Ok(());
            }
            return Err(format!("Helper exited with {status}"));
        }
        if Instant::now() >= deadline {
            return Err("Helper timed out".into());
        }
        thread::sleep(Duration::from_millis(5));
    })();
    drop(process);
    let _ = output.join();
    let diagnostics = errors.join().unwrap_or_default();
    result.map_err(|e| format!("{e}: {}", String::from_utf8_lossy(&diagnostics).trim()))?;
    let bytes = data
        .or_else(|| rx.try_recv().ok().and_then(Result::ok))
        .ok_or("Helper produced no output")?;
    if bytes.len() > limit {
        return Err("Helper output exceeded limit".into());
    }
    Ok(bytes)
}
