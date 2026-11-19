param(
    [Parameter(Mandatory=$true)][string]$AndroidSdk,
    [string]$Flutter = 'flutter',
    [switch]$AllowDevelopmentSigning
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not (Test-Path -LiteralPath "$repo/app/android/key.properties")) {
    if (-not $AllowDevelopmentSigning) {
        throw 'Configure app/android/key.properties for publisher signing; see docs/RELEASING.md. Use -AllowDevelopmentSigning only for local testing with the existing debug key.'
    }
    Write-Warning 'Using the local debug signing key. These APKs are for testing, not publisher-signed distribution.'
}
$version = [regex]::Match((Get-Content "$repo/app/pubspec.yaml" -Raw), '(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)\+\d+\s*$').Groups[1].Value
if (-not $version) { throw 'Invalid pubspec release version' }
$output = Join-Path $repo "dist/$version/android"
New-Item -ItemType Directory -Force -Path $output | Out-Null
& rustup target add armv7-linux-androideabi aarch64-linux-android x86_64-linux-android
if ($LASTEXITCODE -ne 0) { throw 'Android Rust target installation failed' }
& "$PSScriptRoot/prepare_android.ps1" -AndroidSdk $AndroidSdk
Push-Location "$repo/app"
try {
    # Separate builds retain the shared versionCode; Flutter's split mode adds ABI offsets.
    $targets = [ordered]@{ armv7 = 'android-arm'; arm64 = 'android-arm64'; x86_64 = 'android-x64' }
    foreach ($variant in $targets.Keys) {
        & $Flutter build apk --release --target-platform $targets[$variant]
        if ($LASTEXITCODE -ne 0) { throw "APK build failed: $variant" }
        Move-Item -LiteralPath 'build/app/outputs/flutter-apk/app-release.apk' -Destination "$output/ChessPilot-$version-android-$variant.apk" -Force
    }
    & $Flutter build apk --release --no-pub --target-platform 'android-arm,android-arm64,android-x64'
    if ($LASTEXITCODE -ne 0) { throw 'Universal APK build failed' }
    Move-Item -LiteralPath 'build/app/outputs/flutter-apk/app-release.apk' -Destination "$output/ChessPilot-$version-android-universal.apk" -Force
} finally { Pop-Location }
& "$PSScriptRoot/test_android_packages.ps1" -Directory $output -AndroidSdk $AndroidSdk
Get-ChildItem -LiteralPath $output -Filter '*.apk'
