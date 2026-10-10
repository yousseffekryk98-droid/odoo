#ifndef SourceDir
  #error SourceDir must be provided
#endif
#ifndef OutputDir
  #error OutputDir must be provided
#endif

[Setup]
AppId={{657C42A3-EEDC-4B66-9F41-A2123FE579D5}
AppName=TEQ ERP
AppVersion=1.0.0
AppPublisher=TEQ ERP
DefaultDirName={localappdata}\Programs\TEQ ERP
DefaultGroupName=TEQ ERP
UninstallDisplayIcon={app}\TEQ-ERP.exe
OutputDir={#OutputDir}
OutputBaseFilename=TEQ-ERP-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=yes
AllowNoIcons=yes
DiskSpanning=no
SetupLogging=yes

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Icons]
Name: "{autoprograms}\TEQ ERP"; Filename: "{app}\TEQ-ERP.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\TEQ ERP"; Filename: "{app}\TEQ-ERP.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\TEQ-ERP.exe"; Description: "Launch TEQ ERP"; Flags: nowait postinstall skipifsilent
