Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\terra\Desktop\gen3_test"
WshShell.Run "cmd /c call venv\Scripts\activate.bat && pythonw.exe MK1_AWE\gui\app.py", 0