#define MyAppName "Multifora"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.5"
#endif
#ifndef MyAppSource
  #define MyAppSource "..\dist\Multifora"
#endif
#ifndef MyOutputDir
  #define MyOutputDir "..\dist\installer"
#endif

[Setup]
AppId={{52A0322B-B489-42FC-A4E9-25B69CE180EC}
AppName=Мультифора
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=admin
UsePreviousAppDir=yes
ArchitecturesAllowed=x64compatible
OutputDir={#MyOutputDir}
OutputBaseFilename=Multifora-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\Multifora.exe
LicenseFile=..\LICENSE
InfoAfterFile=..\docs\project\INSTALLER_INFO.txt
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyAppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
Type: files; Name: "{app}\bin\pdfcraft\pdfcraft-cli.exe"
Type: files; Name: "{app}\bin\wordcraft\wordcraft-cli.exe"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\Multifora.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Multifora.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Multifora.exe"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
