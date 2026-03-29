# TC_scaner

Надійний Tkinter-лаунчер для щоденного сканування з Total Commander із повноцінною **структурованою системою конфігурації**.

## Нова архітектура конфігурації

Конфіг тепер має секції:
- `scan`
- `paths`
- `behavior`
- `naming`
- `ui`
- `ui_state`
- `doc_types`

### Модулі
- `app_config.py` — dataclass-модель конфігу, load/save, міграція legacy, валідація.
- `naming_utils.py` — рендер і нормалізація імені файлу.
- `scan_runtime.py` — збірка scan command, policy шляхів, temp→move, duplicate handling.
- `tc_scanner_launcher.py` — UI/координація сценарію сканування.

## Головне вікно (новий UX-сценарій)

Головне вікно тепер побудовано як послідовність 4 кроків:
1. **Що скануємо** — список типів документів (Listbox).
2. **Контекст** — вибір **Служби** кнопками та короткий стан (дата/епізод/секція).
3. **Результат** — редагована назва файлу + прев’ю лише у форматі `Файл: <ім’я>.pdf`.
4. **Дія** — акцентна кнопка **Сканувати**, а також **Налаштування** і **Вихід**.

Додатково:
- dropdown для тегів у головному сценарії прибрано, вибір служби виконується кнопками;
- повний шлях до файлу не показується в головному вікні (тільки ім’я файлу);
- постійний статусний рядок внизу показує короткі стани/попередження (`Готово до сканування`, `Сканування...`, `Перенесення файлу...`, `Файл збережено`, тощо).

## Simple vs Advanced settings

### Simple mode
Швидке редагування критичних полів:
- scan: `driver`, `device`, `dpi`, `page_size`, `bitdepth`, `output_extension`
- paths: `temp_dir`, `log_file`
- behavior: `duplicate_strategy`, `allow_incomplete_context`
- naming: `replace_spaces`, `max_length`
- ui: `remember_last_doc_type`, `remember_last_tag`, `focus_name_on_start`

### Advanced mode
Повний контроль:
- `command_template`
- `network_prefixes`, `force_temp_for_network`
- `status_warnings_only`, `log_parse_warnings`
- `minimal_template`
- `doc_types` editor
- `ui.mode`

## Backward compatibility

Підтримується авто-міграція legacy flat config:
- `scan_command` → `scan.command_template`
- `output_extension` → `scan.output_extension`
- `temp_dir`, `log_file` → `paths.*`
- `duplicate_strategy` → `behavior.duplicate_strategy`
- `ui_state`, `doc_types` зберігаються

Якщо файл `scanner_config.json` відсутній — він створюється з дефолтами.

## Приклад повного `scanner_config.json`

```json
{
  "scan": {
    "command_template": "C:\\PROGRA~1\\NAPS2\\NAPS2.Console.exe --noprofile --driver {driver} --device \"{device}\" --pagesize {page_size} --dpi {dpi} --bitdepth {bitdepth} -o \"{output_path}\" --force",
    "driver": "twain",
    "device": "Pantum",
    "dpi": 300,
    "page_size": "a4",
    "bitdepth": "gray",
    "output_extension": "pdf"
  },
  "paths": {
    "temp_dir": "tmp_scans",
    "log_file": "scan_log.csv",
    "force_temp_for_network": true,
    "network_prefixes": ["G:\\"]
  },
  "behavior": {
    "duplicate_strategy": "ask",
    "allow_incomplete_context": true,
    "status_warnings_only": true,
    "log_parse_warnings": true
  },
  "naming": {
    "fallback_if_empty": true,
    "replace_spaces": "_",
    "max_length": 180,
    "trim_extra_separators": true,
    "minimal_template": "{code}_{label}"
  },
  "ui": {
    "remember_last_doc_type": true,
    "remember_last_tag": true,
    "focus_name_on_start": true,
    "show_status_bar": true,
    "mode": "simple"
  },
  "ui_state": {
    "last_doc_type": "as",
    "last_tag": ""
  },
  "doc_types": []
}
```

## Типові сценарії
- Змінити драйвер/пристрій/DPI без редагування JSON.
- Увімкнути temp→move для мережевих шляхів (`G:\`).
- Налаштувати fallback-іменування і max length.
- Оновити `command_template` у advanced режимі.

## Тести

```bash
python -m pytest -q
```
