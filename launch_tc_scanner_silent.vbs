Option Explicit

Dim fso, shell, scriptDir, targetDir, launcherScript
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
targetDir = NormalizeTargetDir(GetArgumentOrEmpty(0), shell.CurrentDirectory)
launcherScript = ResolveLauncherScript(scriptDir)

If Not fso.FileExists(launcherScript) Then
  ShowError "Не знайдено launcher script:" & vbCrLf & launcherScript
  WScript.Quit 1
End If

If LaunchWithPythonw(launcherScript, targetDir) Then
  WScript.Quit 0
End If

If LaunchWithFallbackConsolePython(launcherScript, targetDir) Then
  WScript.Quit 0
End If

ShowError "Python не знайдено." & vbCrLf & _
          "Встановіть Python 3.10+ (з pythonw.exe або py.exe)."
WScript.Quit 1

Function GetArgumentOrEmpty(ByVal index)
  If WScript.Arguments.Count > index Then
    GetArgumentOrEmpty = CStr(WScript.Arguments(index))
  Else
    GetArgumentOrEmpty = ""
  End If
End Function

Function ResolveLauncherScript(ByVal baseDir)
  Dim pywPath, pyPath
  pywPath = fso.BuildPath(baseDir, "launch_tc_scanner.pyw")
  pyPath = fso.BuildPath(baseDir, "tc_scanner_launcher.py")
  If fso.FileExists(pywPath) Then
    ResolveLauncherScript = pywPath
  Else
    ResolveLauncherScript = pyPath
  End If
End Function

