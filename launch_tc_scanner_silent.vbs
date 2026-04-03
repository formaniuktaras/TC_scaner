Option Explicit

Dim fso, shell, scriptDir, targetDir
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
targetDir = NormalizeTargetDir(GetArgumentOrEmpty(0), shell.CurrentDirectory)

If LaunchExecutable(scriptDir, targetDir) Then
  WScript.Quit 0
End If

If LaunchWithWindowedPython(scriptDir, targetDir) Then
  WScript.Quit 0
End If

ShowError "Не знайдено GUI launcher для TC Scanner." & vbCrLf & _
          "Очікується один із варіантів:" & vbCrLf & _
          "1) TC_Scanner.exe у папці проєкту" & vbCrLf & _
          "2) pythonw.exe або pyw.exe + launch_tc_scanner.pyw"
WScript.Quit 1

Function GetArgumentOrEmpty(ByVal index)
  If WScript.Arguments.Count > index Then
    GetArgumentOrEmpty = CStr(WScript.Arguments(index))
  Else
    GetArgumentOrEmpty = ""
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

  value = Replace(value, "/", "\")

  If Len(value) > 3 Then
    Do While Right(value, 1) = "\"
      value = Left(value, Len(value) - 1)
      If Len(value) <= 3 Then Exit Do
    Loop
  End If

  If Len(value) = 0 Then
    value = CStr(defaultDir)
  End If

  NormalizeTargetDir = value
End Function

Function LaunchExecutable(ByVal baseDir, ByVal targetPath)
  Dim candidates, i, exePath, cmd
  candidates = Array( _
    fso.BuildPath(baseDir, "TC_Scanner.exe"), _
    fso.BuildPath(baseDir, "dist\TC_Scanner\TC_Scanner.exe") _
  )

  For i = 0 To UBound(candidates)
    exePath = candidates(i)
    If fso.FileExists(exePath) Then
      cmd = Quote(exePath) & " " & Quote(targetPath)
      On Error Resume Next
      shell.Run cmd, 0, False
      LaunchExecutable = (Err.Number = 0)
      Err.Clear
      On Error GoTo 0
      If LaunchExecutable Then Exit Function
    End If
  Next

  LaunchExecutable = False
End Function

Function LaunchWithWindowedPython(ByVal baseDir, ByVal targetPath)
  Dim launcherScript, runtimes, i, cmd, runtimePath

  launcherScript = fso.BuildPath(baseDir, "launch_tc_scanner.pyw")
  If Not fso.FileExists(launcherScript) Then
    LaunchWithWindowedPython = False
    Exit Function
  End If

  runtimes = WindowedPythonCandidates()
  For i = 0 To UBound(runtimes)
    runtimePath = runtimes(i)
    If IsUsableExecutable(runtimePath) Then
      cmd = Quote(runtimePath) & " " & Quote(launcherScript) & " " & Quote(targetPath)
      On Error Resume Next
      shell.Run cmd, 0, False
      If Err.Number = 0 Then
        LaunchWithWindowedPython = True
        Exit Function
      End If
      Err.Clear
      On Error GoTo 0
    End If
  Next

  LaunchWithWindowedPython = False
End Function

Function WindowedPythonCandidates()
  Dim items
  items = Array( _
    FindInPath("pythonw.exe"), _
    FindInPath("pyw.exe"), _
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
    shell.ExpandEnvironmentStrings("%LocalAppData%") & "\Programs\Python\Python310\pythonw.exe", _
    shell.ExpandEnvironmentStrings("%SystemRoot%") & "\pyw.exe" _
  )
  WindowedPythonCandidates = items
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
