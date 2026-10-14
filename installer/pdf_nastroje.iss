; Inno Setup script for the Windows installer. Built by build.py, which passes:
;   /DAppVersion=<version>   from pdftool.__version__
;   /DSourceDir=<dir>        the PyInstaller output folder (dist\PDF Nastroje)
;   /DIconFile=<file>        the generated app.ico
;   /DOutputDir=<dir>        where PDF-Nastroje-Setup.exe is written

#ifndef AppVersion
  #error AppVersion must be defined (run build.py instead of compiling this script directly)
#endif

#define AppName "PDF Nástroje"
#define AppExeName "PDF Nastroje.exe"

[Setup]
; The AppId identifies the application for upgrades and uninstallation; never change it.
AppId={{74BE936B-E4DE-44BD-9BF7-3D633065FD33}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Ivan Kuka
AppPublisherURL=https://github.com/IvanKuka/PeDeEf
AppSupportURL=https://github.com/IvanKuka/PeDeEf/issues
AppUpdatesURL=https://github.com/IvanKuka/PeDeEf/releases
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\PDF Nastroje
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Installs for the current user without administrator rights by default; the user
; can still choose an installation for all users (which asks for admin rights).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
OutputDir={#OutputDir}
OutputBaseFilename=PDF-Nastroje-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Lets the installer close a running copy of the app before replacing its files.
CloseApplications=yes

[Languages]
Name: "slovak"; MessagesFile: "compiler:Languages\Slovak.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; PyInstaller output differs between versions; remove the previous version's
; libraries so an upgrade does not mix old and new files.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
