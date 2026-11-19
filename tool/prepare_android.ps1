param(
    [Parameter(Mandatory=$true)][string]$AndroidSdk,
    [string]$NdkVersion = '28.2.13676358',
    [ValidateSet('arm64-v8a','armeabi-v7a','x86_64')]
    [string[]]$Abis = @('arm64-v8a','armeabi-v7a','x86_64')
)
$ErrorActionPreference = 'Stop'
$native = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../native'))
$cache = Join-Path $native 'target/android-tools'
$assets = Join-Path $native 'target/android-assets'
New-Item -ItemType Directory -Force -Path $cache, "$assets/networks", "$assets/licenses" | Out-Null
$revision = 'edb0d9db6731067ec50ce619ff372b463bc4dd5d'
$url = "https://codeload.github.com/official-stockfish/Stockfish/tar.gz/$revision"
$archive = Join-Path $cache "stockfish-$revision.tar.gz"
if (-not (Test-Path -LiteralPath $archive)) { Invoke-WebRequest -Uri $url -OutFile $archive }
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne '4FC20699A5ECF7883B036CE180020F5E57979623AD719FD2A52839209521581B') {
    throw 'Stockfish source hash mismatch; remove the cached archive and retry'
}
$source = Join-Path $cache "stockfish-$revision"
New-Item -ItemType Directory -Force -Path $source | Out-Null
& tar -xf $archive -C $source --strip-components=1
if ($LASTEXITCODE -ne 0) { throw 'Stockfish source extraction failed' }
$net = 'nn-1a298aa575a0.nnue'
$path = Join-Path "$assets/networks" $net
if (-not (Test-Path -LiteralPath $path)) {
    Invoke-WebRequest -Uri "https://github.com/official-stockfish/networks/raw/master/$net" -OutFile $path
}
if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne '1A298AA575A085434D29027978DC36867FE9C5BCEA9376654B7A8EBA1E52DFC2') {
    throw "Invalid Stockfish network: $net"
}
$windowsHost = $env:OS -eq 'Windows_NT'
$suffix = if ($windowsHost) { '.exe' } else { '' }
$hostTag = if ($windowsHost) { 'windows-x86_64' } else { 'linux-x86_64' }
$ndk = Join-Path $AndroidSdk "ndk/$NdkVersion"
$cmakeBin = Join-Path $AndroidSdk 'cmake/3.22.1/bin'
$readelf = Join-Path $ndk "toolchains/llvm/prebuilt/$hostTag/bin/llvm-readelf$suffix"
foreach ($abi in $Abis) {
    $build = Join-Path $cache "stockfish-19-$abi-build"
    & "$cmakeBin/cmake$suffix" -S "$PSScriptRoot/stockfish" -B $build -G Ninja "-DCMAKE_MAKE_PROGRAM=$cmakeBin/ninja$suffix" "-DCMAKE_TOOLCHAIN_FILE=$ndk/build/cmake/android.toolchain.cmake" "-DANDROID_ABI=$abi" '-DANDROID_PLATFORM=android-24' '-DANDROID_STL=c++_static' "-DSTOCKFISH_SOURCE=$source" '-DCMAKE_BUILD_TYPE=Release'
    if ($LASTEXITCODE -ne 0) { throw "Stockfish CMake configuration failed: $abi" }
    & "$cmakeBin/cmake$suffix" --build $build --parallel 4
    if ($LASTEXITCODE -ne 0) { throw "Stockfish compilation failed: $abi" }
    New-Item -ItemType Directory -Force -Path "$assets/$abi" | Out-Null
    $binaries = if ($abi -eq 'arm64-v8a') { @('libstockfish.so','libstockfish_dotprod.so') } else { @('libstockfish.so') }
    foreach ($binary in $binaries) {
        $headers = & $readelf -h -l (Join-Path $build $binary)
        if ($LASTEXITCODE -ne 0 -or -not ($headers -match 'Type:.*DYN')) { throw "Stockfish must be a PIE executable: $abi/$binary" }
        foreach ($line in ($headers | Where-Object { $_ -match '^\s*LOAD\s' })) {
            $alignment = [Convert]::ToInt64(($line.Trim() -split '\s+')[-1].Substring(2),16)
            if ($alignment -lt 16384) { throw "Stockfish needs 16 KB load-segment alignment: $abi/$binary" }
        }
        Copy-Item -LiteralPath (Join-Path $build $binary) -Destination (Join-Path "$assets/$abi" $binary)
    }
}
Copy-Item -LiteralPath (Join-Path $source 'Copying.txt') -Destination "$assets/licenses/Stockfish-GPL-3.0.txt"
@"
Stockfish 19, GPL-3.0-or-later; Android executables built without source changes.
Exact source archive: $url
SHA256: 4fc20699a5ecf7883b036ce180020f5e57979623ad719fd2a52839209521581b
Source commit: https://github.com/official-stockfish/Stockfish/tree/$revision
Build recipe: tool/stockfish/CMakeLists.txt and prepare_android.ps1 in the corresponding ChessPilot source.
Network: https://github.com/official-stockfish/networks; SHA256 1a298aa575a085434d29027978dc36867fe9c5bcea9376654b7a8eba1e52dfc2.
"@ | Set-Content -LiteralPath "$assets/licenses/Stockfish-SOURCE.txt" -Encoding utf8
Write-Output "Android engines prepared at $assets for $($Abis -join ', ')"
