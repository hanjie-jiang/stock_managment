' This is what the Desktop shortcut actually runs -- launches the
' dashboard with no visible terminal window. See scripts\launch_dashboard.ps1
' for the real logic.
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
psScript = scriptDir & "\scripts\launch_dashboard.ps1"

Set shell = CreateObject("WScript.Shell")
shell.Run "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & psScript & """", 0, False
