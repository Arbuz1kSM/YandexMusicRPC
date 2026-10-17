Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!ifndef APP_VERSION
!define APP_VERSION "1.0.0"
!endif
!ifndef BUNDLE_DIR
!error "Pass BUNDLE_DIR (absolute path to the prepared Windows application folder)"
!endif
!ifndef OUTPUT_FILE
!define OUTPUT_FILE "..\installer-output\YandexMusicRPC-Setup.exe"
!endif
Name "Yandex Music RPC"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\Yandex Music RPC"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 32
SetDatablockOptimize on
ShowInstDetails show
ShowUninstDetails show
BrandingText "Yandex Music RPC ${APP_VERSION}"
Icon "app.ico"
UninstallIcon "app.ico"
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "Yandex Music RPC"
VIAddVersionKey "CompanyName" "Arbuz1k_SM"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "FileDescription" "Yandex Music RPC Setup"
VIAddVersionKey "LegalCopyright" "Arbuz1k_SM"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\YandexMusicRPC.exe"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "This application requires 64-bit Windows."
    Abort
  ${EndIf}
  SetShellVarContext current
  SetRegView 64
FunctionEnd

Section "Yandex Music RPC"
  SetOutPath "$INSTDIR"
  File /r "${BUNDLE_DIR}\*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\Yandex Music RPC"
  CreateShortcut "$SMPROGRAMS\Yandex Music RPC\Yandex Music RPC.lnk" "$INSTDIR\YandexMusicRPC.exe"
  CreateShortcut "$SMPROGRAMS\Yandex Music RPC\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\Yandex Music RPC.lnk" "$INSTDIR\YandexMusicRPC.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "DisplayName" "Yandex Music RPC"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "Publisher" "Arbuz1k_SM"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "DisplayIcon" "$INSTDIR\YandexMusicRPC.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "QuietUninstallString" '$\"$INSTDIR\Uninstall.exe$\" /S'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "URLInfoAbout" "https://github.com/Arbuz1kSM/YandexMusicRPC"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  SetRegView 64
  Delete "$DESKTOP\Yandex Music RPC.lnk"
  Delete "$SMPROGRAMS\Yandex Music RPC\Yandex Music RPC.lnk"
  Delete "$SMPROGRAMS\Yandex Music RPC\Uninstall.lnk"
  RMDir "$SMPROGRAMS\Yandex Music RPC"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\{9B9A8481-50CE-4BB1-A136-66E26215AC6E}_is1"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "ArbuzYandexMusicRPC"
  RMDir /r "$INSTDIR\app"
  RMDir /r "$INSTDIR\runtime"
  Delete "$INSTDIR\YandexMusicRPC.exe"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\THIRD_PARTY_NOTICES.md"
  Delete "$INSTDIR\BUILD-INFO.json"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
