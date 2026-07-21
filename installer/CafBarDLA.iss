#define AppName "CafBarDLA POS"
#define AppVersion "0.1.0"
#define AppPublisher "DLA Tecnología - Software - Ciberseguridad"
#define AppExeName "CafBarDLA.exe"

[Setup]
AppId={{91AC035D-D9B3-466D-B28A-7CF4E7C8E04D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\CafBarDLA
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=CafBarDLA-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\CafBarDLA\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "..\.env.windows.example"; DestDir: "{app}"; DestName: ".env"; Flags: onlyifdoesntexist
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\CafBarDLA POS"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\CafBarDLA POS"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir CafBarDLA POS"; Flags: nowait postinstall skipifsilent
