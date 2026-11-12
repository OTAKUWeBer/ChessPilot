//! Bounded native diagnostics. Rotation follows logging_setup.py's 5 MiB / five-backup policy.
use log::{Level, LevelFilter, Log, Metadata, Record};
use serde_json::{json, Value};
use std::{
    collections::VecDeque,
    fmt::{self, Write as _},
    fs::{self, File, OpenOptions},
    io::{self, IsTerminal, Write},
    path::{Path, PathBuf},
    sync::{
        mpsc::{self, SyncSender, TrySendError},
        Mutex, Once,
    },
    thread,
    time::{Duration, Instant},
};
pub const LOG_FILENAME: &str = "chesspilot-native.log";
pub const MAX_LOG_BYTES: u64 = 5 * 1024 * 1024;
pub const BACKUP_COUNT: usize = 5;
const MAX_RECORD: usize = 16 * 1024;
const MAX_TAIL: usize = 32 * 1024;

pub struct RotatingLog {
    directory: PathBuf,
    file: Option<File>,
    length: u64,
    limit: u64,
    backups: usize,
    _lock: File,
}
impl RotatingLog {
    pub fn new(directory: &Path, limit: u64, backups: usize) -> io::Result<Self> {
        if limit == 0 || backups > 32 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "Invalid log retention limits",
            ));
        }
        fs::create_dir_all(directory)?;
        let directory = directory.canonicalize()?;
        let lock = OpenOptions::new()
            .create(true)
            .read(true)
            .write(true)
            .truncate(false)
            .open(directory.join(".chesspilot-native.lock"))?;
        lock.try_lock().map_err(|e| {
            io::Error::other(format!(
                "Another logger owns this directory, or locking failed: {e}"
            ))
        })?;
        let mut log = Self {
            directory,
            file: None,
            length: 0,
            limit,
            backups,
            _lock: lock,
        };
        log.open()?;
        Ok(log)
    }
    fn path(&self, index: usize) -> PathBuf {
        self.directory.join(if index == 0 {
            LOG_FILENAME.into()
        } else {
            format!("{LOG_FILENAME}.{index}")
        })
    }
    fn check_paths(&self) -> io::Result<()> {
        for n in 0..=self.backups {
            match fs::symlink_metadata(self.path(n)) {
                Ok(metadata) if !metadata.is_file() || metadata.file_type().is_symlink() => {
                    return Err(io::Error::other(
                        "Refusing to replace a non-regular log file",
                    ))
                }
                Ok(_) => {}
                Err(e) if e.kind() == io::ErrorKind::NotFound => {}
                Err(e) => return Err(e),
            }
        }
        Ok(())
    }
    fn open(&mut self) -> io::Result<()> {
        self.check_paths()?;
        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(self.path(0))?;
        self.length = file.metadata()?.len();
        self.file = Some(file);
        Ok(())
    }
    fn rotate(&mut self) -> io::Result<()> {
        self.check_paths()?;
        self.file.take();
        if self.backups == 0 {
            fs::remove_file(self.path(0))?;
        } else {
            match fs::remove_file(self.path(self.backups)) {
                Ok(()) => {}
                Err(e) if e.kind() == io::ErrorKind::NotFound => {}
                Err(e) => return Err(e),
            }
            for n in (0..self.backups).rev() {
                match fs::rename(self.path(n), self.path(n + 1)) {
                    Ok(()) => {}
                    Err(e) if e.kind() == io::ErrorKind::NotFound => {}
                    Err(e) => return Err(e),
                }
            }
        }
        self.open()
    }
    pub fn append(&mut self, line: &str) -> io::Result<()> {
        if self.file.is_none() {
            self.open()?;
        }
        let mut end = line.len().min(self.limit.min(usize::MAX as u64) as usize);
        while !line.is_char_boundary(end) {
            end -= 1;
        }
        if self.length > 0 && self.length.saturating_add(end as u64) > self.limit {
            self.rotate()?;
        }
        if let Err(error) = self
            .file
            .as_mut()
            .expect("Opened above")
            .write_all(&line.as_bytes()[..end])
        {
            self.file.take();
            return Err(error);
        }
        self.length += end as u64;
        Ok(())
    }
    fn flush(&mut self) -> io::Result<()> {
        if let Some(f) = &mut self.file {
            f.flush()?;
        }
        Ok(())
    }
}

