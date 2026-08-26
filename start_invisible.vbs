Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\erson\Downloads\insta cli"
WshShell.Run """C:\Users\erson\AppData\Local\Programs\Python\Python311\python.exe"" server.py", 0, False
