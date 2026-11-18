param(
    [string]$BundleDir = (Join-Path $PSScriptRoot '../app/build/windows/x64/runner/Release'),
    [string]$OutputDir = (Join-Path $PSScriptRoot '../app/build/windows/installer'),
    [string]$IsccPath,
    [switch]$TestPackage
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$BundleDir = [IO.Path]::GetFullPath($BundleDir).TrimEnd('\', '/')
$OutputDir = [IO.Path]::GetFullPath($OutputDir).TrimEnd('\', '/')
if ($OutputDir -eq $BundleDir -or $OutputDir.StartsWith($BundleDir + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Installer output must be outside the app bundle.'
}
$versionText = Get-Content -LiteralPath (Join-Path $repo 'app/pubspec.yaml') -Raw
$version = [regex]::Match($versionText, '(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)\+([0-9]+)\s*$')
if (-not $version.Success) { throw 'Expected version: MAJOR.MINOR.PATCH[-prerelease]+BUILD in pubspec.yaml.' }
$appVersion = $version.Groups[1].Value
$buildNumber = $version.Groups[2].Value
$versionQuad = ($appVersion -split '-')[0] + '.' + $buildNumber
foreach ($part in $versionQuad.Split('.')) {
    if ([long]$part -gt 65535) { throw 'Windows version components must fit in 16 bits.' }
}
$required = @('chesspilot.exe', 'chesspilot_runtime.dll', 'flutter_windows.dll', 'onnxruntime.dll',
    'onnxruntime_providers_shared.dll', 'msvcp140.dll', 'vcruntime140.dll', 'chess_detection.onnx',
    'ChessPilot-LICENSE.txt', 'data/app.so', 'data/icudtl.dat',
    'licenses/ONNXRuntime/ONNXRuntime-LICENSE.txt', 'licenses/ONNXRuntime/ONNXRuntime-ThirdPartyNotices.txt',
    'licenses/ONNXRuntime/ONNXRuntime-SOURCE.txt', 'licenses/Pillow-LICENSE.txt')
foreach ($file in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $BundleDir $file) -PathType Leaf)) {
        throw "Incomplete Windows release bundle: missing $file. Build with flutter build windows --release first."
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $BundleDir 'data/flutter_assets') -PathType Container)) {
    throw 'Missing Flutter assets; rebuild the complete release bundle.'
}
$exe = Get-Item -LiteralPath (Join-Path $BundleDir 'chesspilot.exe')
if ($exe.VersionInfo.ProductVersion -ne "$appVersion+$buildNumber") {
    throw 'The release executable version differs from pubspec.yaml; rebuild before packaging.'
}
$stream = [IO.File]::OpenRead($exe.FullName)
try {
    $reader = [IO.BinaryReader]::new($stream)
    if ($reader.ReadUInt16() -ne 0x5a4d) { throw 'Invalid Windows executable.' }
    $stream.Position = 0x3c
    $offset = $reader.ReadInt32()
    $stream.Position = $offset
    if ($reader.ReadUInt32() -ne 0x4550 -or $reader.ReadUInt16() -ne 0x8664) {
        throw 'This installer requires an x64 Windows release executable.'
    }
} finally { $stream.Dispose() }
$expected = ((Get-Content -LiteralPath (Join-Path $repo 'assets/models/chess_detection.onnx.sha256') -Raw).Trim() -split '\s+')[0]
if ((Get-FileHash -LiteralPath (Join-Path $BundleDir 'chess_detection.onnx') -Algorithm SHA256).Hash -ne $expected) {
    throw 'Bundled ONNX model differs from the tracked Python model.'
}
if (-not $IsccPath) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { $IsccPath = $command.Source }
    else {
        $IsccPath = @("${env:ProgramFiles(x86)}/Inno Setup 6/ISCC.exe", "$env:ProgramFiles/Inno Setup 6/ISCC.exe") |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    }
}
if (-not $IsccPath -or -not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) {
    throw 'Install Inno Setup 6.3 or newer, put ISCC.exe on PATH, or pass -IsccPath.'
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$outputName = "ChessPilot-$appVersion-windows-x64"
if ($TestPackage) { $outputName += '-test' }
$outputName += '-setup'
$arguments = @('/Qp', "/DBundleDir=$BundleDir", "/DOutputDir=$OutputDir", "/DOutputName=$outputName",
    "/DAppVersion=$appVersion", "/DVersionQuad=$versionQuad")
if ($TestPackage) { $arguments += '/DTestPackage=1' }
& $IsccPath @arguments (Join-Path $repo 'packaging/windows/chesspilot.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE." }
Get-Item -LiteralPath (Join-Path $OutputDir "$outputName.exe")
