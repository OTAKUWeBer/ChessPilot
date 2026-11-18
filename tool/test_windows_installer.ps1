param(
    [string]$BundleDir = (Join-Path $PSScriptRoot '../app/build/windows/x64/runner/Release'),
    [string]$IsccPath
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$work = Join-Path $repo ('native/target/windows-installer-smoke/' + [guid]::NewGuid().ToString('N'))
$install = Join-Path $work 'installed app'
$registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\io.github.otakuweber.chesspilot.installer-test_is1'
if (Test-Path -LiteralPath $registry) { throw 'An earlier installer-test registration exists; remove that test installation first.' }
New-Item -ItemType Directory -Force -Path $work | Out-Null
$builder = @{ BundleDir = $BundleDir; OutputDir = (Join-Path $work 'packages with spaces'); TestPackage = $true }
if ($IsccPath) { $builder.IsccPath = $IsccPath }
& (Join-Path $PSScriptRoot 'build_windows_installer.ps1') @builder | Out-Host
$setup = @(Get-ChildItem -LiteralPath $builder.OutputDir -Filter '*-test-setup.exe')
if ($setup.Count -ne 1) { throw 'Expected one isolated test installer.' }
function Invoke-Setup([string]$Path, [string[]]$Arguments) {
    $process = Start-Process -FilePath $Path -ArgumentList $Arguments -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Installer process failed: $($process.ExitCode). See $work." }
}
$installArgs = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/TASKS=""', "/DIR=`"$install`"")
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'ChessPilot Installer Test/ChessPilot.lnk'
$installed = $false
try {
    Invoke-Setup $setup[0].FullName ($installArgs + "/LOG=`"$(Join-Path $work 'first-install.log')`"")
    $installed = $true
    if (-not (Test-Path -LiteralPath $registry)) { throw 'Missing per-user uninstall registration.' }
    if (-not (Test-Path -LiteralPath $shortcut)) { throw 'Missing Start menu shortcut.' }
    $shell = New-Object -ComObject WScript.Shell
    try {
        $link = $shell.CreateShortcut($shortcut)
        if ($link.TargetPath -ne (Join-Path $install 'chesspilot.exe')) { throw 'Incorrect shortcut target.' }
    } finally { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shell) }
    $bundle = [IO.Path]::GetFullPath($BundleDir).TrimEnd('\', '/')
    $payloadFiles = @(Get-ChildItem -LiteralPath $bundle -File | Where-Object { $_.Extension -eq '.dll' })
    foreach ($name in @('chesspilot.exe', 'chess_detection.onnx', 'ChessPilot-LICENSE.txt')) {
        $payloadFiles += Get-Item -LiteralPath (Join-Path $bundle $name)
    }
    if (Test-Path -LiteralPath (Join-Path $bundle 'native_assets.json')) {
        $payloadFiles += Get-Item -LiteralPath (Join-Path $bundle 'native_assets.json')
    }
    foreach ($folder in @('data', 'licenses')) {
        $payloadFiles += Get-ChildItem -LiteralPath (Join-Path $bundle $folder) -Recurse -File
    }
    foreach ($file in $payloadFiles) {
        $relative = $file.FullName.Substring($bundle.Length + 1)
        $copied = Join-Path $install $relative
        if ((Get-FileHash -LiteralPath $copied).Hash -ne (Get-FileHash -LiteralPath $file.FullName).Hash) {
            throw "Installed payload differs: $relative"
        }
    }
    foreach ($name in @('stockfish.exe', 'engine_config.txt', 'download-cache')) {
        if (Test-Path -LiteralPath (Join-Path $install $name)) { throw "Local user data leaked into setup: $name" }
    }
    New-Item -ItemType Directory -Path (Join-Path $install 'download-cache') | Out-Null
    $userFiles = @('engine_config.txt', 'stockfish.exe', 'download-cache/sentinel.txt')
    foreach ($name in $userFiles) { [IO.File]::WriteAllText((Join-Path $install $name), "User-owned fixture: $name") }
    Invoke-Setup $setup[0].FullName ($installArgs + "/LOG=`"$(Join-Path $work 'upgrade.log')`"")
    foreach ($name in $userFiles) {
        if ([IO.File]::ReadAllText((Join-Path $install $name)) -ne "User-owned fixture: $name") {
            throw "Upgrade changed user-owned data: $name"
        }
    }
    Invoke-Setup (Join-Path $install 'unins000.exe') @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=`"$(Join-Path $work 'uninstall.log')`"")
    $installed = $false
    if ((Test-Path -LiteralPath $registry) -or (Test-Path -LiteralPath $shortcut)) { throw 'Uninstall left its registration or shortcut.' }
    foreach ($name in @('chesspilot.exe', 'chesspilot_runtime.dll', 'chess_detection.onnx')) {
        if (Test-Path -LiteralPath (Join-Path $install $name)) { throw "Uninstall left packaged payload: $name" }
    }
    foreach ($name in $userFiles) {
        if ([IO.File]::ReadAllText((Join-Path $install $name)) -ne "User-owned fixture: $name") {
            throw "Uninstall changed user-owned data: $name"
        }
    }
    Write-Output 'Installer passed: payload, shortcuts, isolated registration, upgrade preservation and uninstall.'
} finally {
    if ($installed -and (Test-Path -LiteralPath (Join-Path $install 'unins000.exe'))) {
        Invoke-Setup (Join-Path $install 'unins000.exe') @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
    }
    Write-Output "Installer test artifacts: $work"
}
