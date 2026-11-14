; Installeur Windows de Caviste (Inno Setup 6).
; Compilé par build.bat : ISCC packaging\caviste.iss

#define AppName "Caviste"
#define AppVersion "1.0.0"
#define AppPublisher "Franck Nz"

[Setup]
AppId={{6E1C5D2B-8E7A-4C37-9A57-CAF15CA7E001}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppContact=064 08 88 68 / 057 66 83 71
AppSupportPhone=064 08 88 68 / 057 66 83 71
AppComments=Gestion de cave. Développé par Franck Nz (064 08 88 68 / 057 66 83 71).
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Caviste, gestion de cave
DefaultDirName={localappdata}\Programs\Caviste
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Caviste-Installation-{#AppVersion}
SetupIconFile=caviste.ico
UninstallDisplayIcon={app}\Caviste.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer une icône sur le Bureau"; GroupDescription: "Raccourcis :"
Name: "demoicon"; Description: "Ajouter aussi la cave de démonstration (données fictives)"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "..\dist\Caviste\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Caviste"; Filename: "{app}\Caviste.exe"
Name: "{autodesktop}\Caviste"; Filename: "{app}\Caviste.exe"; Tasks: desktopicon
Name: "{group}\Caviste (démonstration)"; Filename: "{app}\Caviste.exe"; Parameters: "--demo"; Tasks: demoicon
Name: "{group}\Désinstaller Caviste"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\Caviste.exe"; Description: "Lancer Caviste"; Flags: nowait postinstall skipifsilent

; Les données de la boutique (%LOCALAPPDATA%\Caviste) ne sont jamais supprimées à la désinstallation.
