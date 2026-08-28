' This is what the Desktop shortcut actually runs -- launches the
' dashboard with no visible terminal window. See launch_dashboard.ps1
' (same folder) for the real logic.
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
psScript = scriptDir & "\launch_dashboard.ps1"

Set shell = CreateObject("WScript.Shell")
shell.Run "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & psScript & """", 0, False
