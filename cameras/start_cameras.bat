@echo off

call cameras.bat

timeout /t 6 >nul

"C:\Program Files\AutoHotkey\AutoHotkeyUX.exe" "C:\Users\terra\Desktop\gen3_test\cameras\cameras.ahk"
