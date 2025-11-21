@echo off
setlocal

rem --- Run the camera launcher batch that lives in the same folder as this file ---
call "%~dp0cameras.bat"

rem --- Wait a bit so all VLC windows actually open ---
timeout /t 6 /nobreak >nul

rem --- Run the AutoHotkey script that lives in the same folder as this file ---
"C:\Program Files\AutoHotkey\AutoHotkeyUX.exe" "%~dp0cameras.ahk"

endlocal