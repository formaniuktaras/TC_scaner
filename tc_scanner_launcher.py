#!/usr/bin/env python3
"""TC scanner helper: menu for scan types + automatic filename generation.

Designed to be launched from Total Commander button.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    Button,
    Entry,
    Frame,
    Label,
    Listbox,
    OptionMenu,
    StringVar,
    Tk,
    Toplevel,
    messagebox,
)
from typing import Dict, List

CONFIG_PATH = Path(__file__).with_name("scanner_config.json")


@dataclass
class FolderContext:
    date: str = ""
    episode: str = ""
    tags: List[str] | None = None
    section: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {
            "date": self.date,
            "episode": self.episode,
            "section": self.section,
        }


DEFAULT_CONFIG = {
    "scan_command": "",  # Example: "naps2.console --output {output_path}"
    "output_extension": "pdf",
    "doc_types": [
        {"key": "vvzv", "label": "ВВЗВ", "code": "001", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {"key": "vvm", "label": "ВВМ", "code": "002", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {
            "key": "zalyshkova_vartist",
            "label": "Відомість залишкової вартості",
            "code": "003",
            "template": "{code}_{label}_{date}_{episode}_{tag}",
        },
        {"key": "yeas", "label": "ЄАС", "code": "004", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {"key": "as", "label": "АС", "code": "005", "template": "{code}_{label}_{date}_{episode}_{tag}"},
        {
            "key": "extract_losses",
            "label": "витяг з книги втрат",
            "code": "006",
            "template": "{code}_{section}_{label}_{date}_{episode}_{tag}",
        },
        {
            "key": "extract_shortages",
            "label": "витяг з книги нестач",
            "code": "007",
            "template": "{code}_{section}_{label}_{date}_{episode}_{tag}",
        },
        {"key": "order", "label": "Наказ", "code": "008", "template": "{code}_{label}_{date}_{episode}_{tag}"},
    ],
}

TOP_FOLDER_RE = re.compile(
    r"^(?P<id>\d+?)_(?P<date>\d{2}\.\d{2}\.\d{2})_(?P<episode>\d+?)_(?P<rest>.+)$"
)
SECTION_RE = re.compile(r"^(?P<section>\d{2})[_\s].+$")


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_config(cfg: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


def sanitize_part(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value)
    value = re.sub(r"\s+", " ", value)
    return value


def parse_context(folder: Path) -> FolderContext:
    tags: List[str] = []
    date = ""
    episode = ""
    section = ""

    for part in [folder] + list(folder.parents):
        top_match = TOP_FOLDER_RE.match(part.name)
        if top_match:
            date = top_match.group("date")
            episode = top_match.group("episode")
            suffix = top_match.group("rest")
            if "_" in suffix:
                tags_part = suffix.split("_", maxsplit=2)[-1]
                tags = [sanitize_part(x) for x in tags_part.split("+") if x.strip()]
            break

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


def run_scan(cmd_template: str, output_path: Path) -> None:
    cmd = cmd_template.format(output_path=str(output_path))
    subprocess.run(cmd, shell=True, check=True)


class ScannerUI:
    def __init__(self, cwd: Path):
        self.cwd = cwd
        self.config = load_config()
        self.ctx = parse_context(cwd)

        self.root = Tk()
        self.root.title("TC Scanner")
        self.root.geometry("680x380")

        self.doc_types = self.config.get("doc_types", [])
        self.current_doc: dict | None = None

        self.tag_var = StringVar(self.root)
        tags = self.ctx.tags or [""]
        self.tag_var.set(tags[0])

        self.preview_var = StringVar(self.root)
        self.custom_name_var = StringVar(self.root)

        self._build()
        self._refresh_preview()

    def _build(self) -> None:
        main = Frame(self.root)
        main.pack(fill=BOTH, expand=True, padx=10, pady=10)

        left = Frame(main)
        left.pack(side=LEFT, fill=BOTH, expand=True)

        right = Frame(main)
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="Що сканувати:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.doc_list = Listbox(left, height=12)
        self.doc_list.pack(fill=BOTH, expand=True, pady=(6, 0))
        for item in self.doc_types:
            self.doc_list.insert(END, f"{item.get('code','000')} — {item.get('label','Документ')}")
        self.doc_list.bind("<<ListboxSelect>>", lambda _: self._on_doc_changed())
        if self.doc_types:
            self.doc_list.selection_set(0)
            self._on_doc_changed()

        Label(right, text="Тег/підрозділ:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tags = self.ctx.tags or ["(не знайдено)"]
        OptionMenu(right, self.tag_var, *tags, command=lambda _: self._refresh_preview()).pack(fill="x", pady=(6, 10))

        Label(right, text="Назва файлу:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.name_entry = Entry(right, textvariable=self.custom_name_var)
        self.name_entry.pack(fill="x", pady=(6, 2))
        self.custom_name_var.trace_add("write", lambda *_: self._refresh_preview())

        Label(right, text="Прев'ю:").pack(anchor="w", pady=(8, 0))
        Label(right, textvariable=self.preview_var, wraplength=310, justify=LEFT, fg="#0b5").pack(anchor="w")

        btns = Frame(right)
        btns.pack(fill="x", pady=(14, 0))
        Button(btns, text="Сканувати", command=self._scan, bg="#2f7", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        Button(btns, text="Налаштування", command=self._settings).pack(side=LEFT, padx=8)
        Button(btns, text="Вихід", command=self.root.destroy).pack(side=RIGHT)

    def _on_doc_changed(self) -> None:
        idxs = self.doc_list.curselection()
        if not idxs:
            self.current_doc = None
            return
        self.current_doc = self.doc_types[idxs[0]]
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
            messagebox.showerror("Помилка", "Оберіть тип документа")
            return
        cmd = self.config.get("scan_command", "").strip()
        if not cmd:
            messagebox.showerror("Помилка", "Не налаштована команда сканування")
            return

        tag = self.tag_var.get() if self.tag_var.get() != "(не знайдено)" else ""
        auto_name = build_filename(self.current_doc, self.ctx, tag)
        name = sanitize_part(self.custom_name_var.get()) or auto_name
        output_path = self.cwd / f"{name}.{self.config.get('output_extension', 'pdf')}"

        try:
            run_scan(cmd, output_path)
            messagebox.showinfo("Готово", f"Файл створено:\n{output_path}")
        except subprocess.CalledProcessError as exc:
            messagebox.showerror("Помилка", f"Не вдалося запустити сканування:\n{exc}")

    def _settings(self) -> None:
        wnd = Toplevel(self.root)
        wnd.title("Налаштування")
        wnd.geometry("720x460")

        Label(wnd, text="Команда сканування (використовуйте {output_path}):").pack(anchor="w", padx=10, pady=(10, 2))
        cmd_var = StringVar(wnd, self.config.get("scan_command", ""))
        Entry(wnd, textvariable=cmd_var).pack(fill="x", padx=10)

        Label(wnd, text="JSON для типів документів:").pack(anchor="w", padx=10, pady=(10, 2))
        txt = Entry(wnd)
        txt.pack(fill="x", padx=10)
        txt.insert(0, json.dumps(self.config.get("doc_types", []), ensure_ascii=False))

        def save() -> None:
            try:
                docs = json.loads(txt.get())
                self.config["doc_types"] = docs
                self.config["scan_command"] = cmd_var.get().strip()
                save_config(self.config)
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("Помилка", f"Не вдалося зберегти:\n{exc}")
                return
            messagebox.showinfo("OK", "Налаштування збережено. Перезапустіть вікно.")
            wnd.destroy()

        Button(wnd, text="Зберегти", command=save).pack(padx=10, pady=12, anchor="e")

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    cwd = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    ui = ScannerUI(cwd)
    ui.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
