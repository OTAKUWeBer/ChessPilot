import java.security.MessageDigest

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

data class AndroidNativeTarget(val abi: String, val rustTarget: String, val clangTarget: String)

val nativePlatforms = linkedMapOf(
    "android-arm" to AndroidNativeTarget("armeabi-v7a", "armv7-linux-androideabi", "armv7a-linux-androideabi"),
    "android-arm64" to AndroidNativeTarget("arm64-v8a", "aarch64-linux-android", "aarch64-linux-android"),
    "android-x64" to AndroidNativeTarget("x86_64", "x86_64-linux-android", "x86_64-linux-android"),
)
val selectedTargets = providers.gradleProperty("target-platform")
    .orElse(nativePlatforms.keys.joinToString(",")).get().split(",").map { platform ->
        checkNotNull(nativePlatforms[platform]) { "Unsupported Android target: $platform" }
    }
val splitPerAbi = providers.gradleProperty("split-per-abi").orNull.toBoolean()

android {
    namespace = "io.github.otakuweber.chesspilot"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = "io.github.otakuweber.chesspilot"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        configureEach {
            if (!splitPerAbi) {
                ndk.abiFilters.clear()
                ndk.abiFilters.addAll(selectedTargets.map { it.abi })
            }
        }
        release {
            // Preserve the existing APK update identity; signing limitations are documented in docs/RELEASING.md.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
    packaging { jniLibs.useLegacyPackaging = true }
}

val nativeRoot = file("../../../native").canonicalFile
val engineAssets = file("${nativeRoot}/target/android-assets")
val generatedNative = layout.buildDirectory.dir("generated/nativeLibraries")
val generatedAssets = layout.buildDirectory.dir("generated/nativeAssets")
val rustBuilds = selectedTargets.map { target ->
    tasks.register<Exec>("buildRust_${target.abi.replace('-', '_')}") {
        workingDir(nativeRoot)
        val toolchain = providers.gradleProperty("rustToolchain").orNull
        commandLine(listOf("cargo") + listOfNotNull(toolchain?.let { "+$it" }) +
            listOf("build", "-p", "chesspilot-runtime", "--locked", "--target", target.rustTarget, "--release"))
        val windows = System.getProperty("os.name").startsWith("Windows")
        val host = if (windows) "windows-x86_64" else if (System.getProperty("os.name").startsWith("Mac")) "darwin-x86_64" else "linux-x86_64"
        val ndk = file("${android.sdkDirectory}/ndk/${android.ndkVersion}")
        val linker = "$ndk/toolchains/llvm/prebuilt/$host/bin/${target.clangTarget}24-clang${if (windows) ".cmd" else ""}"
        val prefix = "CARGO_TARGET_${target.rustTarget.uppercase().replace('-', '_')}"
        environment("${prefix}_LINKER", linker)
        environment("${prefix}_RUSTFLAGS", "-C link-arg=-Wl,-z,max-page-size=16384")
        inputs.files(fileTree(nativeRoot) { include("**/src/**/*.rs", "**/Cargo.toml", "Cargo.lock"); exclude("target/**") })
        outputs.file(file("${nativeRoot}/target/${target.rustTarget}/release/libchesspilot_runtime.so"))
    }
}
val buildRust by tasks.registering { dependsOn(rustBuilds) }
val packageNative by tasks.registering(Sync::class) {
    dependsOn(buildRust)
    selectedTargets.forEach { target ->
        from("${nativeRoot}/target/${target.rustTarget}/release/libchesspilot_runtime.so") { into(target.abi) }
        from("$engineAssets/${target.abi}") {
            include("libstockfish.so")
            if (target.abi == "arm64-v8a") include("libstockfish_dotprod.so")
            into(target.abi)
        }
    }
    into(generatedNative)
    doFirst {
        selectedTargets.forEach { target ->
            val names = if (target.abi == "arm64-v8a") listOf("libstockfish.so", "libstockfish_dotprod.so") else listOf("libstockfish.so")
            check(names.all { file("$engineAssets/${target.abi}/$it").isFile }) {
                "Prepare Android Stockfish for ${target.abi} first; see docs/BUILDING.md"
            }
        }
    }
}
val packageAssets by tasks.registering(Sync::class) {
    from("../../../assets/models/chess_detection.onnx")
    from("$engineAssets/licenses") { into("licenses") }
    from("../../../LICENSE") { into("licenses"); rename { "ChessPilot-MIT.txt" } }
    from("../../../native/runtime/third_party/Pillow-LICENSE.txt") { into("licenses") }
    from("$engineAssets/networks/nn-1a298aa575a0.nnue") { into("networks") }
    into(generatedAssets)
    doFirst {
        check(file("../../../assets/models/chess_detection.onnx").isFile) { "Missing assets/models/chess_detection.onnx" }
        check(file("$engineAssets/networks/nn-1a298aa575a0.nnue").isFile) { "Prepare Android Stockfish network first" }
    }
    doLast {
        val model = generatedAssets.get().file("chess_detection.onnx").asFile
        val digest = MessageDigest.getInstance("SHA-256").digest(model.readBytes())
        generatedAssets.get().file("chess_detection.onnx.sha256").asFile.writeText(
            digest.joinToString("") { "%02x".format(it.toInt() and 255) } + "\n"
        )
    }
}
android.sourceSets.getByName("main").apply {
    jniLibs.srcDir(generatedNative)
    assets.srcDir(generatedAssets)
}
tasks.named("preBuild") { dependsOn(packageNative, packageAssets) }

dependencies {
    // Android runtime exposes the C API used by the pinned ort binding; native device tests remain required.
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.23.2")
    testImplementation("junit:junit:4.13.2")
}

flutter {
    source = "../.."
}
