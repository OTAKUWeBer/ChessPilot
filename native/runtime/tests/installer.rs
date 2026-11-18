use chesspilot_runtime::{cpu::CpuInfo, desktop::helper, installer::*};
use serde_json::{json, Value};
use std::{
    collections::BTreeSet,
    fs,
    path::PathBuf,
    process::Command,
    sync::atomic::{AtomicBool, AtomicU64, Ordering},
    time::Duration,
};
static NEXT: AtomicU64 = AtomicU64::new(0);
struct Temp(PathBuf);
impl Temp {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "chesspilot-install-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
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
fn cpu(arch: &str, flags: &[&str]) -> CpuInfo {
    CpuInfo {
        architecture: arch.into(),
        vendor: "intel".into(),
        brand: "Fixture".into(),
        features: flags.iter().map(|s| (*s).into()).collect(),
        cores: 4,
    }
}
fn asset(name: &str) -> Asset {
    Asset {
        name: name.into(),
        url: format!(
            "https://github.com/official-stockfish/Stockfish/releases/download/sf_fixture/{name}"
        ),
        size: 3,
        digest: None,
    }
}
#[test]
fn compatible_pc_choices_match_reference_scoring() {
    let fixture: Value = serde_json::from_str(include_str!("fixtures/downloads.json")).unwrap();
    let assets: Vec<_> = fixture["assets"]
        .as_array()
        .unwrap()
        .iter()
        .map(|a| asset(a["name"].as_str().unwrap()))
        .collect();
    for case in fixture["cases"].as_array().unwrap() {
        let info = CpuInfo {
            architecture: case["arch"].as_str().unwrap().into(),
            vendor: case["vendor"].as_str().unwrap().into(),
            brand: "fixture".into(),
            features: case["flags"]
                .as_array()
                .unwrap()
                .iter()
                .map(|f| f.as_str().unwrap().into())
                .collect::<BTreeSet<_>>(),
            cores: 4,
        };
        assert_eq!(
            choose_asset(&assets, case["os"].as_str().unwrap(), &info).map(|a| a.name.as_str()),
            case.get("native_expected")
                .unwrap_or(&case["expected"])
                .as_str()
        );
    }
}
#[test]
fn selector_rejects_wrong_architecture_and_unavailable_instructions() {
    let assets = [
        asset("stockfish-windows-x86-64-avx2.zip"),
        asset("stockfish-windows-x86-64.zip"),
        asset("stockfish-ubuntu-armv8.tar"),
        asset("stockfish-android-armv8-dotprod.tar"),
        asset("stockfish-android-armv8.tar"),
    ];
    assert_eq!(
        choose_asset(&assets, "windows", &cpu("x86_64", &["avx"]))
            .unwrap()
            .name,
        "stockfish-windows-x86-64.zip"
    );
    assert!(choose_asset(&assets, "windows", &cpu("aarch64", &[])).is_none());
    assert_eq!(
        choose_asset(&assets, "linux", &cpu("aarch64", &["neon"]))
            .unwrap()
            .name,
        "stockfish-ubuntu-armv8.tar"
    );
    assert_eq!(
        choose_asset(&assets, "android", &cpu("aarch64", &["neon"]))
            .unwrap()
            .name,
        "stockfish-android-armv8.tar"
    );
    assert_eq!(
        choose_asset(&assets, "android", &cpu("aarch64", &["neon", "dotprod"]))
            .unwrap()
            .name,
        "stockfish-android-armv8-dotprod.tar"
    );
    assert!(choose_asset(&assets, "linux", &cpu("riscv64", &[])).is_none());
}
#[test]
fn vnni_selection_requires_the_entire_cpu_feature_set() {
    let assets = [
        asset("stockfish-windows-x86-64-vnni512.zip"),
        asset("stockfish-windows-x86-64-vnni256.zip"),
        asset("stockfish-windows-x86-64-avx10.zip"),
        asset("stockfish-windows-x86-64.zip"),
    ];
    let mut info = cpu("x86_64", &["avx512vnni"]);
    assert_eq!(
        choose_asset(&assets, "windows", &info).unwrap().name,
        "stockfish-windows-x86-64.zip"
    );
    info.features = [
        "avx512vnni",
        "avx512f",
        "avx512bw",
        "avx512dq",
        "avx512vl",
        "avx2",
        "bmi2",
        "sse4_1",
        "popcnt",
    ]
    .iter()
    .map(|s| (*s).into())
    .collect();
    assert_eq!(
        choose_asset(&assets, "windows", &info).unwrap().name,
        "stockfish-windows-x86-64-vnni512.zip"
    );
}
#[test]
fn universal_releases_keep_architecture_checks_and_use_runtime_cpu_dispatch() {
    let assets = [
        asset("stockfish-windows-arm64-universal.zip"),
        asset("stockfish-windows-x86-64-universal.zip"),
        asset("stockfish-linux-x86-64-universal.tar.gz"),
    ];
    assert_eq!(
        choose_asset(&assets, "windows", &cpu("x86_64", &[]))
            .unwrap()
            .name,
        "stockfish-windows-x86-64-universal.zip"
    );
    assert_eq!(
        choose_asset(&assets, "windows", &cpu("aarch64", &["neon"]))
            .unwrap()
            .name,
        "stockfish-windows-arm64-universal.zip"
    );
    assert_eq!(
        select_member(
            "stockfish/stockfish-windows-x86-64-universal.exe\n",
            &assets[1],
            "windows"
        )
        .unwrap(),
        "stockfish/stockfish-windows-x86-64-universal.exe"
    );
}
#[test]
fn metadata_and_digest_validation_precede_archive_use() {
    let entry = json!({"name":"stockfish-windows-x86-64.zip","browser_download_url":"https://github.com/official-stockfish/Stockfish/releases/download/sf_19/file.zip","size":3,"digest":"sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"});
    let valid = json!({"tag_name":"sf_19","assets":[entry.clone()]});
    let release = parse_release(valid.to_string().as_bytes()).unwrap();
    let temp = Temp::new();
    let path = temp.0.join("archive");
    fs::write(&path, b"abc").unwrap();
    assert_eq!(
        verify_archive(&path, &release.assets[0], &AtomicBool::new(false)).unwrap(),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
    fs::write(&path, b"abd").unwrap();
    assert!(verify_archive(&path, &release.assets[0], &AtomicBool::new(false)).is_err());
    for (key, value) in [
        ("name", json!("../stockfish.zip")),
        ("size", json!(MAX_ARCHIVE + 1)),
        ("digest", json!("sha256:bad")),
        (
            "browser_download_url",
            json!("https://example.com/engine.zip"),
        ),
    ] {
        let mut bad = valid.clone();
        bad["assets"][0][key] = value;
        assert!(parse_release(bad.to_string().as_bytes()).is_err());
    }
    assert!(verify_archive(&path, &release.assets[0], &AtomicBool::new(true)).is_err());
}
#[test]
fn archive_selection_skips_readmes_and_rejects_ambiguous_or_unsafe_members() {
    let a = asset("stockfish-windows-x86-64.zip");
    assert_eq!(
        select_member(
            "stockfish/README.md\nstockfish/Copying.txt\nstockfish/stockfish-windows-x86-64.exe\n",
            &a,
            "windows"
        )
        .unwrap(),
        "stockfish/stockfish-windows-x86-64.exe"
    );
    for list in [
        "../stockfish.exe\n",
        "/stockfish.exe\n",
        "C:/stockfish.exe\n",
        "x\\stockfish.exe\n",
        "a/stockfish.exe\nb/stockfish.exe\n",
        "stockfish/README.md\n",
    ] {
        assert!(select_member(list, &a, "windows").is_err());
    }
    let mut pe = vec![0; 256];
    pe[..2].copy_from_slice(b"MZ");
    pe[60..64].copy_from_slice(&128u32.to_le_bytes());
    pe[128..132].copy_from_slice(b"PE\0\0");
    pe[132..134].copy_from_slice(&0x8664u16.to_le_bytes());
    validate_binary(&pe, "windows", "x86_64").unwrap();
    assert!(validate_binary(&pe, "windows", "aarch64").is_err());
    assert!(validate_binary(b"readme", "windows", "x86_64").is_err());
    let mut elf = vec![0; 64];
    elf[..6].copy_from_slice(b"\x7fELF\x02\x01");
    elf[18..20].copy_from_slice(&183u16.to_le_bytes());
    validate_binary(&elf, "linux", "aarch64").unwrap();
    assert!(validate_binary(&elf, "linux", "x86_64").is_err());
}
#[test]
fn system_tar_reads_only_the_named_member_without_unpacking_paths() {
    let temp = Temp::new();
    fs::write(temp.0.join("stockfish.exe"), b"fixture binary").unwrap();
    fs::write(temp.0.join("README.md"), b"Stockfish instructions").unwrap();
    let tar = tool("tar").unwrap();
    let archive = temp.0.join("fixture.tar");
    assert!(Command::new(&tar)
        .arg("-cf")
        .arg(&archive)
        .arg("-C")
        .arg(&temp.0)
        .args(["README.md", "stockfish.exe"])
        .status()
        .unwrap()
        .success());
    let flag = AtomicBool::new(false);
    let mut list = Command::new(&tar);
    list.arg("-tf").arg(&archive);
    let bytes = helper::run(list, Duration::from_secs(3), 4096, &flag, || Ok(())).unwrap();
    let name = select_member(
        std::str::from_utf8(&bytes).unwrap(),
        &asset("stockfish-windows-x86-64.tar"),
        "windows",
    )
    .unwrap();
    let mut extract = Command::new(&tar);
    extract.arg("-xOf").arg(&archive).arg("--").arg(name);
    assert_eq!(
        helper::run(extract, Duration::from_secs(3), 100, &flag, || Ok(())).unwrap(),
        b"fixture binary"
    );
}
#[test]
#[ignore = "Requires CHESSPILOT_DOWNLOAD_TEST=1; downloads an official CPU-selected engine into an isolated temporary directory"]
fn real_https_download_and_cpu_install_pass_uci() {
    assert_eq!(
        std::env::var("CHESSPILOT_DOWNLOAD_TEST").as_deref(),
        Ok("1")
    );
    let temp = Temp::new();
    let mut stages = Vec::new();
    let target = install_stockfish(&temp.0, &AtomicBool::new(false), |p| stages.push(p)).unwrap();
    assert!(target.is_file());
    assert!(stages.iter().any(|p| p["stage"] == "Stockfish installed"));
    fs::remove_file(&target).unwrap();
    stages.clear();
    install_stockfish(&temp.0, &AtomicBool::new(false), |p| stages.push(p)).unwrap();
    assert!(stages
        .iter()
        .any(|p| p["stage"] == "Using verified cached download"));
}

#[test]
#[cfg(target_os = "linux")]
fn portable_startup_reuses_stockfish_outside_the_extracted_bundle() {
    if std::env::var_os("CHESSPILOT_PORTABLE_TEST_CHILD").is_some() {
        let directory = PathBuf::from(std::env::var_os("CHESSPILOT_ENGINE_HOME").unwrap());
        let mut progress = Vec::new();
        let engine = ensure_stockfish(&AtomicBool::new(false), |p| progress.push(p)).unwrap();
        assert_eq!(engine, directory.join("stockfish"));
        assert_eq!(progress[0]["stage"], "Checking Stockfish in app data");
        assert_eq!(progress.len(), 1);
        return;
    }
    let temp = Temp::new();
    let profile = temp.0.join("profile with spaces");
    fs::create_dir(&profile).unwrap();
    fs::write(profile.join("stockfish"), b"existing engine fixture").unwrap();
    let status = Command::new(std::env::current_exe().unwrap())
        .args([
            "--exact",
            "portable_startup_reuses_stockfish_outside_the_extracted_bundle",
        ])
        .env("CHESSPILOT_PORTABLE_TEST_CHILD", "1")
        .env("CHESSPILOT_ENGINE_HOME", &profile)
        .status()
        .unwrap();
    assert!(status.success());
    assert_eq!(
        fs::read(profile.join("stockfish")).unwrap(),
        b"existing engine fixture"
    );
}

#[test]
fn an_unwritable_app_destination_fails_before_contacting_the_release_server() {
    let temp = Temp::new();
    let blocked = temp.0.join("blocked");
    fs::write(&blocked, b"existing file").unwrap();
    let mut progress = Vec::new();
    let error =
        install_stockfish(&blocked, &AtomicBool::new(false), |p| progress.push(p)).unwrap_err();
    assert!(progress.is_empty());
    assert!(error.contains("writable folder"));
    assert_eq!(fs::read(&blocked).unwrap(), b"existing file");
}

#[test]
#[ignore = "Requires CHESSPILOT_DOWNLOAD_TEST=1; relocates this test executable and downloads an official engine beside it"]
fn default_startup_installs_in_the_app_folder_and_reuses_it_on_the_next_launch_check() {
    assert_eq!(
        std::env::var("CHESSPILOT_DOWNLOAD_TEST").as_deref(),
        Ok("1")
    );
    if std::env::var("CHESSPILOT_INSTALL_CHILD").as_deref() == Ok("1") {
        let exe = std::env::current_exe().unwrap();
        let folder = exe.parent().unwrap();
        let mut progress = Vec::new();
        let engine = ensure_stockfish(&AtomicBool::new(false), |p| progress.push(p)).unwrap();
        assert_eq!(engine.parent(), Some(folder));
        assert_eq!(
            engine.file_name().unwrap(),
            if cfg!(windows) {
                "stockfish.exe"
            } else {
                "stockfish"
            }
        );
        assert!(progress.iter().any(|p| p["stage"] == "Stockfish installed"));
        progress.clear();
        assert_eq!(
            ensure_stockfish(&AtomicBool::new(false), |p| progress.push(p)).unwrap(),
            engine
        );
        assert_eq!(progress.len(), 1);
        assert_eq!(progress[0]["stage"], "Checking Stockfish in the app folder");
        return;
    }
    let temp = Temp::new();
    let exe = temp.0.join(if cfg!(windows) {
        "app-startup-test.exe"
    } else {
        "app-startup-test"
    });
    fs::copy(std::env::current_exe().unwrap(), &exe).unwrap();
    let mut child = Command::new(exe);
    child
        .args([
            "--ignored",
            "--exact",
            "default_startup_installs_in_the_app_folder_and_reuses_it_on_the_next_launch_check",
        ])
        .env("CHESSPILOT_INSTALL_CHILD", "1")
        .env("CHESSPILOT_DATA_HOME", temp.0.join("unrelated-profile"));
    helper::run(
        child,
        Duration::from_secs(180),
        16384,
        &AtomicBool::new(false),
        || Ok(()),
    )
    .unwrap();
    assert!(!temp
        .0
        .join("unrelated-profile/native/stockfish.exe")
        .exists());
}
