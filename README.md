# TC_scaner

TC_scaner — Tkinter-лаунчер для керування скануванням через NAPS2.

## Чому був потрібен fix для PyInstaller

У frozen-збірках (`PyInstaller`) writable runtime-дані не можна прив'язувати до шляху модуля (`__file__`) або до тимчасового каталогу розпакування (`_MEIPASS` у `onefile`).

Тому в проєкті використовується **єдина стабільна база шляху**:

- frozen mode: папка поруч з `TC_Scanner.exe`;
- script mode: папка проєкту.

Саме в цій папці тепер живуть runtime writable дані:

- `scanner_config.json`;
- `scan_log.csv`;
- `tmp_scans/`.

## Canonical GUI-only запуск

Пріоритет запуску для Total Commander:

1. **`TC_Scanner.exe`** (windowed build, без консолі).
2. **`wscript.exe + launch_tc_scanner_silent.vbs`** (fallback, теж без консолі).
3. **`launch_tc_scanner.cmd`** — shim, який делегує у `wscript.exe + launch_tc_scanner_silent.vbs`.

`launch_tc_scanner_silent.vbs` запускає лише GUI-safe варіанти:

- `TC_Scanner.exe` (у поточній папці або `dist\TC_Scanner\TC_Scanner.exe`);
- `launch_tc_scanner.pyw` через `pythonw.exe` або `pyw.exe`.

> Немає fallback на `python.exe` / `py.exe`, щоб не з'являлась консоль.

## Збірка Windows GUI EXE (основний сценарій = onedir)

```bat
build_tc_scanner.cmd
```

Скрипт викликає:

```bat
pyinstaller --noconfirm --clean TC_Scanner.spec
```

- `console=False` (GUI-only, без консолі)
- `name=TC_Scanner`
- основний формат: **onedir**

Результат:

- `dist\TC_Scanner\TC_Scanner.exe`

## Де будуть runtime-файли

Після першого запуску `dist\TC_Scanner\TC_Scanner.exe`:

- `dist\TC_Scanner\scanner_config.json` — створюється автоматично (із `scanner_config.default.json` або вбудованих дефолтів);
- `dist\TC_Scanner\scan_log.csv` — створюється автоматично при першому записі;
- `dist\TC_Scanner\tmp_scans\` — створюється автоматично при першій потребі.

Це зроблено навмисно: користувач бачить і контролює config/log/tmp поруч із застосунком.

## Команди для кнопки Total Commander

### Preferred (exe)

```text
"D:\PATH\TO\TC_scaner\dist\TC_Scanner\TC_Scanner.exe" "%P"
```

### Fallback (VBS)

```text
wscript.exe //nologo "D:\PATH\TO\TC_scaner\launch_tc_scanner_silent.vbs" "%P"
```

## Тести

```bash
python -m pytest -q
```
