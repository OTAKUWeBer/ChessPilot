//! Port of downloader.py: CPU selection, progress, cancellation and offline-safe installation.
use crate::{
    cpu::{self, CpuInfo},
    desktop::helper,
    engine::{EngineService, Timeouts},
    resources,
};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    process::Command,
    sync::atomic::{AtomicBool, AtomicU64, Ordering},
    time::{Duration, Instant},
};
pub const MAX_ARCHIVE: u64 = 256 * 1024 * 1024;
pub const MAX_BINARY: usize = 192 * 1024 * 1024;
const API: &str = "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest";
static NEXT: AtomicU64 = AtomicU64::new(0);
#[derive(Debug, Clone)]
pub struct Asset {
    pub name: String,
    pub url: String,
    pub size: u64,
    pub digest: Option<String>,
}
#[derive(Debug)]
pub struct Release {
    pub tag: String,
    pub assets: Vec<Asset>,
}
pub fn parse_release(bytes: &[u8]) -> Result<Release, String> {
    if bytes.len() > 2 * 1024 * 1024 {
        return Err("Stockfish metadata exceeded limit".into());
    }
    let data: Value = serde_json::from_slice(bytes).map_err(|e| e.to_string())?;
    let tag = data["tag_name"]
        .as_str()
        .filter(|s| {
            !s.is_empty()
                && s.len() < 128
                && s.bytes()
                    .all(|c| c.is_ascii_alphanumeric() || b"_.-".contains(&c))
        })
        .ok_or("Invalid Stockfish release tag")?;
    let entries = data["assets"]
        .as_array()
        .filter(|a| a.len() <= 512)
        .ok_or("Invalid Stockfish asset list")?;
    let mut assets = Vec::new();
    for entry in entries {
        let name = entry["name"].as_str().ok_or("Missing asset filename")?;
        if name.len() > 160
            || !name
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"_.-".contains(&c))
        {
            return Err("Invalid Stockfish asset filename".into());
        }
        if ![".zip", ".tar", ".tar.gz", ".tgz"]
            .iter()
            .any(|e| name.ends_with(e))
        {
            continue;
        }
        let size = entry["size"]
            .as_u64()
            .filter(|&n| n > 0 && n <= MAX_ARCHIVE)
            .ok_or("Invalid Stockfish archive size")?;
        let url = entry["browser_download_url"]
            .as_str()
            .filter(|url| {
                url.starts_with(
                    "https://github.com/official-stockfish/Stockfish/releases/download/",
                ) && !url.chars().any(char::is_control)
            })
            .ok_or("Unexpected Stockfish download origin")?;
        let digest = match entry["digest"].as_str() {
            Some(value) => Some(
                value
                    .strip_prefix("sha256:")
                    .filter(|s| s.len() == 64 && s.bytes().all(|c| c.is_ascii_hexdigit()))
                    .ok_or("Invalid Stockfish digest")?
                    .to_ascii_lowercase(),
            ),
            None => None,
        };
        assets.push(Asset {
            name: name.into(),
            url: url.into(),
            size,
            digest,
        });
    }
    Ok(Release {
        tag: tag.into(),
        assets,
    })
}
fn compatible(name: &str, os: &str, cpu: &CpuInfo) -> bool {
    let platform = match os {
        "windows" => {
            name.starts_with("stockfish-windows-") || name.starts_with("stockfish_windows_")
        }
        "linux" => name.starts_with("stockfish-linux-") || name.starts_with("stockfish-ubuntu-"),
        "android" => name.starts_with("stockfish-android-"),
        _ => false,
    };
    if !platform {
        return false;
    }
    let has = |s: &str| cpu.features.contains(s);
    match cpu.architecture.as_str() {
        "x86_64" | "amd64" => {
            if !(name.contains("x86-64") || name.contains("x86_64")) || name.contains("arm") {
                return false;
            }
            let stem = [".tar.gz", ".tgz", ".zip", ".tar"]
                .iter()
                .find_map(|suffix| name.strip_suffix(suffix))
                .unwrap_or(name);
            let suffix = stem
                .split_once("x86-64")
                .or_else(|| stem.split_once("x86_64"))
                .map(|(_, s)| s.trim_start_matches(['-', '_']))
                .unwrap_or("");
            let suffix = suffix
                .strip_suffix("-amd")
                .or_else(|| suffix.strip_suffix("-intel"))
                .unwrap_or(suffix);
            if ![
                "",
                "avx2",
                "bmi2",
                "avx512",
                "sse41-popcnt",
                "modern",
                "vnni256",
                "vnni512",
                "avxvnni",
                "universal",
            ]
            .contains(&suffix)
            {
                return false;
            }
            if (name.contains("vnni256") || name.contains("vnni512"))
                && ![
                    "avx512vnni",
                    "avx512f",
                    "avx512bw",
                    "avx512dq",
                    "avx512vl",
                    "bmi2",
                    "avx2",
                    "sse4_1",
                    "popcnt",
                ]
                .iter()
                .all(|f| has(f))
            {
                return false;
            }
            if name.contains("avxvnni")
                && !["avxvnni", "bmi2", "avx2", "sse4_1", "popcnt"]
                    .iter()
                    .all(|f| has(f))
            {
                return false;
            }
            if name.contains("avx512")
                && ![
                    "avx512f", "avx512bw", "avx512dq", "avx512vl", "bmi2", "avx2", "sse4_1",
                    "popcnt",
                ]
                .iter()
                .all(|f| has(f))
            {
                return false;
            }
            if name.contains("bmi2") && !["bmi2", "avx2", "sse4_1", "popcnt"].iter().all(|f| has(f))
            {
                return false;
            }
            if name.contains("avx2") && !["avx2", "sse4_1", "popcnt"].iter().all(|f| has(f)) {
                return false;
            }
            if ["sse41", "sse4", "modern"].iter().any(|f| name.contains(f)) && !has("sse4_1") {
                return false;
            }
            if (name.contains("popcnt") || name.contains("modern")) && !has("popcnt") {
                return false;
            }
            true
        }
        "aarch64" | "arm64" => {
            has("neon")
                && (name.contains("armv8") || name.contains("arm64") || name.contains("aarch64"))
                && (!name.contains("dotprod") || has("dotprod"))
        }
        _ => false,
    }
}
fn score(name: &str, cpu: &CpuInfo) -> i32 {
    let has = |s: &str| cpu.features.contains(s);
    let instruction = if name.contains("universal") {
        // Official universal builds select their supported instruction set at startup.
        140
    } else if name.contains("vnni512") {
        130
    } else if name.contains("vnni256") {
        120
    } else if name.contains("avxvnni") {
        110
    } else if name.contains("avx512") {
        100
    } else if name.contains("bmi2") {
        80
    } else if name.contains("avx2") {
        60
    } else if ["popcnt", "sse41", "sse4"].iter().any(|s| name.contains(s)) {
        50
    } else if name.contains("dotprod") {
        60
    } else {
        0
    };
    let fallback = if name.contains("modern") {
        40
    } else if name.contains("x86-64") || name.contains("x86_64") {
        35
    } else {
        0
    };
    let bonus = if name.contains("bmi2")
        && has("bmi2")
        && ["amd", "intel"].contains(&cpu.vendor.as_str())
        && name.contains(&cpu.vendor)
    {
        10
    } else {
        0
    };
    let penalty = if (name.contains("amd")
        && !["amd", "generic", "unknown"].contains(&cpu.vendor.as_str()))
        || (name.contains("intel")
            && !["intel", "generic", "unknown"].contains(&cpu.vendor.as_str()))
    {
        -5
    } else {
        0
    };
    instruction + fallback + bonus + penalty + 5
}
pub fn choose_asset<'a>(assets: &'a [Asset], os: &str, cpu: &CpuInfo) -> Option<&'a Asset> {
    // Strictly preserve the first highest-scored compatible asset, as in Python.
    let mut best = None;
    let mut best_score = i32::MIN;
    for asset in assets {
        let name = asset.name.to_ascii_lowercase();
        if compatible(&name, os, cpu) {
            let score = score(&name, cpu);
            if score > best_score {
                best_score = score;
                best = Some(asset);
            }
        }
    }
    best
}
pub fn tool(name: &str) -> Result<PathBuf, String> {
    #[cfg(windows)]
    {
        let root = std::env::var_os("SystemRoot").ok_or("SystemRoot is missing")?;
        let path = PathBuf::from(root)
            .join("System32")
            .join(format!("{name}.exe"));
        if path.is_file() {
            Ok(path)
        } else {
            Err(format!(
                "Windows {name} helper is missing; use offline setup"
            ))
        }
    }
    #[cfg(not(windows))]
    {
        resources::executable_path(name, &[])
            .map_err(|e| format!("Install {name} or use offline setup: {e}"))
    }
}
fn curl(url: &str) -> Result<Command, String> {
    let mut command = Command::new(tool("curl")?);
    command.args([
        "-q",
        "--fail",
        "--silent",
        "--show-error",
        "--location",
        "--proto",
        "=https",
        "--proto-redir",
        "=https",
        "--max-redirs",
        "5",
        "--connect-timeout",
        "10",
        "--max-time",
        "600",
        "--speed-limit",
        "1",
        "--speed-time",
        "30",
        "--user-agent",
        "ChessPilot-native/0.1",
        "--url",
        url,
    ]);
    Ok(command)
}
fn check_cancel(cancelled: &AtomicBool) -> Result<(), String> {
    if cancelled.load(Ordering::Acquire) {
        Err("Stockfish setup cancelled".into())
    } else {
        Ok(())
    }
}
pub fn verify_archive(
    path: &Path,
    asset: &Asset,
    cancelled: &AtomicBool,
) -> Result<String, String> {
    let mut file = File::open(path).map_err(|e| e.to_string())?;
    if file.metadata().map_err(|e| e.to_string())?.len() != asset.size {
        return Err("Stockfish download size mismatch".into());
    }
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        check_cancel(cancelled)?;
        let n = file.read(&mut buffer).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    let digest = format!("{:x}", hash.finalize());
    if asset
        .digest
        .as_ref()
        .is_some_and(|expected| !expected.eq_ignore_ascii_case(&digest))
    {
        return Err("Stockfish archive SHA-256 mismatch".into());
    }
    Ok(digest)
}
pub fn select_member(list: &str, asset: &Asset, os: &str) -> Result<String, String> {
    let stem = [".tar.gz", ".tgz", ".zip", ".tar"]
        .iter()
        .find_map(|suffix| asset.name.strip_suffix(suffix))
        .ok_or("Unsupported engine archive")?;
    let expected = if os == "windows" {
        format!("{stem}.exe")
    } else {
        stem.into()
    };
    let generic = if os == "windows" {
        "stockfish.exe"
    } else {
        "stockfish"
    };
    let mut found = None;
    for name in list.lines() {
        if name.len() > 1024
            || name.chars().any(char::is_control)
            || name.contains(['\\', ':'])
            || name.starts_with('/')
            || name.split('/').any(|s| s == "..")
        {
            return Err("Unsafe archive member name".into());
        }
        let base = name.rsplit('/').next().unwrap_or("");
        if base.eq_ignore_ascii_case(&expected) || base.eq_ignore_ascii_case(generic) {
            if found.is_some() {
                return Err("Ambiguous Stockfish executables in archive".into());
            }
            found = Some(name.to_owned());
        }
    }
    found.ok_or_else(|| "Stockfish executable was not found in archive".into())
}
pub fn validate_binary(bytes: &[u8], os: &str, arch: &str) -> Result<(), String> {
    let arm = match arch {
        "aarch64" | "arm64" => true,
        "x86_64" | "amd64" => false,
        _ => return Err("Unsupported engine architecture".into()),
    };
    if os == "windows" {
        if bytes.get(..2) != Some(b"MZ") {
            return Err("Downloaded engine is not a Windows executable".into());
        }
        let offset = bytes
            .get(60..64)
            .map(|b| u32::from_le_bytes(b.try_into().unwrap()) as usize)
            .filter(|&n| n <= 1024 * 1024)
            .ok_or("Invalid PE header")?;
        if bytes.get(offset..offset + 4) != Some(b"PE\0\0") {
            return Err("Invalid Windows executable header".into());
        }
        let machine = bytes
            .get(offset + 4..offset + 6)
            .map(|b| u16::from_le_bytes(b.try_into().unwrap()));
        if machine != Some(if arm { 0xaa64 } else { 0x8664 }) {
            return Err("Windows engine architecture mismatch".into());
        }
    } else {
        if bytes.get(..6) != Some(b"\x7fELF\x02\x01") {
            return Err("Downloaded engine is not a 64-bit little-endian ELF".into());
        }
        let machine = bytes
            .get(18..20)
            .map(|b| u16::from_le_bytes(b.try_into().unwrap()));
        if machine != Some(if arm { 183 } else { 62 }) {
            return Err("Linux engine architecture mismatch".into());
        }
    }
    Ok(())
}
struct Stage(PathBuf);
impl Stage {
    fn new(parent: &Path) -> Result<Self, String> {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        let parent = parent.canonicalize().map_err(|e| e.to_string())?;
        for _ in 0..16 {
            let path = parent.join(format!(
                ".install-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            match fs::create_dir(&path) {
                Ok(()) => return Ok(Self(path)),
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {}
                Err(e) => return Err(e.to_string()),
            }
        }
        Err("Could not allocate engine setup directory".into())
    }
}
impl Drop for Stage {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
pub fn ensure_stockfish(
    cancelled: &AtomicBool,
    progress: impl FnMut(Value),
) -> Result<PathBuf, String> {
    if cfg!(target_os = "android") {
        return Err("Android uses its APK-packaged Stockfish executable".into());
    }
    check_cancel(cancelled)?;
    let dirs = resources::native_asset_directories().map_err(|e| e.to_string())?;
    if let Ok(existing) = resources::stockfish_path(&dirs) {
        return Ok(existing);
    }
    let parent = resources::user_data_directory()
        .map_err(|e| e.to_string())?
        .join("native");
    install_stockfish(&parent, cancelled, progress)
}
pub fn install_stockfish(
    parent: &Path,
    cancelled: &AtomicBool,
    mut progress: impl FnMut(Value),
) -> Result<PathBuf, String> {
    if cfg!(target_os = "android") {
        return Err("Android uses APK-packaged native engines".into());
    }
    check_cancel(cancelled)?;
    progress(json!({"stage":"Fetching Stockfish release metadata","downloaded":0}));
    let metadata = helper::run(
        curl(API)?,
        Duration::from_secs(40),
        2 * 1024 * 1024,
        cancelled,
        || Ok(()),
    )?;
    let release = parse_release(&metadata)?;
    let cpu = cpu::detect();
    let os = std::env::consts::OS;
    let asset = choose_asset(&release.assets, os, &cpu)
        .ok_or("No compatible Stockfish build for this OS/CPU; use offline setup")?;
    log::info!(target:"setup","Selected {} from {} for {} {}",asset.name,release.tag,cpu.vendor,cpu.architecture);
    let stage = Stage::new(parent)?;
    let cache = parent.join("download-cache");
    let cached = cached_archive(&cache, asset, cancelled);
    let archive = cached.clone().unwrap_or_else(|| stage.0.join(&asset.name));
    if cached.is_none() {
        let mut command = curl(&asset.url)?;
        command
            .arg("--max-filesize")
            .arg(MAX_ARCHIVE.to_string())
            .arg("--output")
            .arg(&archive);
        let started = Instant::now();
        let mut last = Instant::now() - Duration::from_secs(1);
        helper::run(
            command,
            Duration::from_secs(610),
            64 * 1024,
            cancelled,
            || {
                let size = match fs::metadata(&archive) {
                    Ok(m) => m.len(),
                    Err(e) if e.kind() == std::io::ErrorKind::NotFound => 0,
                    Err(e) => return Err(e.to_string()),
                };
                if size > MAX_ARCHIVE || size > asset.size {
                    return Err("Stockfish download exceeded expected size".into());
                }
                if last.elapsed() >= Duration::from_millis(100) {
                    progress(
                        json!({"stage":"Downloading Stockfish","asset":asset.name,"release":release.tag,"cpu":cpu.brand,"downloaded":size,"total":asset.size,"bytes_per_second":size as f64/started.elapsed().as_secs_f64().max(0.001)}),
                    );
                    last = Instant::now();
                }
                Ok(())
            },
        )?;
    } else {
        progress(
            json!({"stage":"Using verified cached download","downloaded":asset.size,"total":asset.size}),
        );
    }
    progress(
        json!({"stage":"Checking download and extracting Stockfish","downloaded":asset.size,"total":asset.size}),
    );
    let digest = verify_archive(&archive, asset, cancelled)?;
    if cached.is_none() {
        cache_archive(&cache, &archive, asset, &digest);
    }
    let tar = tool("tar")?;
    let mut list = Command::new(&tar);
    list.arg("-tf").arg(&archive);
    let names = helper::run(
        list,
        Duration::from_secs(30),
        1024 * 1024,
        cancelled,
        || Ok(()),
    )?;
    let member = select_member(
        std::str::from_utf8(&names).map_err(|_| "Non-UTF8 archive listing")?,
        asset,
        os,
    )?;
    let mut extract = Command::new(&tar);
    extract.arg("-xOf").arg(&archive).arg("--").arg(&member);
    let bytes = helper::run(
        extract,
        Duration::from_secs(60),
        MAX_BINARY,
        cancelled,
        || Ok(()),
    )?;
    validate_binary(&bytes, os, &cpu.architecture)?;
    let filename = if os == "windows" {
        "stockfish.exe"
    } else {
        "stockfish"
    };
    let staged = stage.0.join(filename);
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&staged)
        .map_err(|e| e.to_string())?;
    file.write_all(&bytes)
        .and_then(|_| file.sync_all())
        .map_err(|e| e.to_string())?;
    drop(file);
    drop(bytes);
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(&staged, fs::Permissions::from_mode(0o700))
            .map_err(|e| e.to_string())?;
    }
    check_cancel(cancelled)?;
    progress(
        json!({"stage":"Verifying Stockfish UCI startup","downloaded":asset.size,"total":asset.size}),
    );
    let mut engine = EngineService::new(
        Command::new(&staged),
        vec![
            "setoption name Hash value 16".into(),
            "setoption name Threads value 1".into(),
        ],
        Timeouts {
            handshake: Duration::from_secs(5),
            ..Timeouts::default()
        },
    )
    .map_err(|e| e.to_string())?;
    engine
        .initialize()
        .map_err(|e| format!("Downloaded engine failed its UCI check: {e}"))?;
    drop(engine);
    check_cancel(cancelled)?;
    let target = parent.join(filename);
    // Same-volume hard linking publishes a complete file atomically without replacing another install.
    match fs::hard_link(&staged, &target) {
        Ok(()) => {}
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => return Ok(target),
        Err(e) => {
            return Err(format!(
            "Could not publish engine without overwriting existing files: {e}. Use offline setup."
        ))
        }
    }
    let source = parent.join(format!("stockfish-source-{}.txt", &digest[..12]));
    if let Ok(mut file) = OpenOptions::new().write(true).create_new(true).open(source) {
        let _=writeln!(file,"Stockfish {}; GPL-3.0-or-later\nSource: https://github.com/official-stockfish/Stockfish/tree/{}\nArchive: {}\nSHA256: {}\nLicense: https://github.com/official-stockfish/Stockfish/blob/{}/Copying.txt",release.tag,release.tag,asset.url,digest,release.tag);
    }
    progress(json!({"stage":"Stockfish installed","downloaded":asset.size,"total":asset.size}));
    Ok(target)
}
fn cached_archive(cache: &Path, asset: &Asset, cancelled: &AtomicBool) -> Option<PathBuf> {
    let manifest = cache.join("stockfish.json");
    if fs::metadata(&manifest).ok()?.len() > 4096 {
        return None;
    }
    let data: Value = serde_json::from_slice(&fs::read(manifest).ok()?).ok()?;
    if data["url"].as_str() != Some(&asset.url) {
        return None;
    }
    let checksum = data["sha256"]
        .as_str()
        .filter(|s| s.len() == 64 && s.bytes().all(|c| c.is_ascii_hexdigit()))?;
    let mut expected = asset.clone();
    expected.digest = Some(asset.digest.clone().unwrap_or_else(|| checksum.into()));
    let path = cache.join("stockfish.archive");
    verify_archive(&path, &expected, cancelled).ok()?;
    Some(path)
}
fn cache_archive(cache: &Path, archive: &Path, asset: &Asset, digest: &str) {
    // Cache failures never prevent a valid engine installation.
    let result = (|| -> std::io::Result<()> {
        fs::create_dir_all(cache)?;
        let destination = cache.join("stockfish.archive");
        let manifest = cache.join("stockfish.json");
        for path in [&destination, &manifest] {
            match fs::remove_file(path) {
                Ok(()) => {}
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
                Err(e) => return Err(e),
            }
        }
        fs::hard_link(archive, destination)?;
        fs::write(
            manifest,
            json!({"url":asset.url,"sha256":digest}).to_string(),
        )?;
        Ok(())
    })();
    if let Err(error) = result {
        log::warn!(target:"setup","Download cache not retained: {error}");
    }
}