Function NormalizeTargetDir(ByVal rawValue, ByVal defaultDir)
  Dim value
  value = CStr(rawValue)
  value = Trim(value)

  If Len(value) = 0 Then
    value = CStr(defaultDir)
  End If

  Do While Len(value) >= 2 And Left(value, 1) = Chr(34) And Right(value, 1) = Chr(34)
    value = Mid(value, 2, Len(value) - 2)
    value = Trim(value)
  Loop

  Do While Len(value) > 0 And Left(value, 1) = Chr(34)
    value = Mid(value, 2)
    value = Trim(value)
  Loop

  Do While Len(value) > 0 And Right(value, 1) = Chr(34)
    value = Left(value, Len(value) - 1)
    value = Trim(value)
  Loop

  If Len(value) > 3 Then
    Do While Right(value, 1) = "\" Or Right(value, 1) = "/"
      value = Left(value, Len(value) - 1)
      If Len(value) <= 3 Then Exit Do
    Loop
  End If

  value = Replace(value, "/", "\")

  If Len(value) = 0 Then
    value = CStr(defaultDir)
  End If

  NormalizeTargetDir = value
End Function

Function LaunchWithPythonw(ByVal scriptPath, ByVal targetPath)
  Dim candidates, i, cmd, exePath
  candidates = PythonwCandidates()

  For i = 0 To UBound(candidates)
    exePath = candidates(i)
    If IsUsableExecutable(exePath) Then
      cmd = Quote(exePath) & " " & Quote(scriptPath) & " " & Quote(targetPath)
      On Error Resume Next
      shell.Run cmd, 0, False
      If Err.Number = 0 Then
        LaunchWithPythonw = True
        Exit Function
      End If
      Err.Clear
      On Error GoTo 0
    End If
  Next

  LaunchWithPythonw = False
End Function

Function LaunchWithFallbackConsolePython(ByVal scriptPath, ByVal targetPath)
  Dim candidates, i, cmd, exePath
  candidates = ConsolePythonCandidates()

  For i = 0 To UBound(candidates)
    exePath = candidates(i)
    If IsUsableExecutable(exePath) Then
      cmd = Quote(exePath) & " " & Quote(scriptPath) & " " & Quote(targetPath)
      On Error Resume Next
      shell.Run cmd, 0, False
      If Err.Number = 0 Then
        LaunchWithFallbackConsolePython = True
        Exit Function
      End If
      Err.Clear
      On Error GoTo 0
    End If
  Next

  LaunchWithFallbackConsolePython = False
End Function

Function PythonwCandidates()
  Dim items
  items = Array( _
    FindInPath("pythonw.exe"), _
    ReadRegSafe("HKCU\Software\Python\PythonCore\3.13\InstallPath\WindowedExecutablePath"), _
    ReadRegSafe("HKCU\Software\Python\PythonCore\3.12\InstallPath\WindowedExecutablePath"), _
    ReadRegSafe("HKCU\Software\Python\PythonCore\3.11\InstallPath\WindowedExecutablePath"), _
    ReadRegSafe("HKCU\Software\Python\PythonCore\3.10\InstallPath\WindowedExecutablePath"), _
    ReadRegSafe("HKLM\Software\Python\PythonCore\3.13\InstallPath\WindowedExecutablePath"), _
    ReadRegSafe("HKLM\Software\Python\PythonCore\3.12\InstallPath\WindowedExecutablePath"), _
    ReadRegSafe("HKLM\Software\Python\PythonCore\3.11\InstallPath\WindowedExecutablePath"), _
    ReadRegSafe("HKLM\Software\Python\PythonCore\3.10\InstallPath\WindowedExecutablePath"), _
    shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python313\pythonw.exe", _
    shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python312\pythonw.exe", _
    shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python311\pythonw.exe", _
    shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python310\pythonw.exe" _
  )
  PythonwCandidates = items
End Function

Function ConsolePythonCandidates()
  Dim items
  items = Array( _
    FindInPath("py.exe"), _
    shell.ExpandEnvironmentStrings("%SystemRoot%") & "\py.exe", _
    shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Launcher\py.exe", _
    FindInPath("python.exe"), _
    ReadRegSafe("HKCU\Software\Python\PythonCore\3.13\InstallPath\ExecutablePath"), _
    ReadRegSafe("HKCU\Software\Python\PythonCore\3.12\InstallPath\ExecutablePath"), _
    ReadRegSafe("HKCU\Software\Python\PythonCore\3.11\InstallPath\ExecutablePath"), _
    ReadRegSafe("HKCU\Software\Python\PythonCore\3.10\InstallPath\ExecutablePath"), _
    ReadRegSafe("HKLM\Software\Python\PythonCore\3.13\InstallPath\ExecutablePath"), _
    ReadRegSafe("HKLM\Software\Python\PythonCore\3.12\InstallPath\ExecutablePath"), _
    ReadRegSafe("HKLM\Software\Python\PythonCore\3.11\InstallPath\ExecutablePath"), _
    ReadRegSafe("HKLM\Software\Python\PythonCore\3.10\InstallPath\ExecutablePath") _
  )
  ConsolePythonCandidates = items
End Function

Function FindInPath(ByVal exeName)
  Dim pathValue, parts, i, candidate
  pathValue = shell.Environment("PROCESS")("PATH")
  parts = Split(pathValue, ";")

  For i = 0 To UBound(parts)
    candidate = Trim(parts(i))
    If Len(candidate) > 0 Then
      If Right(candidate, 1) = "\" Then
        candidate = candidate & exeName
      Else
        candidate = candidate & "\" & exeName
      End If
      If fso.FileExists(candidate) Then
        FindInPath = candidate
        Exit Function
      End If
    End If
  Next

  FindInPath = ""
End Function

Function ReadRegSafe(ByVal regPath)
  On Error Resume Next
  ReadRegSafe = shell.RegRead(regPath)
  If Err.Number <> 0 Then
    ReadRegSafe = ""
    Err.Clear
  End If
  On Error GoTo 0
End Function

Function IsUsableExecutable(ByVal exePath)
  If Len(exePath) = 0 Then
    IsUsableExecutable = False
    Exit Function
  End If
  IsUsableExecutable = fso.FileExists(exePath)
End Function

Function Quote(ByVal value)
  Quote = Chr(34) & value & Chr(34)
End Function

Sub ShowError(ByVal message)
  MsgBox "[TC_SCANER] " & message, vbCritical + vbOKOnly, "TC Scanner"
End Sub
