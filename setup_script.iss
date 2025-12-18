[Setup]
AppId={{WPMV-PLAYER-2025-DONGT}}
AppName=WPMV Media Player
AppVersion=1.0
DefaultDirName={autopf}\WPMV Player
DefaultGroupName=WPMV Player
UninstallDisplayIcon={app}\WPMV_Player.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Cho phép tạo shortcut desktop và liên kết file
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "fileassoc"; Description: "Đặt làm trình phát mặc định cho Ảnh, Video và Nhạc"; GroupDescription: "Liên kết tệp tin:"

[Files]
; Lấy toàn bộ nội dung trong thư mục dist
Source: "dist*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; File K-Lite Codec Pack từ thư mục dependencies
Source: "dependencies\K-Lite_Codec_Pack_Standard.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\WPMV Player"; Filename: "{app}\WPMV_Player.exe"
Name: "{autodesktop}\WPMV Player"; Filename: "{app}\WPMV_Player.exe"; Tasks: desktopicon

[Registry]
; Đăng ký File Associations cho các định dạng phổ biến
Root: HKA; Subkey: "Software\Classes.mp4\OpenWithProgids"; ValueType: string; ValueName: "WPMVPlayer.AssocFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes.jpg\OpenWithProgids"; ValueType: string; ValueName: "WPMVPlayer.AssocFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes.mp3\OpenWithProgids"; ValueType: string; ValueName: "WPMVPlayer.AssocFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc

; Cấu hình cách hiển thị và lệnh thực thi cho loại file WPMVPlayer.AssocFile
Root: HKA; Subkey: "Software\Classes\WPMVPlayer.AssocFile"; ValueType: string; ValueName: ""; ValueData: "WPMV Media File"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\WPMVPlayer.AssocFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\WPMV_Player.exe,0"; Tasks: fileassoc
Root: HKA; Subkey: "Software\Classes\WPMVPlayer.AssocFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\WPMV_Player.exe"" ""%1"""; Tasks: fileassoc

[Code]
// Hàm kiểm tra K-Lite Codec Pack đã có trong hệ thống chưa
function IsKLiteInstalled: Boolean;
begin
Result := RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\KLiteCodecPack') or
RegKeyExists(HKEY_CURRENT_USER, 'SOFTWARE\KLiteCodecPack') or
RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\WOW6432Node\KLiteCodecPack');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
ResultCode: Integer;
begin
if CurStep = ssPostInstall then
begin
if not IsKLiteInstalled then
begin
if MsgBox('Hệ thống chưa có K-Lite Codec Pack để hỗ trợ giải mã video tốt nhất. Bạn có muốn cài đặt ngay không?', mbConfirmation, MB_YESNO) = IDYES then
begin
// Thực thi trình cài đặt K-Lite từ thư mục tạm
if not Exec(ExpandConstant('{tmp}\K-Lite_Codec_Pack_Standard.exe'), '/verysilent /norestart', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
begin
MsgBox('Không thể khởi chạy trình cài đặt K-Lite: ' + SysErrorMessage(ResultCode), mbError, MB_OK);
end;
end;
end;
end;
end;
