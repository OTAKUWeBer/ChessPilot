plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

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
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "io.github.otakuweber.chesspilot"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        configureEach {
            ndk.abiFilters.clear()
            ndk.abiFilters.add("arm64-v8a")
        }
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
    packaging { jniLibs.useLegacyPackaging = true }
}

val nativeRoot = file("../../../native").canonicalFile
val engineAssets = file("${nativeRoot}/target/android-assets")
val rustLibrary = file("${nativeRoot}/target/aarch64-linux-android/release/libchesspilot_runtime.so")
val generatedNative = layout.buildDirectory.dir("generated/nativeLibraries")
val generatedAssets = layout.buildDirectory.dir("generated/nativeAssets")
val buildRust by tasks.registering(Exec::class) {
    workingDir(nativeRoot)
    val toolchain = providers.gradleProperty("rustToolchain").orNull
    commandLine(listOf("cargo") + listOfNotNull(toolchain?.let { "+$it" }) +
        listOf("build", "-p", "chesspilot-runtime", "--target", "aarch64-linux-android", "--release"))
    val windows = System.getProperty("os.name").startsWith("Windows")
    val host = if (windows) "windows-x86_64" else if (System.getProperty("os.name").startsWith("Mac")) "darwin-x86_64" else "linux-x86_64"
    val ndk = file("${android.sdkDirectory}/ndk/${android.ndkVersion}")
    environment("CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER", "$ndk/toolchains/llvm/prebuilt/$host/bin/aarch64-linux-android24-clang${if (windows) ".cmd" else ""}")
    environment("CARGO_TARGET_AARCH64_LINUX_ANDROID_RUSTFLAGS", "-C link-arg=-Wl,-z,max-page-size=16384")
    inputs.files(fileTree(nativeRoot) { include("**/src/**/*.rs", "**/Cargo.toml", "Cargo.lock"); exclude("target/**") })
    outputs.file(rustLibrary)
}
val packageNative by tasks.registering(Sync::class) {
    dependsOn(buildRust)
    from(rustLibrary) { into("arm64-v8a") }
    from("$engineAssets/arm64-v8a/libstockfish.so") { into("arm64-v8a") }
    into(generatedNative)
    doFirst {
        check(file("$engineAssets/arm64-v8a/libstockfish.so").isFile) {
            "Prepare Android Stockfish first; see next/android-testing.md"
        }
    }
}
val packageAssets by tasks.registering(Sync::class) {
    from("../../../../src/chess_detection.onnx")
    from("$engineAssets/licenses") { into("licenses") }
    into(generatedAssets)
    doFirst { check(file("../../../../src/chess_detection.onnx").isFile) { "Missing src/chess_detection.onnx" } }
}
android.sourceSets.getByName("main").apply {
    jniLibs.srcDir(generatedNative)
    assets.srcDir(generatedAssets)
}
tasks.named("preBuild") { dependsOn(packageNative, packageAssets) }

dependencies {
    // Android runtime exposes the C API used by the pinned ort binding; native device tests remain required.
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.23.2")
}

flutter {
    source = "../.."
}
