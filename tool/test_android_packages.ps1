param(
    [Parameter(Mandatory=$true)][string]$Directory,
    [Parameter(Mandatory=$true)][string]$AndroidSdk
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$versionText = Get-Content "$repo/app/pubspec.yaml" -Raw
$versionMatch = [regex]::Match($versionText, '(?m)^version:\s*([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)\+(\d+)\s*$')
if (-not $versionMatch.Success) { throw 'Invalid pubspec release version' }
$version = $versionMatch.Groups[1].Value
$build = $versionMatch.Groups[2].Value
$expected = [ordered]@{
    armv7 = @('armeabi-v7a')
    arm64 = @('arm64-v8a')
    x86_64 = @('x86_64')
    universal = @('armeabi-v7a','arm64-v8a','x86_64')
}
$machines = @{ 'armeabi-v7a' = 40; 'arm64-v8a' = 183; 'x86_64' = 62 }
$modelHash = ((Get-Content "$repo/assets/models/chess_detection.onnx.sha256" -Raw).Trim() -split '\s+')[0]
$suffix = if ($env:OS -eq 'Windows_NT') { '.exe' } else { '' }
$signer = if ($env:OS -eq 'Windows_NT') { '.bat' } else { '' }
$tools = Join-Path $AndroidSdk 'build-tools/36.0.0'
$certificate = $null
foreach ($variant in $expected.Keys) {
    $apk = Join-Path $Directory "ChessPilot-$version-android-$variant.apk"
    & "$tools/apksigner$signer" verify --verbose $apk | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "APK signature validation failed: $variant" }
    $cert = (& "$tools/apksigner$signer" verify --print-certs $apk | Select-String '^Signer #1 certificate SHA-256 digest:').ToString()
    if ($certificate -and $cert -ne $certificate) { throw 'APK variants use different signing identities' }
    $certificate = $cert
    & "$tools/zipalign$suffix" -c -P 16 4 $apk
    if ($LASTEXITCODE -ne 0) { throw "APK alignment validation failed: $variant" }
    $package = (& "$tools/aapt$suffix" dump badging $apk | Select-String '^package:').ToString()
    if ($package -notmatch "name='io.github.otakuweber.chesspilot'" -or $package -notmatch "versionName='$([regex]::Escape($version))'" -or $package -notmatch "versionCode='$build'") {
        throw "APK identity/version mismatch: $variant"
    }
    $permissions = (& "$tools/aapt$suffix" dump permissions $apk) -join "`n"
    foreach ($permission in @('READ_SMS','RECEIVE_SMS','READ_CONTACTS','READ_CALL_LOG','BIND_NOTIFICATION_LISTENER_SERVICE','QUERY_ALL_PACKAGES','REQUEST_INSTALL_PACKAGES')) {
        if ($permissions.Contains("android.permission.$permission'")) { throw "Unexpected sensitive permission: $permission" }
    }
    $zip = [IO.Compression.ZipFile]::OpenRead([IO.Path]::GetFullPath($apk))
    try {
        $abis = @($zip.Entries | ForEach-Object { if ($_.FullName -match '^lib/([^/]+)/') { $Matches[1] } } | Sort-Object -Unique)
        if (Compare-Object ($expected[$variant] | Sort-Object) $abis) { throw "Unexpected APK ABIs: $variant ($abis)" }
        foreach ($abi in $abis) {
            foreach ($name in @('libflutter.so','libapp.so','libchesspilot_runtime.so','libonnxruntime.so','libstockfish.so')) {
                $entry = $zip.GetEntry("lib/$abi/$name")
                if (-not $entry) { throw "Missing $abi/$name in $variant" }
                $stream = $entry.Open()
                try {
                    $reader = [IO.BinaryReader]::new($stream)
                    $header = $reader.ReadBytes(64)
                    $bits = if ($abi -eq 'armeabi-v7a') { 1 } else { 2 }
                    if ($header.Length -lt 64 -or $header[0] -ne 127 -or [Text.Encoding]::ASCII.GetString($header,1,3) -ne 'ELF' -or $header[4] -ne $bits -or [BitConverter]::ToUInt16($header,18) -ne $machines[$abi]) {
                        throw "Wrong native architecture: $variant $abi/$name"
                    }
                } finally { $stream.Dispose() }
            }
        }
        foreach ($asset in @{
            'assets/chess_detection.onnx' = $modelHash
            'assets/networks/nn-1a298aa575a0.nnue' = '1a298aa575a085434d29027978dc36867fe9c5bcea9376654b7a8eba1e52dfc2'
        }.GetEnumerator()) {
            $entry = $zip.GetEntry($asset.Key)
            if (-not $entry) { throw "Missing $($asset.Key)" }
            $stream = $entry.Open()
            $sha = [Security.Cryptography.SHA256]::Create()
            try {
                $hash = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','').ToLowerInvariant()
                if ($hash -ne $asset.Value) { throw "Bundled asset checksum mismatch: $($asset.Key)" }
            } finally { $sha.Dispose(); $stream.Dispose() }
        }
        foreach ($notice in @('ChessPilot-MIT.txt','Pillow-LICENSE.txt','Stockfish-GPL-3.0.txt','Stockfish-SOURCE.txt')) {
            if (-not $zip.GetEntry("assets/licenses/$notice")) { throw "Missing license notice: $notice" }
        }
    } finally { $zip.Dispose() }
    Write-Output "Verified $variant APK: version, signature, alignment, native ABIs, model, NNUE and licenses."
}
