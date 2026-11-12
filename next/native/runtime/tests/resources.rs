use chesspilot_runtime::resources::*;
use std::{
    fs,
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};

struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "chesspilot-resources-{}-{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }
}
impl Drop for Temp {
    fn drop(&mut self) {
        assert!(self
            .0
            .canonicalize()
            .unwrap()
            .starts_with(std::env::temp_dir().canonicalize().unwrap()));
        fs::remove_dir_all(&self.0).unwrap();
    }
}

#[test]
fn defaults_and_portable_config_preserve_user_content() {
    let temp = Temp::new();
    let portable = temp.0.join("portable");
    let user = temp.0.join("user");
    let path = config_file_path(&portable, &user).unwrap();
    assert_eq!(path, portable.join("engine_config.txt"));
    assert_eq!(
        engine_options(&fs::read_to_string(&path).unwrap()).unwrap(),
        [
            "setoption name Hash value 1024",
            "setoption name Threads value 4"
        ]
    );
    fs::write(&path, "# user\nsetoption name Hash value 32\n").unwrap();
    assert!(!ensure_config_exists(&path).unwrap());
    assert!(fs::read_to_string(&path).unwrap().contains("value 32"));
    let blocked = temp.0.join("file");
    fs::write(&blocked, "not a directory").unwrap();
    assert_eq!(
        config_file_path(&blocked, &user).unwrap(),
        user.join("engine_config.txt")
    );
}
#[test]
fn local_resources_options_and_missing_assets() {
    let temp = Temp::new();
    fs::write(temp.0.join("chess_detection.onnx"), b"fixture").unwrap();
    assert_eq!(
        resource_path("chess_detection.onnx", std::slice::from_ref(&temp.0)).unwrap(),
        temp.0.join("chess_detection.onnx")
    );
    assert!(resource_path("../chess_detection.onnx", std::slice::from_ref(&temp.0)).is_err());
    assert!(resource_path("missing", std::slice::from_ref(&temp.0)).is_err());
    assert_eq!(
        engine_options("\n # comment\nsetoption name Threads value 2\n")
            .unwrap()
            .len(),
        1
    );
    assert!(engine_options("quit").is_err());
    assert!(engine_options("setoption name Hash value 16\rquit").is_err());
}
