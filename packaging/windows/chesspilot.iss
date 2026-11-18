#ifndef BundleDir
  #error Build with tool/build_windows_installer.ps1
#endif
#ifdef TestPackage
  #define AppName "ChessPilot Installer Test"
  #define AppId "io.github.otakuweber.chesspilot.installer-test"
#else
  #define AppName "ChessPilot"
  #define AppId "io.github.otakuweber.chesspilot.desktop"
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Weber
AppPublisherURL=https://github.com/OTAKUWeBer/ChessPilot
AppSupportURL=https://github.com/OTAKUWeBer/ChessPilot/issues
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
SetupIconFile=..\..\assets\logo.ico
LicenseFile={#BundleDir}\ChessPilot-LICENSE.txt
UninstallDisplayIcon={app}\chesspilot.exe
VersionInfoVersion={#VersionQuad}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#VersionQuad}
VersionInfoTextVersion={#AppVersion}
VersionInfoProductTextVersion={#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

; Only immutable build payload belongs here. Engine/config/cache files stay user-owned.
[Files]
Source: "{#BundleDir}\chesspilot.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BundleDir}\*.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BundleDir}\chess_detection.onnx"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BundleDir}\native_assets.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#BundleDir}\ChessPilot-LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BundleDir}\data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#BundleDir}\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ChessPilot"; Filename: "{app}\chesspilot.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\ChessPilot"; Filename: "{app}\chesspilot.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\chesspilot.exe"; Description: "Launch {#AppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
