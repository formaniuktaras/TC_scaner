# TC_scaner

TC_scaner — Tkinter-лаунчер для керування скануванням через NAPS2.

## Безконсольний запуск з Total Commander

`.cmd` **не може бути** повністю безконсольним primary launcher, бо Windows створює консоль для batch-процесу. Тому для кнопки Total Commander треба використовувати саме `wscript.exe + launch_tc_scanner_silent.vbs`.

### Рекомендована конфігурація кнопки TC

- **Command:** `wscript.exe`
- **Parameters:** `"D:\PATH\TO\TC_scaner\launch_tc_scanner_silent.vbs" "%P"`

Готова команда (одним рядком):

```text
wscript.exe "D:\PATH\TO\TC_scaner\launch_tc_scanner_silent.vbs" "%P"
```

`launch_tc_scanner_silent.vbs`:
- коректно очищає зайві лапки в аргументі папки;
- обробляє пробіли/кирилицю в шляхах;
- чистить trailing quote/slash проблеми;
- намагається запуск через `pythonw.exe` (без консолі);
- fallback: `py.exe` / `python.exe`;
- за повної відсутності Python показує `MsgBox`, а не текст у консолі.

## Ролі launcher-файлів

- `launch_tc_scanner_silent.vbs` — **основний launcher для Total Commander**.
- `launch_tc_scanner.pyw` — windowed Python entry point (future-proof для `pythonw.exe`).
- `launch_tc_scanner.cmd` — debug launcher (консоль можлива, це нормально).

## Future-proof (опційно)

Для окремого exe можна зібрати windowed build:

```bash
pyinstaller --noconfirm --onefile --windowed tc_scanner_launcher.py
```

`--windowed` (`--noconsole`) прибирає консоль на рівні exe.

## Тести

```bash
python -m pytest -q
```
