Option Explicit

Dim fso, shell, scriptDir, targetDir, launcherCmd, quotedScript, quotedTarget, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
targetDir = ""

If WScript.Arguments.Count > 0 Then
  targetDir = WScript.Arguments(0)
End If

If Len(targetDir) = 0 Then
  targetDir = shell.CurrentDirectory
End If

' remove accidental wrapping quotes if they arrived from caller
If Len(targetDir) >= 2 Then
  If Left(targetDir, 1) = Chr(34) And Right(targetDir, 1) = Chr(34) Then
    targetDir = Mid(targetDir, 2, Len(targetDir) - 2)
  End If
End If

'trailing backslash before a closing quote can produce a literal quote in TC argument
If Right(targetDir, 1) = Chr(34) Then
  targetDir = Left(targetDir, Len(targetDir) - 1)
End If

quotedScript = Chr(34) & fso.BuildPath(scriptDir, "tc_scanner_launcher.py") & Chr(34)
quotedTarget = Chr(34) & targetDir & Chr(34)

launcherCmd = ""
On Error Resume Next
launcherCmd = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\py.exe"
If Not fso.FileExists(launcherCmd) Then launcherCmd = ""
On Error GoTo 0

If Len(launcherCmd) > 0 Then
  cmd = Chr(34) & launcherCmd & Chr(34) & " -3 " & quotedScript & " " & quotedTarget
  shell.Run cmd, 0, False
  WScript.Quit 0
End If

launcherCmd = ""
On Error Resume Next
launcherCmd = shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Launcher\py.exe"
If Not fso.FileExists(launcherCmd) Then launcherCmd = ""
On Error GoTo 0

If Len(launcherCmd) > 0 Then
  cmd = Chr(34) & launcherCmd & Chr(34) & " -3 " & quotedScript & " " & quotedTarget
  shell.Run cmd, 0, False
  WScript.Quit 0
End If

launcherCmd = ""
On Error Resume Next
launcherCmd = shell.RegRead("HKCU\Software\Python\PythonCore\3.11\InstallPath\WindowedExecutablePath")
If Len(launcherCmd) = 0 Then
  launcherCmd = shell.RegRead("HKCU\Software\Python\PythonCore\3.10\InstallPath\WindowedExecutablePath")
End If
On Error GoTo 0

If Len(launcherCmd) > 0 And fso.FileExists(launcherCmd) Then
  cmd = Chr(34) & launcherCmd & Chr(34) & " " & quotedScript & " " & quotedTarget
  shell.Run cmd, 0, False
  WScript.Quit 0
End If

MsgBox "[TC_SCANER] Python launcher was not found." & vbCrLf & _
       "Install Python 3.10+ and ensure py.exe is available.", _
       vbCritical + vbOKOnly, "TC Scanner"
WScript.Quit 1
