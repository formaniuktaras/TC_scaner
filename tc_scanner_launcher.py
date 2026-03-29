#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    INSERT,
    LEFT,
    RIGHT,
    Button,
    Entry,
    Frame,
    Label,
    Listbox,
    Menu,
    OptionMenu,
    StringVar,
    Text,
    Tk,
    Toplevel,
    messagebox,
)
from tkinter.scrolledtext import ScrolledText
from typing import Callable, Dict, List

CONFIG_PATH = Path(__file__).with_name("scanner_config.json")


@dataclass
class FolderContext:
    date: str = ""
    episode: str = ""
    tags: List[str] | None = None
    section: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {"date": self.date, "episode": self.episode, "section": self.section}


DEFAULT_CONFIG = {
    "scan_command": "",
    "output_extension": "pdf",
    "duplicate_strategy": "ask",
    "temp_dir": "tmp_scans",
    "log_file": "scan_log.csv",
    "ui_state": {
        "last_doc_type": "as",
        "last_tag": "",
    },
    "doc_types": [
        {"key": "vvzv", "label": "ВВЗВ", "code": "001", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {"key": "vvm", "label": "ВВМ", "code": "002", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {"key": "zalyshkova_vartist", "label": "Відомість залишкової вартості", "code": "003", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {"key": "yeas", "label": "ЄАС", "code": "004", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {"key": "as", "label": "АС", "code": "005", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {"key": "extract_losses", "label": "витяг з книги втрат", "code": "006", "template": "{code}_{section}_{label}_{date}_{episode}_{tag}"},
        {"key": "extract_shortages", "label": "витяг з книги нестач", "code": "007", "template": "{code}_{section}_{label}_{date}_{episode}_{tag}"},
        {"key": "order", "label": "Наказ", "code": "008", "template": "{code}_{label}_{date}_{episode}_{tag}"},
    ],
}

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{2}$")
SECTION_RE = re.compile(r"^(?P<section>\d{2})[_\s].+$")
PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")
ALLOWED_TEMPLATE_PLACEHOLDERS = {"code", "label", "date", "episode", "section", "tag"}
LOG_FIELDS = [
    "timestamp",
    "status",
    "current_folder",
    "document_key",
    "document_label",
    "selected_tag",
    "generated_filename",
    "temp_output_path",
    "final_output_path",
    "duplicate_strategy",
    "message",
]


def _normalize_scan_command(value: str) -> str:
    value = value.strip()
    value = value.replace(r'\\"{output_path}\\"', r'"{output_path}"')
    value = value.replace(r'\\"', r'\"')
    return value


def _clean_target_dir(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    value = value.replace('"', "")
    return value


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    merged_ui_state = dict(DEFAULT_CONFIG.get("ui_state", {}))
    merged_ui_state.update(cfg.get("ui_state", {}))
    merged["ui_state"] = merged_ui_state
    merged["scan_command"] = _normalize_scan_command(merged.get("scan_command", ""))
    return merged


def save_config(cfg: dict) -> None:
    cfg = dict(cfg)
    cfg["scan_command"] = _normalize_scan_command(cfg.get("scan_command", ""))
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


def sanitize_part(value: str) -> str:
    value = value.strip()
    value = re.sub(r'[\\/:*?"<>|]+', '-', value)
    value = re.sub(r'\s+', ' ', value)
    return value


def parse_context(folder: Path) -> FolderContext:
    tags: List[str] = []
    date = ""
    episode = ""
    section = ""

    for part in [folder] + list(folder.parents):
        parts = [p.strip() for p in part.name.split("_") if p.strip()]
        if len(parts) < 3:
            continue
        date_candidate = parts[1]
        episode_candidate = parts[2]
        date = date_candidate
        episode = episode_candidate
        if not DATE_RE.match(date):
            logging.warning("parse_warning: invalid date format in folder '%s': '%s'", part.name, date)

        last_part = parts[-1]
        if "+" in last_part:
            tags = [sanitize_part(x) for x in last_part.split("+") if x.strip()]
        else:
            tags = []
        break

    if not date or not episode:
        logging.warning("parse_warning: context not detected for folder '%s'", folder)

    for part in [folder] + list(folder.parents):
        section_match = SECTION_RE.match(part.name)
        if section_match:
            section = section_match.group("section")
            break

    return FolderContext(date=date, episode=episode, tags=tags, section=section)


def build_filename(doc_type: dict, ctx: FolderContext, tag: str) -> str:
    tpl = doc_type.get("template", "{code}_{label}_{date}_{episode}_{tag}")
    values = {
        "code": sanitize_part(doc_type.get("code", "000")),
        "label": sanitize_part(doc_type.get("label", "документ")),
        "tag": sanitize_part(tag),
        **{k: sanitize_part(v) for k, v in ctx.as_dict().items()},
    }
    name = tpl.format(**values)
    name = re.sub(r"_+", "_", name)
    return name.strip("_ ")


def _build_scan_args(cmd_template: str, output_path: Path) -> str | list[str]:
    normalized_cmd = _normalize_scan_command(cmd_template)
    output_placeholder = "{output_path}"
    output_value = str(output_path)
    if sys.platform.startswith("win"):
        if f'"{output_placeholder}"' in normalized_cmd or f"'{output_placeholder}'" in normalized_cmd:
            cmd = normalized_cmd.format(output_path=output_value)
        else:
            cmd = normalized_cmd.replace(output_placeholder, f'"{output_value}"')
    else:
        cmd = normalized_cmd.format(output_path=output_value)
    if sys.platform.startswith("win"):
        return cmd
    return shlex.split(cmd, posix=True)


def run_scan(cmd_template: str, output_path: Path) -> None:
    args = _build_scan_args(cmd_template, output_path)
    if not args:
        raise ValueError("Команда сканування порожня")
    kwargs = {"check": True, "shell": False, "capture_output": True, "text": True}
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.run(args, **kwargs)


def cleanup_temp_files(temp_dir: Path) -> int:
    if not temp_dir.exists():
        return 0
    removed = 0
    for item in temp_dir.iterdir():
        if item.is_file():
            item.unlink(missing_ok=True)
            removed += 1
    return removed


def cleanup_temp_file(temp_path: Path) -> None:
    if temp_path.exists():
        temp_path.unlink(missing_ok=True)


def select_initial_doc_index(doc_types: list[dict], last_doc_type: str) -> int:
    for idx, doc_type in enumerate(doc_types):
        if doc_type.get("key", "") == last_doc_type:
            return idx
    return 0


def select_initial_tag(tags: list[str], last_tag: str) -> str:
    if not tags:
        return ""
    if last_tag and last_tag in tags:
        return last_tag
    return tags[0]


def collect_parse_warnings(ctx: FolderContext, tag: str, doc_type: dict | None = None) -> list[str]:
    warnings: list[str] = []
    if not tag:
        warnings.append("не знайдено підрозділ")
    if not ctx.date:
        warnings.append("не знайдено дату")
    if not ctx.episode:
        warnings.append("не знайдено епізод")
    if doc_type and "{section}" in doc_type.get("template", "") and not ctx.section:
        warnings.append("не знайдено секцію")
    return warnings


def format_scan_process_error(exc: subprocess.CalledProcessError) -> str:
    details = (exc.stderr or exc.stdout or "").strip()
    if details:
        return f"Сканування завершилось з помилкою (код {exc.returncode}): {details}"
    return f"Сканування завершилось з помилкою (код {exc.returncode})"


def pick_increment_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    idx = 2
    while True:
        candidate = parent / f"{stem} ({idx}){suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def resolve_final_output_path(
    target_path: Path,
    duplicate_strategy: str,
    ask_user_choice: Callable[[], str] | None = None,
) -> tuple[Path | None, str]:
    strategy = (duplicate_strategy or "ask").lower()
    if strategy not in {"ask", "overwrite", "increment"}:
        strategy = "ask"
    if not target_path.exists():
        return target_path, strategy
    if strategy == "overwrite":
        return target_path, strategy
    if strategy == "increment":
        return pick_increment_path(target_path), strategy
    chooser = ask_user_choice or (lambda: "cancel")
    user_choice = chooser()
    if user_choice == "overwrite":
        return target_path, "overwrite"
    if user_choice == "increment":
        return pick_increment_path(target_path), "increment"
    return None, "cancelled"


def _resolve_relative_to_launcher(path_value: str, fallback: str) -> Path:
    value = (path_value or fallback).strip() or fallback
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parent / candidate


def get_temp_output_path(temp_dir_value: str, extension: str = "pdf") -> Path:
    ext = extension.lstrip(".") or "pdf"
    temp_dir = _resolve_relative_to_launcher(temp_dir_value, "tmp_scans")
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"


def validate_temp_scan_result(temp_output_path: Path) -> None:
    if not temp_output_path.exists():
        raise FileNotFoundError(f"Тимчасовий файл сканування не створено: {temp_output_path}")
    if temp_output_path.stat().st_size <= 0:
        raise ValueError(f"Тимчасовий файл сканування порожній: {temp_output_path}")


def move_temp_to_final(temp_output_path: Path, final_output_path: Path) -> Path:
    final_output_path.parent.mkdir(parents=True, exist_ok=True)
    if final_output_path.exists():
        final_output_path.unlink()
    try:
        shutil.move(str(temp_output_path), str(final_output_path))
    except Exception as exc:
        raise RuntimeError(f"Не вдалося перемістити файл у цільову папку: {exc}") from exc
    return final_output_path


def append_scan_log(log_path: Path, entry: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = log_path.exists()
    with log_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        row = {field: entry.get(field, "") for field in LOG_FIELDS}
        writer.writerow(row)


def validate_doc_types(doc_types: object) -> tuple[bool, str | None]:
    if not isinstance(doc_types, list):
        return False, "doc_types має бути списком об'єктів"
    required = {"key", "label", "code", "template"}
    for idx, item in enumerate(doc_types, start=1):
        if not isinstance(item, dict):
            return False, f"Елемент doc_types #{idx} має бути об'єктом"
        missing = required - set(item.keys())
        if missing:
            return False, f"Елемент doc_types #{idx} не містить поля: {', '.join(sorted(missing))}"
        template = str(item.get("template", ""))
        placeholders = set(PLACEHOLDER_RE.findall(template))
        unknown = placeholders - ALLOWED_TEMPLATE_PLACEHOLDERS
        if unknown:
            return (
                False,
                f"Елемент doc_types #{idx} містить невідомі плейсхолдери: {', '.join(sorted(unknown))}",
            )
    return True, None


class TextEditHelper:
    def __init__(self, root: Tk):
        self.root = root
        self._menu = Menu(root, tearoff=0)
        self._widget: Entry | Text | None = None
        self._menu.add_command(label="Вирізати", command=lambda: self._cut(self._widget))
        self._menu.add_command(label="Копіювати", command=lambda: self._copy(self._widget))
        self._menu.add_command(label="Вставити", command=lambda: self._paste(self._widget))
        self._menu.add_separator()
        self._menu.add_command(label="Виділити все", command=lambda: self._select_all(self._widget))
        self._menu.add_command(label="Очистити", command=lambda: self._clear(self._widget))

    def bind(self, widget: Entry | Text) -> None:
        widget.bind("<Button-1>", lambda e: self._focus_widget(e.widget), add="+")
        widget.bind("<Button-3>", self._show_menu, add="+")
        for seq in ("<Control-a>", "<Control-A>"):
            widget.bind(seq, self._on_select_all, add="+")
        for seq in ("<Control-c>", "<Control-C>", "<Control-Insert>"):
            widget.bind(seq, self._on_copy, add="+")
        for seq in ("<Control-x>", "<Control-X>"):
            widget.bind(seq, self._on_cut, add="+")
        for seq in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
            widget.bind(seq, self._on_paste, add="+")

    def _show_menu(self, event) -> str:
        self._widget = event.widget
        self._focus_widget(event.widget)
        self._menu.tk_popup(event.x_root, event.y_root)
        self._menu.grab_release()
        return "break"

    def _focus_widget(self, widget) -> None:
        widget.focus_set()

    def _on_select_all(self, event) -> str:
        self._select_all(event.widget)
        return "break"

    def _on_copy(self, event) -> str:
        self._copy(event.widget)
        return "break"

    def _on_cut(self, event) -> str:
        self._cut(event.widget)
        return "break"

    def _on_paste(self, event) -> str:
        self._paste(event.widget)
        return "break"

    def _select_all(self, widget: Entry | Text | None) -> None:
        if widget is None:
            return
        if isinstance(widget, Entry):
            widget.selection_range(0, END)
            widget.icursor(END)
        else:
            widget.tag_add("sel", "1.0", END)
            widget.mark_set(INSERT, "1.0")
            widget.see(INSERT)

    def _copy(self, widget: Entry | Text | None) -> None:
        if widget is None:
            return
        try:
            widget.event_generate("<<Copy>>")
        except Exception:
            pass

    def _cut(self, widget: Entry | Text | None) -> None:
        if widget is None:
            return
        try:
            widget.event_generate("<<Cut>>")
        except Exception:
            pass

    def _paste(self, widget: Entry | Text | None) -> None:
        if widget is None:
            return
        try:
            widget.event_generate("<<Paste>>")
        except Exception:
            pass

    def _clear(self, widget: Entry | Text | None) -> None:
        if widget is None:
            return
        if isinstance(widget, Entry):
            widget.delete(0, END)
        else:
            widget.delete("1.0", END)


class ScannerUI:
    def __init__(self, cwd: Path):
        self.cwd = cwd
        self.config = load_config()
        self.ctx = parse_context(cwd)
        self.root = Tk()
        self.root.title("TC Scanner")
        self.root.geometry("720x420")
        self.text_helper = TextEditHelper(self.root)
        self.doc_types = self.config.get("doc_types", [])
        self.current_doc: dict | None = None
        self.tag_var = StringVar(self.root)
        self.tags = self.ctx.tags or []
        ui_state = self.config.get("ui_state", {})
        self.tag_var.set(select_initial_tag(self.tags, ui_state.get("last_tag", "")))
        self.preview_var = StringVar(self.root)
        self.custom_name_var = StringVar(self.root)
        self.status_var = StringVar(self.root, "Готово")
        self._build()
        self.name_entry.focus_set()
        initial_tag = self.tag_var.get().strip()
        parse_warnings = collect_parse_warnings(self.ctx, initial_tag)
        if parse_warnings:
            log_path = _resolve_relative_to_launcher(self.config.get("log_file", ""), "scan_log.csv")
            append_scan_log(
                log_path,
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "status": "parse_warning",
                    "current_folder": str(self.cwd),
                    "document_key": "",
                    "document_label": "",
                    "selected_tag": "",
                    "generated_filename": "",
                    "temp_output_path": "",
                    "final_output_path": "",
                    "duplicate_strategy": self.config.get("duplicate_strategy", "ask"),
                    "message": f"Контекст папки розпізнано частково: {', '.join(parse_warnings)}",
                },
            )
            self._set_status("Попередження: структура папки неповна")
        self._refresh_preview()

    def _build(self) -> None:
        main = Frame(self.root)
        main.pack(fill=BOTH, expand=True, padx=16, pady=14)

        left = Frame(main)
        left.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 12))
        right = Frame(main)
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="Що сканувати:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.doc_list = Listbox(left, height=12, font=("Segoe UI", 10), activestyle="dotbox")
        self.doc_list.pack(fill=BOTH, expand=True, pady=(8, 0))
        for item in self.doc_types:
            self.doc_list.insert(END, f"{item.get('code','000')} — {item.get('label','Документ')}")
        self.doc_list.bind("<<ListboxSelect>>", lambda _: self._on_doc_changed())

        if self.doc_types:
            idx = select_initial_doc_index(self.doc_types, self.config.get("ui_state", {}).get("last_doc_type", ""))
            self.doc_list.selection_set(idx)
            self._on_doc_changed()

        Label(right, text="Тег/підрозділ:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        if len(self.tags) <= 1:
            self.tag_var.set(self.tags[0] if self.tags else "")
            Label(right, textvariable=self.tag_var, fg="#1f6d1f").pack(anchor="w", pady=(8, 12))
        else:
            OptionMenu(right, self.tag_var, *self.tags, command=lambda _: self._on_tag_changed()).pack(fill="x", pady=(8, 12))

        Label(right, text="Назва файлу:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.name_entry = Entry(right, textvariable=self.custom_name_var)
        self.name_entry.pack(fill="x", pady=(8, 4))
        self.text_helper.bind(self.name_entry)
        self.custom_name_var.trace_add("write", lambda *_: self._refresh_preview())

        Label(right, text="Прев'ю:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        Label(
            right,
            textvariable=self.preview_var,
            wraplength=340,
            justify=LEFT,
            fg="#0a5a9c",
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        btns = Frame(right)
        btns.pack(fill="x", pady=(16, 0))
        Button(btns, text="Сканувати", command=self._scan, bg="#2f7", font=("Segoe UI", 12, "bold"), padx=20, pady=7).pack(side=LEFT)
        Button(btns, text="Налаштування", command=self._settings).pack(side=LEFT, padx=8)
        Button(btns, text="Вихід", command=self.root.destroy).pack(side=RIGHT)

        Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken", padx=8).pack(fill="x", side="bottom")
        self.root.bind("<Return>", lambda _: self._scan())
        self.root.bind("<Escape>", lambda _: self.root.destroy())
        self.root.bind("<Control-l>", lambda _: self._clear_name())
        self.root.bind("<Control-L>", lambda _: self._clear_name())

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.root.update_idletasks()

    def _save_ui_state(self) -> None:
        self.config["ui_state"] = {
            "last_doc_type": self.current_doc.get("key", "") if self.current_doc else "",
            "last_tag": self.tag_var.get(),
        }
        save_config(self.config)

    def _on_tag_changed(self) -> None:
        self._save_ui_state()
        self._refresh_preview()

    def _clear_name(self) -> str:
        self.custom_name_var.set("")
        return "break"

    def _on_doc_changed(self) -> None:
        idxs = self.doc_list.curselection()
        if not idxs:
            self.current_doc = None
            return
        self.current_doc = self.doc_types[idxs[0]]
        self._save_ui_state()
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        if not self.current_doc:
            return
        tag = self.tag_var.get() if self.tag_var.get() != "(не знайдено)" else ""
        auto_name = build_filename(self.current_doc, self.ctx, tag)
        manual = sanitize_part(self.custom_name_var.get())
        name = manual if manual else auto_name
        ext = self.config.get("output_extension", "pdf")
        self.preview_var.set(str(self.cwd / f"{name}.{ext}"))

    def _scan(self) -> None:
        if not self.current_doc:
            self._set_status("Помилка: оберіть тип документа")
            messagebox.showerror("Помилка", "Оберіть тип документа")
            return

        cmd = _normalize_scan_command(self.config.get("scan_command", "")).strip()
        if not cmd:
            self._set_status("Помилка: не налаштована команда сканування")
            messagebox.showerror("Помилка", "Не налаштована команда сканування")
            return

        tag = self.tag_var.get().strip()
        parse_warnings = collect_parse_warnings(self.ctx, tag, self.current_doc)
        if parse_warnings:
            warning_text = "Попередження: структура папки неповна"
            if len(parse_warnings) == 1:
                warning_text = f"Попередження: {parse_warnings[0]}"
            self._set_status(warning_text)

        auto_name = build_filename(self.current_doc, self.ctx, tag)
        name = sanitize_part(self.custom_name_var.get()) or auto_name
        extension = self.config.get("output_extension", "pdf")
        output_path = self.cwd / f"{name}.{extension}"

        temp_path = get_temp_output_path(self.config.get("temp_dir", "tmp_scans"), extension)
        log_path = _resolve_relative_to_launcher(self.config.get("log_file", "scan_log.csv"), "scan_log.csv")

        log_entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": "error",
            "current_folder": str(self.cwd),
            "document_key": self.current_doc.get("key", ""),
            "document_label": self.current_doc.get("label", ""),
            "selected_tag": tag,
            "generated_filename": f"{name}.{extension}",
            "temp_output_path": str(temp_path),
            "final_output_path": "",
            "duplicate_strategy": self.config.get("duplicate_strategy", "ask"),
            "message": "",
        }

        def _ask_duplicate_choice() -> str:
            res = messagebox.askyesnocancel(
                "Файл вже існує",
                "Файл вже існує.\nТак — перезаписати\nНі — створити копію з номером\nСкасувати — відмінити сканування",
            )
            if res is True:
                return "overwrite"
            if res is False:
                return "increment"
            return "cancel"

        try:
            resolved_path, resolved_strategy = resolve_final_output_path(
                output_path,
                self.config.get("duplicate_strategy", "ask"),
                ask_user_choice=_ask_duplicate_choice,
            )
            log_entry["duplicate_strategy"] = resolved_strategy
            if resolved_path is None:
                cleanup_temp_file(temp_path)
                log_entry["status"] = "cancelled"
                log_entry["message"] = "Користувач скасував операцію через конфлікт дубліката"
                append_scan_log(log_path, log_entry)
                self._set_status("Скасовано")
                return

            log_entry["final_output_path"] = str(resolved_path)
            if parse_warnings:
                append_scan_log(
                    log_path,
                    {
                        **log_entry,
                        "status": "parse_warning",
                        "message": f"Сканування з неповним контекстом: {', '.join(parse_warnings)}",
                    },
                )
            self._set_status("Сканування...")
            run_scan(cmd, temp_path)
            validate_temp_scan_result(temp_path)
            self._set_status("Обробка...")
            final_path = move_temp_to_final(temp_path, resolved_path)

            log_entry["status"] = "success"
            log_entry["message"] = "Сканування завершено успішно"
            append_scan_log(log_path, log_entry)
            self._set_status("Готово")
            messagebox.showinfo("Готово", f"Файл створено:\n{final_path}")
        except ValueError as exc:
            log_entry["message"] = str(exc)
            append_scan_log(log_path, log_entry)
            self._set_status(f"Помилка: {exc}")
            messagebox.showerror("Помилка", str(exc))
        except FileNotFoundError as exc:
            log_entry["message"] = str(exc)
            append_scan_log(log_path, log_entry)
            self._set_status(f"Помилка: {exc}")
            messagebox.showerror("Помилка", str(exc))
        except subprocess.CalledProcessError as exc:
            error_message = format_scan_process_error(exc)
            log_entry["message"] = error_message
            append_scan_log(log_path, log_entry)
            self._set_status(f"Помилка: {error_message}")
            messagebox.showerror("Помилка", error_message)
        except Exception as exc:
            log_entry["message"] = str(exc)
            append_scan_log(log_path, log_entry)
            self._set_status(f"Помилка: {exc}")
            messagebox.showerror("Помилка", str(exc))
        finally:
            cleanup_temp_file(temp_path)

    def _settings(self) -> None:
        wnd = Toplevel(self.root)
        wnd.title("Налаштування")
        wnd.geometry("760x500")
        Label(wnd, text="Команда сканування (використовуйте {output_path}):").pack(anchor="w", padx=10, pady=(10, 2))
        cmd_var = StringVar(wnd, self.config.get("scan_command", ""))
        cmd_entry = Entry(wnd, textvariable=cmd_var)
        cmd_entry.pack(fill="x", padx=10)
        self.text_helper.bind(cmd_entry)

        Label(wnd, text="Стратегія дублікатів:").pack(anchor="w", padx=10, pady=(10, 2))
        dup_var = StringVar(wnd, self.config.get("duplicate_strategy", "ask"))
        OptionMenu(wnd, dup_var, "ask", "overwrite", "increment").pack(fill="x", padx=10)

        Label(wnd, text="Тимчасова папка (відносно папки програми):").pack(anchor="w", padx=10, pady=(10, 2))
        temp_var = StringVar(wnd, self.config.get("temp_dir", "tmp_scans"))
        temp_entry = Entry(wnd, textvariable=temp_var)
        temp_entry.pack(fill="x", padx=10)
        self.text_helper.bind(temp_entry)

        Label(wnd, text="Файл логу (відносно папки програми):").pack(anchor="w", padx=10, pady=(10, 2))
        log_var = StringVar(wnd, self.config.get("log_file", "scan_log.csv"))
        log_entry = Entry(wnd, textvariable=log_var)
        log_entry.pack(fill="x", padx=10)
        self.text_helper.bind(log_entry)

        Label(wnd, text="JSON для типів документів:").pack(anchor="w", padx=10, pady=(10, 2))
        txt = ScrolledText(wnd, height=14, wrap="word")
        txt.pack(fill=BOTH, expand=True, padx=10)
        self.text_helper.bind(txt)
        txt.insert("1.0", json.dumps(self.config.get("doc_types", []), ensure_ascii=False, indent=2))

        def save() -> None:
            try:
                raw_docs = txt.get("1.0", END).rstrip("\n")
                docs = json.loads(raw_docs)
                ok, validation_message = validate_doc_types(docs)
                if not ok:
                    messagebox.showerror("Помилка", validation_message)
                    return

                self.config["doc_types"] = docs
                self.config["scan_command"] = _normalize_scan_command(cmd_var.get().strip())
                self.config["duplicate_strategy"] = dup_var.get().strip() or "ask"
                self.config["temp_dir"] = temp_var.get().strip() or "tmp_scans"
                self.config["log_file"] = log_var.get().strip() or "scan_log.csv"
                save_config(self.config)
            except json.JSONDecodeError as exc:
                messagebox.showerror("Помилка JSON", f"Невалідний JSON у типах документів:\n{exc}")
                return
            except Exception as exc:
                messagebox.showerror("Помилка", f"Не вдалося зберегти:\n{exc}")
                return
            messagebox.showinfo("OK", "Налаштування збережено. Перезапустіть вікно.")
            wnd.destroy()

        Button(wnd, text="Зберегти", command=save).pack(padx=10, pady=12, anchor="e")

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    raw_cwd = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    cwd = Path(_clean_target_dir(raw_cwd)).resolve()
    cfg = load_config()
    cleanup_temp_files(_resolve_relative_to_launcher(cfg.get("temp_dir", "tmp_scans"), "tmp_scans"))
    ui = ScannerUI(cwd)
    ui.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
