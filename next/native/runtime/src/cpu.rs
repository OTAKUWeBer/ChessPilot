//! Native replacement for cpu_features.py; unknown CPUs never gain assumed instructions.
use serde_json::{json, Value};
use std::collections::BTreeSet;
#[derive(Debug, Clone)]
pub struct CpuInfo {
    pub architecture: String,
    pub vendor: String,
    pub brand: String,
    pub features: BTreeSet<String>,
    pub cores: usize,
}
pub fn detect() -> CpuInfo {
    #[allow(unused_mut)]
    let mut cpu = CpuInfo {
        architecture: std::env::consts::ARCH.into(),
        vendor: "unknown".into(),
        brand: std::env::consts::ARCH.into(),
        features: BTreeSet::new(),
        cores: std::thread::available_parallelism()
            .map(usize::from)
            .unwrap_or(1),
    };
    #[cfg(target_arch = "x86_64")]
    {
        use std::arch::x86_64::__cpuid;
        // CPUID is part of the x86-64 baseline; feature macros also check OS vector-state support.
        let id = __cpuid(0);
        let vendor = [
            id.ebx.to_le_bytes(),
            id.edx.to_le_bytes(),
            id.ecx.to_le_bytes(),
        ]
        .concat();
        let vendor = String::from_utf8_lossy(&vendor);
        cpu.vendor = match vendor.as_ref() {
            "GenuineIntel" => "intel",
            "AuthenticAMD" => "amd",
            _ => "unknown",
        }
        .into();
        if __cpuid(0x80000000).eax >= 0x80000004 {
            let mut brand = Vec::with_capacity(48);
            for leaf in 0x80000002..=0x80000004 {
                let r = __cpuid(leaf);
                for word in [r.eax, r.ebx, r.ecx, r.edx] {
                    brand.extend(word.to_le_bytes());
                }
            }
            cpu.brand = String::from_utf8_lossy(&brand)
                .trim_matches('\0')
                .trim()
                .into();
        }
        macro_rules! feature {
            ($rust:tt,$name:literal) => {
                if std::is_x86_feature_detected!($rust) {
                    cpu.features.insert($name.into());
                }
            };
        }
        feature!("sse2", "sse2");
        feature!("sse4.1", "sse4_1");
        feature!("sse4.2", "sse4_2");
        feature!("popcnt", "popcnt");
        feature!("avx", "avx");
        feature!("avx2", "avx2");
        feature!("avxvnni", "avxvnni");
        feature!("bmi2", "bmi2");
        feature!("avx512f", "avx512f");
        feature!("avx512bw", "avx512bw");
        feature!("avx512dq", "avx512dq");
        feature!("avx512vl", "avx512vl");
        feature!("avx512vnni", "avx512vnni");
    }
    #[cfg(target_arch = "aarch64")]
    {
        cpu.vendor = "arm".into();
        if std::arch::is_aarch64_feature_detected!("neon") {
            cpu.features.insert("neon".into());
        }
        if std::arch::is_aarch64_feature_detected!("dotprod") {
            cpu.features.insert("dotprod".into());
        }
    }
    cpu
}
pub fn system_info() -> Value {
    let cpu = detect();
    json!({"os":std::env::consts::OS,"architecture":cpu.architecture,"cpu_vendor":cpu.vendor,"cpu_brand":cpu.brand,"cpu_cores":cpu.cores,"cpu_features":cpu.features,
        "runtime_version":env!("CARGO_PKG_VERSION"),"debug_build":cfg!(debug_assertions)})
}
pub fn format_bytes(mut bytes: f64) -> String {
    for unit in ["B", "KB", "MB", "GB", "TB"] {
        if bytes.abs() < 1024. {
            return format!("{bytes:.1} {unit}");
        }
        bytes /= 1024.;
    }
    format!("{bytes:.1} PB")
}
