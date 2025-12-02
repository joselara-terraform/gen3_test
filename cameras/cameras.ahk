#Requires AutoHotkey v2.0

Sleep 6000    ; give VLC more time

; Only get real VLC video windows
winList := WinGetList("VLC media player ahk_exe vlc.exe")

if (winList.Length = 0) {
    MsgBox "No VLC video windows found."
    ExitApp
}

; ----- GRID CONFIG -----
; 4 columns x 4 rows (up to 16 slots, your 4 streams will fill the first 4)
cols := 4
rows := 4

screenW := A_ScreenWidth
screenH := A_ScreenHeight

tileW := screenW // cols
tileH := screenH // rows

positions := []
Loop rows {
    r := A_Index - 1
    Loop cols {
        c := A_Index - 1
        positions.Push(Map(
            "x", c * tileW,
            "y", r * tileH,
            "w", tileW,
            "h", tileH
        ))
    }
}

Loop winList.Length {
    idx := A_Index
    if (idx > positions.Length)
        break

    hwnd := winList[idx]

    if !WinExist("ahk_id " hwnd)
        continue

    ; Skip minimized/zero-size windows
    if (WinGetMinMax("ahk_id " hwnd) = -1)
        continue

    rect := WinGetPos("ahk_id " hwnd)
    if (rect[2] < 100 or rect[3] < 100)
        continue

    p := positions[idx]

    WinRestore("ahk_id " hwnd)
    WinMove("ahk_id " hwnd, p["x"], p["y"], p["w"], p["h"])
}

ExitApp
