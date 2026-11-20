; Inno Setup script for SmartScan.
; Build the application first:   pyinstaller packaging/smartscan.spec --noconfirm
; Then compile this file:        iscc packaging/inno/smartscan.iss
; Result:                        dist/SmartScan-Setup-1.0.0.exe

#define AppName        "SmartScan"
#define AppVersion     "1.0.0"
#define AppPublisher   "SmartScan"
#define AppExeName     "SmartScan.exe"
#define SourceDir      "..\..\dist\SmartScan"
#define AssetsDir      "..\..\assets"

[Setup]
AppId={{8C3F1D42-7B25-4B5E-9A31-6E0D5C2F7A18}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Per-user install by default: no admin prompt, writes next to the user's data.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
SetupIconFile={#AssetsDir}\smartscan.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
LicenseFile=..\..\LICENSE
InfoBeforeFile=..\..\docs\install-notes.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associate"; Description: "Add SmartScan to the Open with menu for images"; GroupDescription: "Integration:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*";             DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#AssetsDir}\smartscan.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\..\HOW-TO-USE.md";        DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";              Filename: "{app}\{#AppExeName}"
Name: "{group}\How to use {#AppName}";   Filename: "{app}\HOW-TO-USE.md"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";        Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; "Open with" registration, only if the user asked for it.
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}"; ValueType: string; \
    ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Tasks: associate; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}\shell\open\command"; ValueType: string; \
    ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""; Tasks: associate; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}\SupportedTypes"; \
    ValueName: ".jpg"; ValueType: string; ValueData: ""; Tasks: associate; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}\SupportedTypes"; \
    ValueName: ".jpeg"; ValueType: string; ValueData: ""; Tasks: associate; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}\SupportedTypes"; \
    ValueName: ".png"; ValueType: string; ValueData: ""; Tasks: associate; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}\SupportedTypes"; \
    ValueName: ".tif"; ValueType: string; ValueData: ""; Tasks: associate; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\{#AppExeName}\SupportedTypes"; \
    ValueName: ".tiff"; ValueType: string; ValueData: ""; Tasks: associate; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
    Flags: nowait postinstall skipifsilent
Filename: "{app}\HOW-TO-USE.md"; Description: "Open the How-to-use guide"; \
    Flags: shellexec nowait postinstall skipifsilent unchecked
