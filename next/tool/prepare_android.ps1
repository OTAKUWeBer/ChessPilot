param(
    [Parameter(Mandatory=$true)][string]$AndroidSdk,
    [string]$NdkVersion = '28.2.13676358'
)
$ErrorActionPreference = 'Stop'
$native = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../native'))
$cache = Join-Path $native 'target/android-tools'
$assets = Join-Path $native 'target/android-assets'
New-Item -ItemType Directory -Force -Path $cache, "$assets/arm64-v8a", "$assets/networks", "$assets/licenses" | Out-Null
$archive = Join-Path $cache 'stockfish-android-armv8.tar'
$url = 'https://github.com/official-stockfish/Stockfish/releases/download/sf_17.1/stockfish-android-armv8.tar'
if (-not (Test-Path -LiteralPath $archive)) { Invoke-WebRequest -Uri $url -OutFile $archive }
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne '634D8E7AF7F776E641D909B49FA52E7F88E8EC3F18C0535EE63D564BF246EBCD') {
    throw 'Stockfish archive hash mismatch; remove the cached archive and retry'
}
$engine = Join-Path $cache 'engine'
New-Item -ItemType Directory -Force -Path $engine | Out-Null
& tar -xf $archive -C $engine
if ($LASTEXITCODE -ne 0) { throw 'Stockfish source extraction failed' }
$source = Join-Path $engine 'stockfish'
$networks = @{
    'nn-1c0000000000.nnue' = '1C0000000000A67D629999D932D0C373F7450CE43CD12D0562868F4EAF9AE2AD'
    'nn-37f18f62d772.nnue' = '37F18F62D772F3107E1D6AACA3898C130C3C86F2AB63E6555FBBCA20635A899D'
}
foreach ($net in $networks.Keys) {
    $path = Join-Path $source "src/$net"
    if (-not (Test-Path -LiteralPath $path)) {
        Invoke-WebRequest -Uri "https://github.com/official-stockfish/networks/raw/master/$net" -OutFile $path
    }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $networks[$net]) {
        throw "Invalid Stockfish network: $net"
    }
    Copy-Item -LiteralPath $path -Destination (Join-Path "$assets/networks" $net)
}
$ndk = Join-Path $AndroidSdk "ndk/$NdkVersion"
$cmakeBin = Join-Path $AndroidSdk 'cmake/3.22.1/bin'
$build = Join-Path $cache 'stockfish-build'
& "$cmakeBin/cmake.exe" -S "$PSScriptRoot/stockfish" -B $build -G Ninja "-DCMAKE_MAKE_PROGRAM=$cmakeBin/ninja.exe" "-DCMAKE_TOOLCHAIN_FILE=$ndk/build/cmake/android.toolchain.cmake" '-DANDROID_ABI=arm64-v8a' '-DANDROID_PLATFORM=android-24' '-DANDROID_STL=c++_static' "-DSTOCKFISH_SOURCE=$source"
if ($LASTEXITCODE -ne 0) { throw 'Stockfish CMake configuration failed' }
& "$cmakeBin/cmake.exe" --build $build --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Stockfish compilation failed' }
$readelf = Join-Path $ndk 'toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-readelf.exe'
foreach ($binary in @('libstockfish.so','libstockfish_dotprod.so')) {
$headers = & $readelf -h -l (Join-Path $build $binary)
if ($LASTEXITCODE -ne 0 -or -not ($headers -match 'Type:.*DYN')) { throw 'Stockfish must be a PIE executable' }
foreach ($line in ($headers | Where-Object { $_ -match '^\s*LOAD\s' })) {
    $alignment = [Convert]::ToInt64(($line.Trim() -split '\s+')[-1].Substring(2),16)
    if ($alignment -lt 16384) { throw 'Stockfish needs 16 KB load-segment alignment' }
}
Copy-Item -LiteralPath (Join-Path $build $binary) -Destination (Join-Path "$assets/arm64-v8a" $binary)
}
Copy-Item -LiteralPath (Join-Path $source 'Copying.txt') -Destination "$assets/licenses/Stockfish-GPL-3.0.txt"
@"
Stockfish 17.1, GPL-3.0-or-later; Android ARM64 executable built without source changes.
Exact source archive: $url
SHA256: 634d8e7af7f776e641d909b49fa52e7f88e8ec3f18c0535ee63d564bf246ebcd
Source tag: https://github.com/official-stockfish/Stockfish/tree/sf_17.1
Build recipe: next/tool/stockfish/CMakeLists.txt and prepare_android.ps1 in the ChessPilot source corresponding to this app.
Networks: https://github.com/official-stockfish/networks (full SHA256 hashes pinned in prepare_android.ps1).
"@ | Set-Content -LiteralPath "$assets/licenses/Stockfish-SOURCE.txt" -Encoding utf8
Write-Output "Android engine prepared at $assets"
