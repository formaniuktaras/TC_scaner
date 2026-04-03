# TC_scaner

TC_scaner — Tkinter-лаунчер для керування скануванням через NAPS2.

## Canonical GUI-only запуск

Пріоритет запуску для Total Commander:

1. **`TC_Scanner.exe`** (windowed build, без консолі).
2. **`wscript.exe + launch_tc_scanner_silent.vbs`** (fallback, теж без консолі).
3. **`launch_tc_scanner.cmd`** — shim, який делегує у `wscript.exe + launch_tc_scanner_silent.vbs` (без постійної консолі).

`launch_tc_scanner_silent.vbs` запускає **лише GUI-safe** варіанти:
- `TC_Scanner.exe` у папці проєкту (пріоритет №1);
- `launch_tc_scanner.pyw` через `pythonw.exe` або `pyw.exe` (пріоритет №2);
- якщо GUI runtime відсутній — показується `MsgBox` з поясненням.

> Важливо: у silent launcher **немає** fallback на `python.exe` / `py.exe`, щоб не з'являлось console window.

## Команди для кнопки Total Commander

### Preferred (exe)

- **Command:** `D:\PATH\TO\TC_scaner\dist\TC_Scanner.exe`
- **Parameters:** `"%P"`

Одним рядком:

```text
"D:\PATH\TO\TC_scaner\dist\TC_Scanner.exe" "%P"
```

### Fallback (VBS)

- **Command:** `wscript.exe`
- **Parameters:** `//nologo "D:\PATH\TO\TC_scaner\launch_tc_scanner_silent.vbs" "%P"`

Одним рядком:

```text
wscript.exe //nologo "D:\PATH\TO\TC_scaner\launch_tc_scanner_silent.vbs" "%P"
```

## Build windowed exe (`TC_Scanner.exe`)

```bat
build_tc_scanner.cmd
```

Скрипт викликає PyInstaller з `--windowed --onefile --name TC_Scanner`.
Результат: `dist\TC_Scanner.exe`.

## Frozen / script mode paths

Для стабільної роботи в script і frozen режимах використовується спільний helper:

- у frozen (`sys.frozen=True`) база = папка `sys.executable`;
- у script mode база = папка python-файлів.

Тому runtime-файли працюють стабільно в обох режимах:

- `scanner_config.json`;
- `scan_log.csv`;
- `tmp_scans`.

## Тести

```bash
python -m pytest -q
```
