# TC_scaner

TC_scaner — Tkinter-лаунчер для керування скануванням через NAPS2 із temp→move workflow, логуванням і duplicate-strategy.

## Модель сканування (нова)

Підтримуються **два режими**:

1. **Profile mode (рекомендований)**
   - TC_scaner запускає `NAPS2.Console.exe -p "<profile>" -o "<output>"`.
   - ADF/duplex/blank pages/alignment/post-processing налаштовуються в NAPS2-профілі.
   - TC_scaner не дублює GUI-логіку NAPS2, а керує файлами/логами/UX.

2. **Manual mode (fallback)**
   - TC_scaner будує CLI з `driver/device/dpi/page_size/bitdepth`.
   - Потрібний для технічних сценаріїв або коли профілі не використовуються.

## Конфігурація

Секція `scan` підтримує поля:
- `mode`: `profile | manual`
- `naps2_exe`
- `profile_name`
- `command_template` (необов’язково; якщо порожній, команда збирається автоматично)
- `driver`, `device`, `dpi`, `page_size`, `bitdepth`
- `output_extension`
- `multi_page`
- `force_overwrite_flag`

### Приклад `scanner_config.json`

```json
{
  "scan": {
    "mode": "profile",
    "naps2_exe": "C:\\PROGRA~1\\NAPS2\\NAPS2.Console.exe",
    "profile_name": "DR",
    "command_template": "",
    "driver": "wia",
    "device": "CANON DR-C240 USB",
    "dpi": 300,
    "page_size": "a4",
    "bitdepth": "color",
    "output_extension": "pdf",
    "multi_page": true,
    "force_overwrite_flag": true
  }
}
```

## Команди сканування

- Profile mode (default builder):
  - `"{naps2_exe}" -p "{profile_name}" -o "{output_path}" [--force]`
- Manual mode (default builder):
  - `"{naps2_exe}" --noprofile --driver {driver} --device "{device}" --pagesize {page_size} --dpi {dpi} --bitdepth {bitdepth} -o "{output_path}" [--force]`

`--force` додається керовано через `scan.force_overwrite_flag`; duplicate strategy залишається у Python-шарі.

## Multi-page

- У **profile mode** multi-page визначається **профілем NAPS2** і сканером.
- `scan.multi_page` у profile mode — інформаційний прапорець / сумісність на майбутнє.
- TC_scaner не реалізує власний page manager.

## Налаштування UI

- **Simple mode**: режим сканування + релевантні поля (profile або manual).
- **Advanced mode**: `command_template`, `multi_page`, `force_overwrite_flag`, технічні поля, raw `doc_types`.
- Додано кнопку **«Перевірити NAPS2»**: перевіряє існування exe, базовий запуск `--help` і показує preview команди.
- У головному вікні показується короткий статус режиму:
  - `Режим сканування: профіль DR`
  - або `Режим сканування: ручний (WIA / 300 dpi)`

## Backward compatibility

Legacy flat config підтримано:
- `scan_command` → `scan.command_template`
- legacy конфіг автоматично мігрується в structured формат
- якщо знайдено legacy `scan_command`, режим виставляється в `manual`

## Тести

```bash
python -m pytest -q
```

Покрито:
- валідацію profile/manual конфігів
- legacy migration
- build_profile/build_manual/build_scan_command
- roundtrip save/load для обох режимів
- helper для режимного label у UI
