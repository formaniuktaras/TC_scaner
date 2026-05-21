# TC_scaner

TC_scaner — Tkinter-лаунчер для керування скануванням через NAPS2.

## Чому був потрібен fix для PyInstaller

У frozen-збірках (`PyInstaller`) writable runtime-дані не можна прив'язувати до шляху модуля (`__file__`) або до тимчасового каталогу розпакування (`_MEIPASS` у `onefile`).

Тому в проєкті використовується **єдина стабільна база шляху**:

- frozen mode: папка поруч з `TC_Scanner.exe`;
- script mode: папка проєкту.

Саме в цій папці живуть runtime writable дані:

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

## Перевірка build-середовища (debug)

Перед збіркою можна перевірити середовище:

```bat
check_build_env.cmd
```

Скрипт покаже:

- `where py`
- `py --version`
- `py -m PyInstaller --version`
- поточну робочу папку
- наявність `TC_Scanner.spec`
- наявність `launch_tc_scanner.pyw`
- наявність `scanner_config.default.json`

## Збірка Windows GUI EXE (основний сценарій = onedir)

Команда збірки:

```bat
build_tc_scanner.cmd
```

`build_tc_scanner.cmd` робить наступне:

1. Показує діагностику середовища:
   - `where py`
   - `py --version`
   - `py -m PyInstaller --version`
   - поточну папку.
2. Очищає тільки релевантні артефакти:
   - `build\`
   - `dist\TC_Scanner\`
3. Запускає збірку через надійний виклик:
   - `py -m PyInstaller --noconfirm --clean "TC_Scanner.spec"`
4. Логує повний вивід у:
   - `build_pyinstaller.log`
5. Виконує post-build validation:
   - обов'язково перевіряє `dist\TC_Scanner\TC_Scanner.exe`
   - додатково повідомляє про `dist\TC_Scanner\scanner_config.default.json`.

### Що вважається успішною збіркою

Успіх — коли після завершення є файл:

- `dist\TC_Scanner\TC_Scanner.exe`

і скрипт явно виводить `Build SUCCESS` + точний шлях до `.exe`.

### Якщо `dist` порожня

Це означає, що build **провалився** (а не "файл десь сховався").

Перевірте лог:

- `build_pyinstaller.log`

Скрипт завершиться з помилкою та явним повідомленням `Build FAILED`.

## Де будуть runtime-файли після запуску EXE

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