/// Preserve the Python Windows/XDG order while rejecting relative environment-directory values.
pub fn default_directories(
    os: &str,
    environment: impl Fn(&str) -> Option<PathBuf>,
    cwd: &Path,
) -> Vec<PathBuf> {
    let absolute = |key: &str| environment(key).filter(|p| p.is_absolute());
    if let Some(path) = absolute("CHESSPILOT_LOG_DIR") {
        return vec![path];
    }
    if os == "android" {
        return vec![];
    }
    let home = absolute("USERPROFILE").or_else(|| absolute("HOME"));
    let primary = if os == "windows" {
        absolute("LOCALAPPDATA")
            .or_else(|| home.as_ref().map(|h| h.join("AppData/Local")))
            .map(|h| h.join("ChessPilot/logs"))
    } else {
        absolute("XDG_STATE_HOME")
            .or_else(|| absolute("XDG_DATA_HOME"))
            .or_else(|| home.as_ref().map(|h| h.join(".local/share")))
            .map(|h| h.join("chesspilot/logs"))
    };
    primary
        .into_iter()
        .chain(home.map(|h| h.join(".chesspilot/logs")))
        .chain([cwd.join("logs")])
        .collect()
}
enum Event {
    Line(Level, String),
    Flush(SyncSender<()>),
}
struct Status {
    directory: Option<PathBuf>,
    error: Option<String>,
    sender: Option<SyncSender<Event>>,
    recent: VecDeque<(Level, String)>,
    dropped: u64,
}
struct Logger {
    status: Mutex<Status>,
}
static LOGGER: Logger = Logger {
    status: Mutex::new(Status {
        directory: None,
        error: None,
        sender: None,
        recent: VecDeque::new(),
        dropped: 0,
    }),
};
static INSTALL: Once = Once::new();
fn install() {
    INSTALL.call_once(|| {
        if log::set_logger(&LOGGER).is_ok() {
            log::set_max_level(LevelFilter::Debug);
        }
        let previous = std::panic::take_hook();
        std::panic::set_hook(Box::new(move |info| {
            log::error!(target:"panic","{info}\n{}",std::backtrace::Backtrace::force_capture());
            flush();
            previous(info);
        }));
    });
}
/// Optional Android path is supplied by its Context before the session is opened.
pub fn configure(directory: Option<&Path>) -> io::Result<PathBuf> {
    install();
    let mut state = LOGGER.status.lock().unwrap_or_else(|e| e.into_inner());
    if let Some(current) = &state.directory {
        if directory.is_some_and(|p| p.canonicalize().ok().as_ref() != Some(current)) {
            return Err(io::Error::other(
                "Restart before changing the log directory",
            ));
        }
        return Ok(current.clone());
    }
    let directories = match directory {
        Some(p) if p.is_absolute() => vec![p.to_path_buf()],
        Some(_) => {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "Log directory must be absolute",
            ))
        }
        None => default_directories(
            std::env::consts::OS,
            |name| std::env::var_os(name).map(PathBuf::from),
            &std::env::current_dir()?,
        ),
    };
    let mut last = io::Error::other("Android log directory has not been configured");
    let mut writer = None;
    for path in directories {
        match RotatingLog::new(&path, MAX_LOG_BYTES, BACKUP_COUNT) {
            Ok(log) => {
                writer = Some(log);
                break;
            }
            Err(e) => last = e,
        }
    }
    let Some(mut writer) = writer else {
        state.error = Some(last.to_string());
        return Err(last);
    };
    let path = writer.directory.clone();
    let (tx, rx) = mpsc::sync_channel(128);
    thread::Builder::new()
        .name("chesspilot-log".into())
        .spawn(move || {
            let console = io::stderr().is_terminal();
            while let Ok(event) = rx.recv() {
                match event {
                    Event::Line(level, line) => {
                        if console {
                            let color = match level {
                                Level::Error => "\x1b[31m",
                                Level::Warn => "\x1b[33m",
                                Level::Info => "\x1b[32m",
                                _ => "\x1b[36m",
                            };
                            let _ = write!(io::stderr(), "{color}{line}\x1b[0m");
                        }
                        if let Err(e) = writer.append(&line) {
                            LOGGER
                                .status
                                .lock()
                                .unwrap_or_else(|e| e.into_inner())
                                .error = Some(e.to_string());
                        }
                    }
                    Event::Flush(done) => {
                        if let Err(e) = writer.flush() {
                            LOGGER
                                .status
                                .lock()
                                .unwrap_or_else(|e| e.into_inner())
                                .error = Some(e.to_string());
                        }
                        let _ = done.try_send(());
                    }
                }
            }
        })?;
    for (level, line) in &state.recent {
        let _ = tx.try_send(Event::Line(*level, line.clone()));
    }
    state.sender = Some(tx);
    state.directory = Some(path.clone());
    state.error = None;
    drop(state);
    log::info!(target:"startup","ChessPilot native diagnostics; timestamps UTC; system={}",crate::cpu::system_info());
    Ok(path)
}
pub fn ensure() {
    if LOGGER
        .status
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .directory
        .is_none()
    {
        let _ = configure(None);
    }
}
struct Line {
    text: String,
    limit: usize,
}
impl fmt::Write for Line {
    fn write_str(&mut self, value: &str) -> fmt::Result {
        for ch in value.chars() {
            let escaped = match ch {
                '\n' => Some("\\n"),
                '\r' => Some("\\r"),
                '\t' => Some("\\t"),
                '\u{1b}' => Some("\\u001b"),
                _ => None,
            };
            let needed = escaped.map(str::len).unwrap_or(ch.len_utf8());
            if self.text.len() + needed > self.limit {
                return Err(fmt::Error);
            }
            if let Some(text) = escaped {
                self.text.push_str(text);
            } else if ch.is_control() {
                self.text.push('?');
            } else {
                self.text.push(ch);
            }
        }
        Ok(())
    }
}
pub fn render(record: &Record<'_>) -> String {
    let now = time::OffsetDateTime::now_utc();
    let mut line = Line {
        text: format!(
            "[{}-{:02}-{:02} {:02}:{:02}:{:02}.{:03}Z] [{:<5}] [",
            now.year(),
            u8::from(now.month()),
            now.day(),
            now.hour(),
            now.minute(),
            now.second(),
            now.millisecond(),
            record.level()
        ),
        limit: MAX_RECORD - 18,
    };
    let target = record.target().chars().take(80).collect::<String>();
    let result = write!(line, "{target}] {}", record.args());
    if result.is_err() {
        line.text.push_str(" ...[truncated]");
    }
    line.text.push('\n');
    line.text
}
impl Log for Logger {
    fn enabled(&self, metadata: &Metadata<'_>) -> bool {
        metadata.level() <= Level::Debug
    }
    fn log(&self, record: &Record<'_>) {
        if !self.enabled(record.metadata()) {
            return;
        }
        let line = render(record);
        let mut state = self.status.lock().unwrap_or_else(|e| e.into_inner());
        if state.recent.len() == 64 {
            state.recent.pop_front();
        }
        state.recent.push_back((record.level(), line.clone()));
        if let Some(sender) = &state.sender {
            match sender.try_send(Event::Line(record.level(), line)) {
                Ok(()) => {}
                Err(TrySendError::Full(_)) => state.dropped = state.dropped.saturating_add(1),
                Err(TrySendError::Disconnected(_)) => {
                    state.error = Some("Native log writer stopped".into())
                }
            }
        }
    }
    fn flush(&self) {
        flush();
    }
}
pub fn flush() {
    let sender = LOGGER
        .status
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .sender
        .clone();
    let Some(sender) = sender else {
        return;
    };
    let (tx, rx) = mpsc::sync_channel(1);
    let until = Instant::now() + Duration::from_secs(1);
    let mut event = Event::Flush(tx);
    loop {
        match sender.try_send(event) {
            Ok(()) => break,
            Err(TrySendError::Full(returned)) if Instant::now() < until => {
                event = returned;
                thread::sleep(Duration::from_millis(2));
            }
            Err(_) => return,
        }
    }
    let _ = rx.recv_timeout(until.saturating_duration_since(Instant::now()));
}
pub fn snapshot(include_tail: bool) -> Value {
    let state = LOGGER.status.lock().unwrap_or_else(|e| e.into_inner());
    let mut tail = String::new();
    if include_tail {
        for (_, line) in state.recent.iter().rev() {
            if tail.len() + line.len() > MAX_TAIL {
                break;
            }
            tail.insert_str(0, line);
        }
    }
    json!({"log_dir":state.directory,"log_path":state.directory.as_ref().map(|p|p.join(LOG_FILENAME)),"write_error":state.error,"dropped_records":state.dropped,"tail":tail,"system":crate::cpu::system_info()})
}
pub fn open_folder() -> Result<(), String> {
    ensure();
    flush();
    let path = LOGGER
        .status
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .directory
        .clone()
        .ok_or("No writable log directory")?;
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        let path: Vec<_> = path.as_os_str().encode_wide().chain([0]).collect();
        let verb: Vec<_> = "open\0".encode_utf16().collect();
        let result = unsafe {
            windows_sys::Win32::UI::Shell::ShellExecuteW(
                std::ptr::null_mut(),
                verb.as_ptr(),
                path.as_ptr(),
                std::ptr::null(),
                std::ptr::null(),
                1,
            )
        } as isize;
        if result <= 32 {
            return Err(format!("File manager could not open logs (code {result})"));
        }
        Ok(())
    }
    #[cfg(target_os = "linux")]
    {
        use std::process::{Command, Stdio};
        let mut child = Command::new("xdg-open")
            .arg(&path)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Could not open log folder: {e}"))?;
        thread::Builder::new()
            .name("log-folder".into())
            .spawn(move || {
                let _ = child.wait();
            })
            .map_err(|e| e.to_string())?;
        Ok(())
    }
    #[cfg(not(any(windows, target_os = "linux")))]
    {
        let _ = path;
        Err("Use Share recent logs on Android".into())
    }
}
