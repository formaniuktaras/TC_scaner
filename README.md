# TC_scaner

Надійний Tkinter-лаунчер для щоденного сканування з Total Commander.

## Що реалізовано

- **Temp scan → move**: зовнішній сканер пише у тимчасовий PDF (`temp_dir`), далі файл валідується і переноситься у фінальну папку.
- **Duplicate strategy** (`duplicate_strategy`):
  - `ask` — Yes=overwrite, No=increment, Cancel=cancelled;
  - `overwrite` — перезапис;
  - `increment` — `file.pdf`, `file (2).pdf`, `file (3).pdf`.
- **CSV лог** (`log_file`): `success`, `error`, `cancelled`, `parse_warning`.
- **UI state** (`ui_state`): відновлення останніх `doc_type` і `tag` між запусками.
- **UX**:
  - Enter = Сканувати
  - Esc = Вихід
  - Ctrl+L = очистити поле назви
  - автофокус у полі "Назва файлу"
  - status bar: `Готово`, `Сканування...`, `Перенесення файлу...`, `Помилка: ...`, `Скасовано`
- **Парсер папок менш крихкий**: `split("_")`, підтримка `2осб`, `1єб`, `3рв`, частковий контекст без падіння.
- **Валідація перед сканом** з конкретними повідомленнями:
  - `Не знайдено дату справи в назві папки`
  - `Не знайдено епізод у назві папки`
  - `Не знайдено підрозділ у суфіксі папки`
  - `Не знайдено секцію 01_...`
- **Валідація doc_types template** у налаштуваннях.
- **Backward compatibility**: старі конфіги працюють, відсутні ключі доповнюються дефолтами.
- **Реальний текст помилок сканера**: stderr/stdout додається в popup і лог.

## Ключі конфігурації

```json
{
  "scan_command": "C:\\PROGRA~1\\NAPS2\\NAPS2.Console.exe ... -o \"{output_path}\" --force",
  "output_extension": "pdf",
  "duplicate_strategy": "ask",
  "temp_dir": "tmp_scans",
  "log_file": "scan_log.csv",
  "ui_state": {
    "last_doc_type": "as",
    "last_tag": "СЗ"
  },
  "doc_types": []
}
```

### Дозволені placeholders у `template`

- `{code}`
- `{label}`
- `{date}`
- `{episode}`
- `{section}`
- `{tag}`

## Ручна перевірка (нові сценарії)

1. **Success**: скан успішний, статуси `Сканування...` → `Перенесення файлу...` → `Готово`, у лог `success`.
2. **Duplicate overwrite**: при `overwrite` файл перезаписується.
3. **Duplicate increment**: при `increment` створюється `file (2).pdf`, `file (3).pdf`.
4. **Cancel**: при `ask` + Cancel — скан не стартує, статус `Скасовано`, у лог `cancelled`.
5. **Scan failure**: зламана команда/сканер повертає код ≠ 0 — показується реальний stderr.
6. **Move failure**: неможливо перемістити temp → final — конкретна помилка, запис у `error`.
7. **Parse failure**: крива папка не валить GUI, формується `parse_warning`.
8. **Old config compatibility**: старий `scanner_config.json` без нових полів запускається без падіння.

## Тести

```bash
python -m pytest -q
```
