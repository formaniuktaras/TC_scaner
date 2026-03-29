#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    INSERT,
    LEFT,
    RIGHT,
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    Label,
    Listbox,
    Menu,
    OptionMenu,
    StringVar,
    Tk,
    Toplevel,
    messagebox,
)
from tkinter.scrolledtext import ScrolledText
from typing import Dict, List

from app_config import AppConfig, ConfigValidationError, DocTypeConfig, load_config, save_config
from naming_utils import build_document_filename, sanitize_part
from scan_runtime import (
    append_scan_log,
    cleanup_temp_file,
    cleanup_temp_files,
    format_scan_process_error,
    get_log_file_path,
    get_temp_dir,
    get_temp_output_path,
    move_temp_to_final,
    resolve_final_output_path,
    run_scan,
    should_force_temp_for_path,
    validate_temp_scan_result,
)

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{2}$")
SECTION_RE = re.compile(r"^(?P<section>\d{2})[_\s].+$")


@dataclass
class FolderContext:
    date: str = ""
    episode: str = ""
    tags: List[str] | None = None
    section: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {"date": self.date, "episode": self.episode, "section": self.section}


def _clean_target_dir(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    return value.replace('"', "")


def parse_context(folder: Path) -> FolderContext:
    tags: List[str] = []
    date = ""
    episode = ""
    section = ""

    for part in [folder] + list(folder.parents):
        parts = [p.strip() for p in part.name.split("_") if p.strip()]
        if len(parts) < 3:
            continue
        date, episode = parts[1], parts[2]
        if not DATE_RE.match(date):
            logging.debug("parse_warning: invalid date format in folder '%s': '%s'", part.name, date)
        last_part = parts[-1]
        tags = [sanitize_part(x) for x in last_part.split("+") if x.strip()] if "+" in last_part else []
        break

    for part in [folder] + list(folder.parents):
        section_match = SECTION_RE.match(part.name)
        if section_match:
            section = section_match.group("section")
            break

    return FolderContext(date=date, episode=episode, tags=tags, section=section)


def select_initial_doc_index(doc_types: list[DocTypeConfig], last_doc_type: str) -> int:
    for idx, doc_type in enumerate(doc_types):
        if doc_type.key == last_doc_type:
            return idx
    return 0


def select_initial_tag(tags: list[str], last_tag: str) -> str:
    if not tags:
        return ""
    if last_tag and last_tag in tags:
        return last_tag
    return tags[0]


def collect_parse_warnings(ctx: FolderContext, tag: str, template: str | None = None) -> list[str]:
    warnings: list[str] = []
    if not tag:
        warnings.append("не знайдено підрозділ")
    if not ctx.date:
        warnings.append("не знайдено дату")
    if not ctx.episode:
        warnings.append("не знайдено епізод")
    if template and "{section}" in template and not ctx.section:
        warnings.append("не знайдено секцію")
    return warnings


class TextEditHelper:
    def __init__(self, root: Tk):
        self.root = root
        self._menu = Menu(root, tearoff=0)
        self._widget: Entry | ScrolledText | None = None
        self._menu.add_command(label="Вирізати", command=lambda: self._event(self._widget, "<<Cut>>"))
        self._menu.add_command(label="Копіювати", command=lambda: self._event(self._widget, "<<Copy>>"))
        self._menu.add_command(label="Вставити", command=lambda: self._event(self._widget, "<<Paste>>"))

    def bind(self, widget):
        widget.bind("<Button-3>", self._show_menu, add="+")

    def _show_menu(self, event) -> str:
        self._widget = event.widget
        self._menu.tk_popup(event.x_root, event.y_root)
        self._menu.grab_release()
        return "break"

    @staticmethod
    def _event(widget, name: str):
        if widget:
            widget.event_generate(name)


class ScannerUI:
    def __init__(self, cwd: Path):
        self.cwd = cwd
        self.app_config = load_config()
        self.ctx = parse_context(cwd)
        self.root = Tk()
        self.root.title("TC Scanner")
        self.root.geometry("760x460")
        self.text_helper = TextEditHelper(self.root)
        self.doc_types = self.app_config.doc_types
        self.current_doc: DocTypeConfig | None = None
        self.tag_var = StringVar(self.root)
        self.tags = self.ctx.tags or []
        self.tag_var.set(select_initial_tag(self.tags, self.app_config.ui_state.last_tag))
        self.preview_var = StringVar(self.root)
        self.custom_name_var = StringVar(self.root)
        self.status_var = StringVar(self.root, "Готово")
        self._build()
        if self.app_config.ui.focus_name_on_start:
            self.name_entry.focus_set()
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
            self.doc_list.insert(END, f"{item.code} — {item.label}")
        self.doc_list.bind("<<ListboxSelect>>", lambda _: self._on_doc_changed())

        if self.doc_types:
            idx = select_initial_doc_index(self.doc_types, self.app_config.ui_state.last_doc_type)
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
        self.custom_name_var.trace_add("write", lambda *_: self._refresh_preview())

        Label(right, text="Прев'ю:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        Label(right, textvariable=self.preview_var, wraplength=340, justify=LEFT, fg="#0a5a9c", anchor="w").pack(anchor="w", pady=(6, 0))

        btns = Frame(right)
        btns.pack(fill="x", pady=(16, 0))
        Button(btns, text="Сканувати", command=self._scan, bg="#2f7", font=("Segoe UI", 12, "bold"), padx=20, pady=7).pack(side=LEFT)
        Button(btns, text="Налаштування", command=self._settings).pack(side=LEFT, padx=8)
        Button(btns, text="Вихід", command=self.root.destroy).pack(side=RIGHT)

        if self.app_config.ui.show_status_bar:
            Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken", padx=8).pack(fill="x", side="bottom")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.root.update_idletasks()

    def _save_ui_state(self) -> None:
        if self.app_config.ui.remember_last_doc_type:
            self.app_config.ui_state.last_doc_type = self.current_doc.key if self.current_doc else ""
        if self.app_config.ui.remember_last_tag:
            self.app_config.ui_state.last_tag = self.tag_var.get()
        save_config(self.app_config)

    def _on_tag_changed(self) -> None:
        self._save_ui_state()
        self._refresh_preview()

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
        tag = self.tag_var.get().strip()
        values = {
            "code": self.current_doc.code,
            "label": self.current_doc.label,
            "tag": tag,
            **self.ctx.as_dict(),
        }
        auto_name = build_document_filename(
            self.current_doc.template,
            self.app_config.naming.minimal_template,
            values,
            self.app_config.naming,
        )
        manual = sanitize_part(self.custom_name_var.get())
        name = manual if manual else auto_name
        self.preview_var.set(str(self.cwd / f"{name}.{self.app_config.scan.output_extension}"))

    def _settings(self) -> None:
        wnd = Toplevel(self.root)
        wnd.title("Налаштування")
        wnd.geometry("850x640")

        mode_var = StringVar(wnd, self.app_config.ui.mode)
        Button(wnd, text="Розширені налаштування", command=lambda: mode_var.set("advanced")).pack(anchor="e", padx=10, pady=4)

        form = Frame(wnd)
        form.pack(fill="both", expand=True, padx=10, pady=6)

        Label(form, text="driver").grid(row=0, column=0, sticky="w")
        driver_var = StringVar(form, self.app_config.scan.driver)
        OptionMenu(form, driver_var, "twain", "wia", "sane").grid(row=0, column=1, sticky="ew")
        Label(form, text="device").grid(row=1, column=0, sticky="w")
        device_var = StringVar(form, self.app_config.scan.device)
        Entry(form, textvariable=device_var).grid(row=1, column=1, sticky="ew")
        Label(form, text="dpi").grid(row=2, column=0, sticky="w")
        dpi_var = StringVar(form, str(self.app_config.scan.dpi))
        Entry(form, textvariable=dpi_var).grid(row=2, column=1, sticky="ew")
        Label(form, text="page_size").grid(row=3, column=0, sticky="w")
        page_size_var = StringVar(form, self.app_config.scan.page_size)
        Entry(form, textvariable=page_size_var).grid(row=3, column=1, sticky="ew")
        Label(form, text="bitdepth").grid(row=4, column=0, sticky="w")
        bitdepth_var = StringVar(form, self.app_config.scan.bitdepth)
        Entry(form, textvariable=bitdepth_var).grid(row=4, column=1, sticky="ew")
        Label(form, text="output_extension").grid(row=5, column=0, sticky="w")
        ext_var = StringVar(form, self.app_config.scan.output_extension)
        Entry(form, textvariable=ext_var).grid(row=5, column=1, sticky="ew")

        Label(form, text="temp_dir").grid(row=6, column=0, sticky="w")
        temp_var = StringVar(form, self.app_config.paths.temp_dir)
        Entry(form, textvariable=temp_var).grid(row=6, column=1, sticky="ew")
        Label(form, text="log_file").grid(row=7, column=0, sticky="w")
        log_var = StringVar(form, self.app_config.paths.log_file)
        Entry(form, textvariable=log_var).grid(row=7, column=1, sticky="ew")

        Label(form, text="duplicate_strategy").grid(row=8, column=0, sticky="w")
        dup_var = StringVar(form, self.app_config.behavior.duplicate_strategy)
        OptionMenu(form, dup_var, "ask", "overwrite", "increment").grid(row=8, column=1, sticky="ew")

        allow_incomplete_var = BooleanVar(form, self.app_config.behavior.allow_incomplete_context)
        Checkbutton(form, text="allow_incomplete_context", variable=allow_incomplete_var).grid(row=9, column=1, sticky="w")
        replace_spaces_var = StringVar(form, self.app_config.naming.replace_spaces)
        Label(form, text="replace_spaces").grid(row=10, column=0, sticky="w")
        Entry(form, textvariable=replace_spaces_var).grid(row=10, column=1, sticky="ew")
        max_length_var = StringVar(form, str(self.app_config.naming.max_length))
        Label(form, text="max_length").grid(row=11, column=0, sticky="w")
        Entry(form, textvariable=max_length_var).grid(row=11, column=1, sticky="ew")

        remember_doc_var = BooleanVar(form, self.app_config.ui.remember_last_doc_type)
        remember_tag_var = BooleanVar(form, self.app_config.ui.remember_last_tag)
        focus_var = BooleanVar(form, self.app_config.ui.focus_name_on_start)
        Checkbutton(form, text="remember_last_doc_type", variable=remember_doc_var).grid(row=12, column=1, sticky="w")
        Checkbutton(form, text="remember_last_tag", variable=remember_tag_var).grid(row=13, column=1, sticky="w")
        Checkbutton(form, text="focus_name_on_start", variable=focus_var).grid(row=14, column=1, sticky="w")

        Label(form, text="advanced: command_template").grid(row=15, column=0, sticky="w")
        cmd_var = StringVar(form, self.app_config.scan.command_template)
        Entry(form, textvariable=cmd_var).grid(row=15, column=1, sticky="ew")
        Label(form, text="advanced: network_prefixes (comma)").grid(row=16, column=0, sticky="w")
        prefixes_var = StringVar(form, ",".join(self.app_config.paths.network_prefixes))
        Entry(form, textvariable=prefixes_var).grid(row=16, column=1, sticky="ew")
        force_temp_var = BooleanVar(form, self.app_config.paths.force_temp_for_network)
        Checkbutton(form, text="force_temp_for_network", variable=force_temp_var).grid(row=17, column=1, sticky="w")

        Label(form, text="doc_types JSON").grid(row=18, column=0, sticky="nw")
        doc_editor = ScrolledText(form, height=10, wrap="word")
        doc_editor.grid(row=18, column=1, sticky="nsew")
        doc_editor.insert("1.0", json.dumps([d.__dict__ for d in self.app_config.doc_types], ensure_ascii=False, indent=2))
        form.columnconfigure(1, weight=1)
        form.rowconfigure(18, weight=1)

        def save_settings() -> None:
            try:
                self.app_config.scan.driver = driver_var.get().strip()
                self.app_config.scan.device = device_var.get().strip()
                self.app_config.scan.dpi = int(dpi_var.get().strip())
                self.app_config.scan.page_size = page_size_var.get().strip()
                self.app_config.scan.bitdepth = bitdepth_var.get().strip()
                self.app_config.scan.output_extension = ext_var.get().strip()
                self.app_config.scan.command_template = cmd_var.get().strip()
                self.app_config.paths.temp_dir = temp_var.get().strip()
                self.app_config.paths.log_file = log_var.get().strip()
                self.app_config.paths.force_temp_for_network = force_temp_var.get()
                self.app_config.paths.network_prefixes = [x.strip() for x in prefixes_var.get().split(",") if x.strip()]
                self.app_config.behavior.duplicate_strategy = dup_var.get().strip()
                self.app_config.behavior.allow_incomplete_context = allow_incomplete_var.get()
                self.app_config.naming.replace_spaces = replace_spaces_var.get()
                self.app_config.naming.max_length = int(max_length_var.get().strip())
                self.app_config.ui.remember_last_doc_type = remember_doc_var.get()
                self.app_config.ui.remember_last_tag = remember_tag_var.get()
                self.app_config.ui.focus_name_on_start = focus_var.get()
                self.app_config.ui.mode = mode_var.get().strip() or "simple"
                docs = json.loads(doc_editor.get("1.0", END).strip())
                self.app_config.doc_types = [DocTypeConfig.from_dict(x) for x in docs]
                self.app_config.validate()
                save_config(self.app_config)
            except (ValueError, ConfigValidationError, json.JSONDecodeError) as exc:
                messagebox.showerror("Помилка валідації", str(exc))
                return
            messagebox.showinfo("OK", "Налаштування збережено")
            wnd.destroy()

        Button(wnd, text="Зберегти", command=save_settings).pack(padx=10, pady=8, anchor="e")

    def _scan(self) -> None:
        if not self.current_doc:
            messagebox.showerror("Помилка", "Оберіть тип документа")
            return

        tag = self.tag_var.get().strip()
        parse_warnings = collect_parse_warnings(self.ctx, tag, self.current_doc.template)
        if parse_warnings and not self.app_config.behavior.allow_incomplete_context:
            messagebox.showerror("Помилка", f"Контекст папки неповний: {', '.join(parse_warnings)}")
            return

        values = {"code": self.current_doc.code, "label": self.current_doc.label, "tag": tag, **self.ctx.as_dict()}
        auto_name = build_document_filename(self.current_doc.template, self.app_config.naming.minimal_template, values, self.app_config.naming)
        name = sanitize_part(self.custom_name_var.get()) or auto_name
        output_path = self.cwd / f"{name}.{self.app_config.scan.output_extension}"

        temp_path = get_temp_output_path(self.app_config, self.app_config.scan.output_extension)
        log_path = get_log_file_path(self.app_config)
        force_temp = should_force_temp_for_path(output_path, self.app_config)

        def _ask_duplicate_choice() -> str:
            res = messagebox.askyesnocancel("Файл вже існує", "Так — перезаписати, Ні — створити копію, Скасувати — відмінити")
            if res is True:
                return "overwrite"
            if res is False:
                return "increment"
            return "cancel"

        log_entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": "error",
            "current_folder": str(self.cwd),
            "document_key": self.current_doc.key,
            "document_label": self.current_doc.label,
            "selected_tag": tag,
            "generated_filename": f"{name}.{self.app_config.scan.output_extension}",
            "temp_output_path": str(temp_path),
            "final_output_path": "",
            "duplicate_strategy": self.app_config.behavior.duplicate_strategy,
            "message": "",
        }

        try:
            resolved_path, strategy = resolve_final_output_path(output_path, self.app_config.behavior.duplicate_strategy, _ask_duplicate_choice)
            log_entry["duplicate_strategy"] = strategy
            if resolved_path is None:
                log_entry["status"] = "cancelled"
                log_entry["message"] = "Користувач скасував операцію через конфлікт дубліката"
                append_scan_log(log_path, log_entry)
                return

            if parse_warnings and self.app_config.behavior.log_parse_warnings:
                append_scan_log(log_path, {**log_entry, "status": "parse_warning", "message": ", ".join(parse_warnings)})
            self._set_status("Сканування...")
            run_scan(self.app_config, temp_path if force_temp else resolved_path)
            target = temp_path if force_temp else resolved_path
            validate_temp_scan_result(target)
            if force_temp:
                move_temp_to_final(temp_path, resolved_path)
            log_entry["status"] = "success"
            append_scan_log(log_path, log_entry)
            self._set_status("Готово")
        except subprocess.CalledProcessError as exc:
            log_entry["message"] = format_scan_process_error(exc)
            append_scan_log(log_path, log_entry)
            self._set_status(log_entry["message"])
            messagebox.showerror("Помилка", log_entry["message"])
        except Exception as exc:
            log_entry["message"] = str(exc)
            append_scan_log(log_path, log_entry)
            self._set_status(f"Помилка: {exc}")
            messagebox.showerror("Помилка", str(exc))
        finally:
            cleanup_temp_file(temp_path)

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    raw_cwd = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    cwd = Path(_clean_target_dir(raw_cwd)).resolve()
    cfg = load_config()
    cleanup_temp_files(get_temp_dir(cfg))
    ui = ScannerUI(cwd)
    ui.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
