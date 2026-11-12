//! Source: services/engine_service.py and utils/resource_path.py.
use std::{
    fs::{self, OpenOptions},
    io::{self, Write},
    path::{Path, PathBuf},
};

pub const DEFAULT_CONFIG: &str = "# ChessPilot Engine Configuration\n# Restart the engine after editing.\nsetoption name Hash value 1024\nsetoption name Threads value 4\n";

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
