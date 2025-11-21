#Requires AutoHotkey v2.0

; Wait for VLC windows to appear
Sleep 5000

; Get all VLC windows
winList := WinGetList("ahk_exe vlc.exe")

if (winList.Length = 0) {
    MsgBox "No VLC windows found."
    ExitApp
}

; ----- GRID CONFIG -----
; 3 columns x 2 rows (for 6 cameras)

cols := 3
rows := 2

screenW := A_ScreenWidth
screenH := A_ScreenHeight

tileW := screenW // cols
tileH := screenH // rows

; Generate positions for each grid slot
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

; Move each VLC window
Loop winList.Length {
    idx := A_Index
    if (idx > positions.Length)
        break

    hwnd := winList[idx]
    p := positions[idx]

    WinRestore(hwnd)
    WinMove(hwnd, p.x, p.y, p.w, p.h)
}

ExitApp
