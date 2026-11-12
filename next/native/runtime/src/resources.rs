//! Source: services/engine_service.py and utils/resource_path.py.
use std::{
    fs::{self, OpenOptions},
    io::{self, Read, Write},
    path::{Path, PathBuf},
};

pub const DEFAULT_CONFIG: &str = "# ChessPilot Engine Configuration\n# Restart the engine after editing.\nsetoption name Hash value 1024\nsetoption name Threads value 4\n";

pub fn native_asset_directories() -> io::Result<Vec<PathBuf>> {
    let exe = std::env::current_exe()?;
    let mut directories = vec![exe
        .parent()
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "Missing executable directory"))?
        .to_path_buf()];
    if cfg!(debug_assertions) {
        directories.push(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../.."));
        directories.push(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../src"));
    }
    if let Ok(user) = user_data_directory() {
        directories.push(user.join("native"));
    }
    Ok(directories)
}
pub fn vision_paths(model: Option<&str>, runtime: Option<&str>) -> io::Result<(PathBuf, PathBuf)> {
    let mut directories = native_asset_directories()?;
    let model = match model {
        Some(path) => PathBuf::from(path),
        None => resource_path("chess_detection.onnx", &directories).or_else(|missing| {
            let mut matches = Vec::new();
            for directory in &directories {
                let Ok(entries) = fs::read_dir(directory) else {
                    continue;
                };
                for entry in entries.flatten() {
                    let path = entry.path();
                    let name = entry.file_name().to_string_lossy().to_ascii_lowercase();
                    if path.is_file() && name.contains("chess_detection") && name.ends_with(".onnx")
                    {
                        matches.push(path);
                    }
                }
            }
            matches.sort();
            matches.dedup();
            if matches.len() == 1 {
                Ok(matches.remove(0))
            } else if matches.is_empty() {
                Err(missing)
            } else {
                Err(io::Error::other(
                    "Several detection models found; specify the model path",
                ))
            }
        })?,
    };
    if cfg!(all(debug_assertions, windows)) {
        directories.push(
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("../../../venv/Lib/site-packages/onnxruntime/capi"),
        );
    }
    let name = if cfg!(windows) {
        "onnxruntime.dll"
    } else {
        "libonnxruntime.so"
    };
    let runtime = match runtime {
        Some(path) => PathBuf::from(path),
        None => resource_path(name, &directories)?,
    };
    Ok((model, runtime))
}

/// Resolve an existing bundle/development asset without moving the user's file.
pub fn resource_path(name: &str, directories: &[PathBuf]) -> io::Result<PathBuf> {
    if Path::new(name).components().count() != 1 || name == "." || name == ".." {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "Expected a resource filename",
        ));
    }
    directories
        .iter()
        .map(|dir| dir.join(name))
        .find(|path| path.is_file())
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, format!("Missing resource: {name}")))
}

pub fn stockfish_path(directories: &[PathBuf]) -> io::Result<PathBuf> {
    let name = if cfg!(windows) {
        "stockfish.exe"
    } else {
        "stockfish"
    };
    executable_path(name, directories)
}
fn absolute_env(name: &str) -> Option<PathBuf> {
    std::env::var_os(name)
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
}
pub fn user_data_directory() -> io::Result<PathBuf> {
    if let Some(path) = absolute_env("CHESSPILOT_DATA_HOME") {
        return Ok(path);
    }
    if cfg!(target_os = "android") {
        return Err(io::Error::other(
            "Android native resources require app-private paths",
        ));
    }
    let home = absolute_env("USERPROFILE").or_else(|| absolute_env("HOME"));
    if cfg!(windows) {
        absolute_env("LOCALAPPDATA")
            .or_else(|| home.map(|p| p.join("AppData/Local")))
            .map(|p| p.join("ChessPilot"))
    } else {
        absolute_env("XDG_DATA_HOME")
            .or_else(|| home.map(|p| p.join(".local/share")))
            .map(|p| p.join("chesspilot"))
    }
    .ok_or_else(|| io::Error::other("No writable application data location"))
}
pub fn default_config_path() -> io::Result<PathBuf> {
    if let Some(path) = absolute_env("CHESSPILOT_DATA_HOME") {
        let path = path.join("engine_config.txt");
        ensure_config_exists(&path)?;
        return Ok(path);
    }
    let exe = std::env::current_exe()?;
    let portable = exe
        .parent()
        .ok_or_else(|| io::Error::other("Missing executable directory"))?;
    let existing = portable.join("engine_config.txt");
    if existing.is_file() {
        return Ok(existing);
    }
    if cfg!(debug_assertions) {
        let source = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../engine_config.txt");
        if source.is_file() {
            return Ok(source);
        }
    }
    let user = if cfg!(windows) {
        user_data_directory()?
    } else {
        absolute_env("XDG_CONFIG_HOME")
            .or_else(|| absolute_env("HOME").map(|p| p.join(".config")))
            .map(|p| p.join("ChessPilot"))
            .ok_or_else(|| io::Error::other("No configuration directory"))?
    };
    config_file_path(portable, &user)
}
pub fn load_options(path: &Path) -> io::Result<Vec<String>> {
    let mut text = String::new();
    fs::File::open(path)?
        .take(1024 * 1024 + 1)
        .read_to_string(&mut text)?;
    if text.len() > 1024 * 1024 {
        return Err(io::Error::other("Engine config exceeded 1 MiB"));
    }
    engine_options(&text)
}
pub fn executable_path(name: &str, directories: &[PathBuf]) -> io::Result<PathBuf> {
    if Path::new(name).components().count() != 1 || name == "." || name == ".." {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "Expected an executable filename",
        ));
    }
    resource_path(name, directories).or_else(|error| {
        let paths = std::env::var_os("PATH").unwrap_or_default();
        std::env::split_paths(&paths)
            .map(|p| p.join(name))
            .find(|p| p.is_file())
            .ok_or(error)
    })
}

/// Prefer the existing portable config; otherwise create in a writable app directory.
pub fn config_file_path(portable: &Path, user_data: &Path) -> io::Result<PathBuf> {
    let portable = portable.join("engine_config.txt");
    if portable.is_file() {
        return Ok(portable);
    }
    ensure_config_exists(&portable)
        .map(|_| portable)
        .or_else(|_| {
            let path = user_data.join("engine_config.txt");
            ensure_config_exists(&path)?;
            Ok(path)
        })
}

pub fn ensure_config_exists(path: &Path) -> io::Result<bool> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    match OpenOptions::new().write(true).create_new(true).open(path) {
        Ok(mut file) => {
            file.write_all(DEFAULT_CONFIG.as_bytes())?;
            file.sync_all()?;
            Ok(true)
        }
        Err(error) if error.kind() == io::ErrorKind::AlreadyExists => Ok(false),
        Err(error) => Err(error),
    }
}

/// A config file contains options, never arbitrary UCI commands.
pub fn engine_options(text: &str) -> io::Result<Vec<String>> {
    let mut options = Vec::new();
    for line in text
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
    {
        if !line.starts_with("setoption name ")
            || line.len() > 4096
            || line.contains(['\0', '\r'])
            || options.len() >= 128
        {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "Invalid engine option in config",
            ));
        }
        options.push(line.into());
    }
    Ok(options)
}
