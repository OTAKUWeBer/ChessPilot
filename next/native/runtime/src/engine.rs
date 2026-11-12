//! Persistent Stockfish UCI service. Source: services/engine_service.py.
use chesspilot_core::{board::fen_to_list, notation::Move};
use std::{
    collections::VecDeque,
    io::{self, BufRead, BufReader, Read, Write},
    process::{Child, ChildStdin, Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Receiver, RecvTimeoutError},
        Arc, Mutex,
    },
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};

#[derive(Debug, Clone, Copy)]
pub struct Timeouts {
    pub handshake: Duration,
    pub search: Duration,
    pub stop: Duration,
}
impl Default for Timeouts {
    fn default() -> Self {
        Self {
            handshake: Duration::from_secs(10),
            search: Duration::from_secs(15),
            stop: Duration::from_secs(2),
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Score {
    Centipawns(i32),
    Mate(i32),
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Analysis {
    pub best_move: Option<String>,
    pub updated_fen: Option<String>,
    pub score: Option<Score>,
    pub depth: u32,
    pub stopped: bool,
}

/// One owner serializes all engine IO; UI threads send commands to that owner.
pub struct EngineService {
    command: Command,
    options: Vec<String>,
    timeouts: Timeouts,
    process: Option<EngineProcess>,
    last_diagnostics: Vec<String>,
}
impl EngineService {
    pub fn new(command: Command, options: Vec<String>, timeouts: Timeouts) -> io::Result<Self> {
        // Also validate programmatically supplied options at the protocol boundary.
        for option in &options {
            if option.contains(['\n', '\r', '\0']) {
                return Err(invalid("Engine options must be single lines"));
            }
        }
        crate::resources::engine_options(&options.join("\n"))?;
        Ok(Self {
            command,
            options,
            timeouts,
            process: None,
            last_diagnostics: Vec::new(),
        })
    }
    pub fn initialize(&mut self) -> io::Result<()> {
        if let Some(process) = &mut self.process {
            if process.child.try_wait()?.is_none() {
                return Ok(());
            }
        }
        self.cleanup();
        let mut process = EngineProcess::spawn(&mut self.command)?;
        process.send("uci")?;
        process.wait_for("uciok", self.timeouts.handshake)?;
        for option in &self.options {
            process.send(option)?;
        }
        process.ready(self.timeouts.handshake)?;
        self.process = Some(process);
        Ok(())
    }
    pub fn cleanup(&mut self) {
        if let Some(process) = self.process.take() {
            let diagnostics = process.diagnostics.clone();
            drop(process);
            self.last_diagnostics = diagnostics
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .iter()
                .cloned()
                .collect();
        }
    }
    pub fn process_id(&self) -> Option<u32> {
        self.process.as_ref().map(|p| p.child.id())
    }
    pub fn diagnostics(&self) -> Vec<String> {
        self.process
            .as_ref()
            .map(|p| {
                p.diagnostics
                    .lock()
                    .unwrap_or_else(|e| e.into_inner())
                    .iter()
                    .cloned()
                    .collect()
            })
            .unwrap_or_else(|| self.last_diagnostics.clone())
    }
    pub fn get_best_move(
        &mut self,
        depth: u32,
        fen: &str,
        cancelled: &AtomicBool,
        mut progress: impl FnMut(u32, Option<Score>),
    ) -> io::Result<Analysis> {
        validate_fen(fen)?;
        if !(1..=128).contains(&depth) {
            return Err(invalid("Analysis depth must be between 1 and 128"));
        }
        if cancelled.load(Ordering::Acquire) {
            return Err(interrupted());
        }
        self.initialize()?;
        if cancelled.load(Ordering::Acquire) {
            return Err(interrupted());
        }
        let result = self.process.as_mut().expect("Initialized above").analyze(
            depth,
            fen,
            cancelled,
            &mut progress,
            self.timeouts,
        );
        if result.is_err() {
            self.cleanup();
        }
        result
    }
}

struct EngineProcess {
    child: Child,
    input: Option<ChildStdin>,
    output: Option<Receiver<io::Result<String>>>,
    readers: Vec<JoinHandle<()>>,
    diagnostics: Arc<Mutex<VecDeque<String>>>,
}
impl EngineProcess {
    fn spawn(command: &mut Command) -> io::Result<Self> {
        command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            command.creation_flags(0x08000000); // CREATE_NO_WINDOW, as in Python.
        }
        let mut child = command.spawn()?;
        let input = child.stdin.take();
        let stdout = child.stdout.take().expect("Piped stdout");
        let stderr = child.stderr.take().expect("Piped stderr");
        let (tx, rx) = mpsc::sync_channel(256);
        let diagnostics = Arc::new(Mutex::new(VecDeque::new()));
        let mut process = Self {
            child,
            input,
            output: Some(rx),
            readers: Vec::new(),
            diagnostics: diagnostics.clone(),
        };
        process.readers.push(
            thread::Builder::new()
                .name("stockfish-stdout".into())
                .spawn(move || {
                    let mut reader = BufReader::new(stdout);
                    loop {
                        let line = read_line(&mut reader);
                        let done = line.is_err();
                        if tx.send(line).is_err() || done {
                            break;
                        }
                    }
                })?,
        );
        process.readers.push(
            thread::Builder::new()
                .name("stockfish-stderr".into())
                .spawn(move || {
                    let mut reader = BufReader::new(stderr);
                    while let Ok(line) = read_line(&mut reader) {
                        let mut log = diagnostics.lock().unwrap_or_else(|e| e.into_inner());
                        if log.len() == 64 {
                            log.pop_front();
                        }
                        log.push_back(line);
                    }
                })?,
        );
        Ok(process)
    }
    fn send(&mut self, command: &str) -> io::Result<()> {
        let input = self
            .input
            .as_mut()
            .ok_or_else(|| invalid("Engine input closed"))?;
        writeln!(input, "{command}")?;
        input.flush()
    }
    fn receive(&self, deadline: Instant) -> io::Result<String> {
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            return Err(timeout());
        }
        match self
            .output
            .as_ref()
            .expect("Live receiver")
            .recv_timeout(remaining)
        {
            Ok(line) => {
                let line = line?;
                if line.contains("CRITICAL ERROR:") {
                    return Err(invalid(&line));
                }
                Ok(line)
            }
            Err(RecvTimeoutError::Timeout) => Err(timeout()),
            Err(RecvTimeoutError::Disconnected) => Err(io::Error::new(
                io::ErrorKind::UnexpectedEof,
                "Stockfish output closed",
            )),
        }
    }
    fn wait_for(&self, expected: &str, duration: Duration) -> io::Result<()> {
        let deadline = Instant::now() + duration;
        loop {
            if self.receive(deadline)? == expected {
                return Ok(());
            }
        }
    }
    fn ready(&mut self, duration: Duration) -> io::Result<()> {
        self.send("isready")?;
        self.wait_for("readyok", duration)
    }
    fn analyze(
        &mut self,
        depth: u32,
        fen: &str,
        cancelled: &AtomicBool,
        progress: &mut impl FnMut(u32, Option<Score>),
        timeouts: Timeouts,
    ) -> io::Result<Analysis> {
        self.send(&format!("position fen {fen}"))?;
        self.send(&format!("go depth {depth}"))?;
        let mut deadline = Instant::now() + timeouts.search;
        let mut analysis = Analysis {
            best_move: None,
            updated_fen: None,
            score: None,
            depth: 0,
            stopped: false,
        };
        loop {
            if !analysis.stopped
                && (cancelled.load(Ordering::Acquire) || Instant::now() >= deadline)
            {
                self.send("stop")?;
                analysis.stopped = true;
                deadline = Instant::now() + timeouts.stop;
            }
            // Polling the receiver keeps cancellation responsive even when stdout is silent.
            let poll = deadline.min(Instant::now() + Duration::from_millis(25));
            let line = match self.receive(poll) {
                Err(error)
                    if error.kind() == io::ErrorKind::TimedOut && Instant::now() < deadline =>
                {
                    continue
                }
                Err(error) if error.kind() == io::ErrorKind::TimedOut && !analysis.stopped => {
                    continue
                }
                result => result?,
            };
            let parts: Vec<_> = line.split_whitespace().collect();
            if parts.first() == Some(&"info") {
                if let Some(d) = parts
                    .windows(2)
                    .find(|p| p[0] == "depth")
                    .and_then(|p| p[1].parse().ok())
                {
                    analysis.depth = d;
                }
                if let Some(score) = parse_score(&parts) {
                    analysis.score = Some(score);
                }
                progress(analysis.depth, analysis.score);
            }
            if parts.first() == Some(&"bestmove") {
                let value = *parts
                    .get(1)
                    .ok_or_else(|| invalid("Missing bestmove value"))?;
                if value != "(none)" && value != "0000" {
                    Move::parse(value).map_err(|e| invalid(&e))?;
                    analysis.best_move = Some(value.into());
                }
                break;
            }
        }
        if cancelled.load(Ordering::Acquire) {
            self.ready(timeouts.stop)?;
            return Err(interrupted());
        }
        if let Some(value) = &analysis.best_move {
            self.send(&format!("position fen {fen} moves {value}"))?;
            self.send("d")?;
            let deadline = Instant::now() + timeouts.handshake;
            loop {
                let line = self.receive(deadline)?;
                if let Some(fen) = line.strip_prefix("Fen:") {
                    validate_fen(fen.trim())?;
                    analysis.updated_fen = Some(fen.trim().into());
                }
                if line.starts_with("Checkers:") {
                    break;
                }
            }
            if analysis.updated_fen.is_none() {
                return Err(invalid("Engine omitted updated FEN"));
            }
        }
        self.ready(timeouts.handshake)?;
        Ok(analysis)
    }
}
impl Drop for EngineProcess {
    fn drop(&mut self) {
        let _ = self.send("quit");
        self.input.take();
        self.output.take(); // Unblock a stdout reader waiting on a full channel.
        let deadline = Instant::now() + Duration::from_millis(200);
        loop {
            match self.child.try_wait() {
                Ok(Some(_)) => break,
                _ if Instant::now() >= deadline => {
                    let _ = self.child.kill();
                    let _ = self.child.wait();
                    break;
                }
                _ => thread::sleep(Duration::from_millis(5)),
            }
        }
        for reader in self.readers.drain(..) {
            let _ = reader.join();
        }
    }
}
fn read_line(reader: &mut impl BufRead) -> io::Result<String> {
    let mut line = String::new();
    let size = reader.take(16 * 1024).read_line(&mut line)?;
    if size == 0 {
        return Err(io::Error::new(
            io::ErrorKind::UnexpectedEof,
            "Stockfish exited before its response",
        ));
    }
    if size == 16 * 1024 && !line.ends_with('\n') {
        return Err(invalid("Engine output line exceeded limit"));
    }
    Ok(line.trim().to_owned())
}
fn parse_score(parts: &[&str]) -> Option<Score> {
    let p = parts.windows(3).find(|p| p[0] == "score")?;
    match p[1] {
        "cp" => Some(Score::Centipawns(p[2].parse().ok()?)),
        "mate" => Some(Score::Mate(p[2].parse().ok()?)),
        _ => None,
    }
}
fn validate_fen(fen: &str) -> io::Result<()> {
    if fen.contains(['\n', '\r', '\0']) {
        return Err(invalid("FEN must be a single line"));
    }
    let fields: Vec<_> = fen.split_whitespace().collect();
    if fields.len() != 6 {
        return Err(invalid("Expected six FEN fields"));
    }
    let board = fen_to_list(fen).map_err(|e| invalid(&e))?;
    if board.iter().filter(|&&p| p == 'K').count() != 1
        || board.iter().filter(|&&p| p == 'k').count() != 1
    {
        return Err(invalid("Expected one king per color"));
    }
    if !matches!(fields[1], "w" | "b")
        || !(fields[2] == "-" || fields[2].chars().all(|c| "KQkq".contains(c)))
    {
        return Err(invalid("Invalid FEN side/castling fields"));
    }
    if fields[3] != "-"
        && (chesspilot_core::board::algebraic_to_index(fields[3]).is_err()
            || !matches!(fields[3].as_bytes().get(1), Some(b'3' | b'6')))
    {
        return Err(invalid("Invalid en-passant square"));
    }
    if fields[4].parse::<u32>().is_err() || fields[5].parse::<u32>().ok().is_none_or(|n| n == 0) {
        return Err(invalid("Invalid FEN counters"));
    }
    Ok(())
}
fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message.to_owned())
}
fn timeout() -> io::Error {
    io::Error::new(io::ErrorKind::TimedOut, "Stockfish response timed out")
}
fn interrupted() -> io::Error {
    io::Error::new(io::ErrorKind::Interrupted, "Analysis cancelled")
}
