#!/usr/bin/env python3
"""TC scanner helper: compact launcher window + filename generation.

Designed to be launched from Total Commander button.
"""
from __future__ import annotations

import json
import re
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tkinter import (  # noqa: TC003
    BOTH,
    END,
    LEFT,
    RIGHT,
    TOP,
    Button,
    Entry,
    Frame,
    Label,
    Listbox,
    OptionMenu,
    StringVar,
    Text,
    Tk,
    Toplevel,
    messagebox,
)
from typing import Any

CONFIG_PATH = Path(__file__).with_name("scanner_config.json")
ALLOWED_PLACEHOLDERS = {"code", "label", "date", "episode", "section", "tag"}
REQUIRED_DOC_TYPE_FIELDS = {"key", "label", "code", "template"}


@dataclass
class FolderContext:
    date: str = ""
    episode: str = ""
    tags: list[str] | None = None
    section: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "date": self.date,
            "episode": self.episode,
            "section": self.section,
        }


DEFAULT_CONFIG = {
    "scan_command": "",  # Example: "naps2.console --output \"{output_path}\""
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
SECTION_RE = re.compile(r"^(?P<section>\d{2})(?:[_.\s-].*)?$")
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_config(cfg: dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


def sanitize_part(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value)
    value = re.sub(r"\s+", " ", value)
    return value


def extract_placeholders(template: str) -> set[str]:
    return {match for match in PLACEHOLDER_RE.findall(template)}


def validate_template(template: str) -> str | None:
    unknown = sorted(extract_placeholders(template) - ALLOWED_PLACEHOLDERS)
    if unknown:
        return f"Невідомі плейсхолдери: {', '.join(unknown)}"

    formatter = string.Formatter()
    try:
        for _, field_name, _, _ in formatter.parse(template):
            if field_name:
                # already validated by regex/allow-list; this call catches malformed braces
                continue
    except ValueError as exc:
        return f"Некоректний шаблон: {exc}"

    return None


def validate_doc_types(doc_types: list[dict[str, Any]]) -> str | None:
    if not isinstance(doc_types, list) or not doc_types:
        return "doc_types має бути непорожнім масивом"

    for idx, item in enumerate(doc_types, start=1):
        if not isinstance(item, dict):
            return f"Елемент #{idx} у doc_types має бути об'єктом"
        missing = REQUIRED_DOC_TYPE_FIELDS - set(item)
        if missing:
            return f"Тип документа #{idx}: бракує полів: {', '.join(sorted(missing))}"
        template_error = validate_template(str(item.get("template", "")))
        if template_error:
            return f"Тип документа #{idx} ({item.get('key', '?')}): {template_error}"

    return None


def parse_context(folder: Path) -> FolderContext:
    tags: list[str] = []
    date = ""
    episode = ""
    section = ""

    lineage = [folder] + list(folder.parents)

    for part in lineage:
        top_match = TOP_FOLDER_RE.match(part.name)
        if not top_match:
            continue
        date = top_match.group("date")
        episode = top_match.group("episode")
        suffix = top_match.group("rest")
        suffix_parts = suffix.split("_")
        candidate = suffix_parts[-1] if suffix_parts else ""
        tags = [sanitize_part(x) for x in candidate.split("+") if sanitize_part(x)]
        break

    for part in lineage:
        section_match = SECTION_RE.match(part.name)
        if section_match:
            section = section_match.group("section")
            break

    return FolderContext(date=date, episode=episode, tags=tags, section=section)


def build_filename(doc_type: dict[str, Any], ctx: FolderContext, tag: str) -> str:
    tpl = str(doc_type.get("template", "{code}_{label}_{date}_{episode}_{tag}"))
    values = {
        "code": sanitize_part(str(doc_type.get("code", "000"))),
        "label": sanitize_part(str(doc_type.get("label", "документ"))),
        "tag": sanitize_part(tag),
        **{k: sanitize_part(v) for k, v in ctx.as_dict().items()},
    }
    name = tpl.format(**values)
    name = re.sub(r"_+", "_", name)
    return name.strip("_ ")


def missing_context_fields(doc_type: dict[str, Any], ctx: FolderContext, tag: str) -> list[str]:
    template = str(doc_type.get("template", ""))
    placeholders = extract_placeholders(template)

    values = {
        "date": ctx.date,
        "episode": ctx.episode,
        "section": ctx.section,
        "tag": tag,
    }
    return sorted([key for key in (placeholders & set(values)) if not sanitize_part(values[key])])


def format_context_warnings(ctx: FolderContext) -> list[str]:
    warnings: list[str] = []
    if not ctx.date:
        warnings.append("Дата не знайдена")
    if not ctx.episode:
        warnings.append("Епізод не знайдений")
    if not ctx.section:
        warnings.append("Секція не знайдена")
    if not ctx.tags:
        warnings.append("Теги/підрозділи не знайдені")
    return warnings


def find_available_copy_path(target: Path) -> Path:
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    parent = target.parent

    index = 2
    while True:
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def resolve_output_path_conflict(target: Path) -> Path | None:
    if not target.exists():
        return target

    answer = messagebox.askyesnocancel(
        "Файл вже існує",
        f"Файл вже існує:\n{target}\n\n"
        "Так — Перезаписати\n"
        "Ні — Створити копію\n"
        "Скасувати — відмінити сканування",
    )
    if answer is None:
        return None
    if answer:
        return target
    return find_available_copy_path(target)


def run_scan(cmd_template: str, output_path: Path) -> tuple[str, str]:
    cmd = cmd_template.format(output_path=str(output_path))
    completed = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    return cmd, (completed.stdout or completed.stderr or "").strip()


class ScannerUI:
    def __init__(self, cwd: Path):
        self.cwd = cwd
        self.config = load_config()
        self.ctx = parse_context(cwd)

        self.root = Tk()
        self.root.title("TC Scanner")
        self.root.geometry("830x500")

        self.doc_types = self.config.get("doc_types", [])
        self.current_doc: dict[str, Any] | None = None

        self.tag_var = StringVar(self.root)
        tags = self.ctx.tags or [""]
        self.tag_var.set(tags[0])

        self.preview_var = StringVar(self.root)
        self.custom_name_var = StringVar(self.root)
        self.context_var = StringVar(self.root)
        self.warning_var = StringVar(self.root)

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
        self.doc_list = Listbox(left, height=17)
        self.doc_list.pack(fill=BOTH, expand=True, pady=(6, 0), padx=(0, 10))
        for item in self.doc_types:
            self.doc_list.insert(END, f"{item.get('code','000')} — {item.get('label','Документ')}")
        self.doc_list.bind("<<ListboxSelect>>", lambda _: self._on_doc_changed())
        if self.doc_types:
            self.doc_list.selection_set(0)
            self._on_doc_changed()

        Label(right, text="Тег/підрозділ:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tags = self.ctx.tags or ["(не знайдено)"]
        OptionMenu(right, self.tag_var, *tags, command=lambda _: self._refresh_preview()).pack(fill="x", pady=(6, 10))

        Label(right, text="Ручна назва (опціонально):", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.name_entry = Entry(right, textvariable=self.custom_name_var)
        self.name_entry.pack(fill="x", pady=(6, 2))
        self.custom_name_var.trace_add("write", lambda *_: self._refresh_preview())

        Label(right, text="Прев'ю повного шляху:").pack(anchor="w", pady=(8, 0))
        Label(right, textvariable=self.preview_var, wraplength=420, justify=LEFT, fg="#0b5").pack(anchor="w")

        Label(right, text="Розпізнаний контекст:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        Label(right, textvariable=self.context_var, justify=LEFT, wraplength=420).pack(anchor="w")
        Label(right, textvariable=self.warning_var, justify=LEFT, wraplength=420, fg="#b00").pack(anchor="w", pady=(6, 0))

        btns = Frame(right)
        btns.pack(fill="x", side=TOP, pady=(16, 0))
        Button(btns, text="Сканувати", command=self._scan, bg="#2f7", font=("Segoe UI", 10, "bold")).pack(side=LEFT)
        Button(btns, text="Налаштування", command=self._settings).pack(side=LEFT, padx=8)
        Button(btns, text="Вихід", command=self.root.destroy).pack(side=RIGHT)

    def _context_text(self) -> str:
        tags = ", ".join(self.ctx.tags or []) or "—"
        return (
            f"date: {self.ctx.date or '—'}\n"
            f"episode: {self.ctx.episode or '—'}\n"
            f"section: {self.ctx.section or '—'}\n"
            f"tags: {tags}"
        )

    def _on_doc_changed(self) -> None:
        idxs = self.doc_list.curselection()
        if not idxs:
            self.current_doc = None
            return
        self.current_doc = self.doc_types[idxs[0]]
        self._refresh_preview()

    def _selected_tag(self) -> str:
        return "" if self.tag_var.get() == "(не знайдено)" else self.tag_var.get()

    def _effective_name(self) -> str:
        if not self.current_doc:
            return ""
        auto_name = build_filename(self.current_doc, self.ctx, self._selected_tag())
        manual = sanitize_part(self.custom_name_var.get())
        return manual or auto_name

    def _refresh_preview(self) -> None:
        if not self.current_doc:
            return

        ext = self.config.get("output_extension", "pdf")
        self.preview_var.set(str(self.cwd / f"{self._effective_name()}.{ext}"))
        self.context_var.set(self._context_text())

        warnings = format_context_warnings(self.ctx)
        missing = missing_context_fields(self.current_doc, self.ctx, self._selected_tag())
        if missing:
            warnings.append(f"Для шаблону бракує: {', '.join(missing)}")

        self.warning_var.set("\n".join(f"⚠ {w}" for w in warnings) if warnings else "")

    def _scan(self) -> None:
        if not self.current_doc:
            messagebox.showerror("Помилка", "Оберіть тип документа")
            return

        cmd_template = self.config.get("scan_command", "").strip()
        if not cmd_template:
            messagebox.showerror("Помилка", "Не налаштована команда сканування")
            return

        missing = missing_context_fields(self.current_doc, self.ctx, self._selected_tag())
        if missing:
            messagebox.showerror(
                "Помилка",
                "Неможливо сканувати: для цього шаблону бракує даних:\n"
                f"{', '.join(missing)}",
            )
            return

        output_path = self.cwd / f"{self._effective_name()}.{self.config.get('output_extension', 'pdf')}"
        resolved_path = resolve_output_path_conflict(output_path)
        if resolved_path is None:
            return

        try:
            command, output = run_scan(cmd_template, resolved_path)
            details = f"\n\nВивід команди:\n{output}" if output else ""
            messagebox.showinfo("Готово", f"Файл створено:\n{resolved_path}{details}")
        except (subprocess.CalledProcessError, OSError, KeyError) as exc:
            attempted_cmd = ""
            try:
                attempted_cmd = cmd_template.format(output_path=str(resolved_path))
            except Exception:  # noqa: BLE001
                attempted_cmd = cmd_template
            messagebox.showerror(
                "Помилка сканування",
                "Не вдалося запустити команду сканування.\n\n"
                f"Куди писали: {resolved_path}\n"
                f"Команда: {attempted_cmd}\n"
                f"Помилка: {exc}",
            )

    def _settings(self) -> None:
        wnd = Toplevel(self.root)
        wnd.title("Налаштування")
        wnd.geometry("820x600")

        Label(wnd, text="Команда сканування (використовуйте {output_path}):").pack(anchor="w", padx=10, pady=(10, 2))
        cmd_var = StringVar(wnd, self.config.get("scan_command", ""))
        Entry(wnd, textvariable=cmd_var).pack(fill="x", padx=10)

        Label(wnd, text="Типи документів (JSON масив):").pack(anchor="w", padx=10, pady=(10, 2))
        txt = Text(wnd, height=22)
        txt.pack(fill=BOTH, expand=True, padx=10)
        txt.insert("1.0", json.dumps(self.config.get("doc_types", []), ensure_ascii=False, indent=2))

        Label(
            wnd,
            text="Плейсхолдери: {code}, {label}, {date}, {episode}, {section}, {tag}",
            justify=LEFT,
            fg="#444",
        ).pack(anchor="w", padx=10, pady=(6, 0))

        def save() -> None:
            docs_text = txt.get("1.0", "end").strip()
            try:
                docs = json.loads(docs_text)
            except json.JSONDecodeError as exc:
                messagebox.showerror("Помилка JSON", f"Некоректний JSON:\n{exc}")
                return

            validation_error = validate_doc_types(docs)
            if validation_error:
                messagebox.showerror("Помилка валідації", validation_error)
                return

            self.config["doc_types"] = docs
            self.config["scan_command"] = cmd_var.get().strip()
            save_config(self.config)
            self.doc_types = docs
            self.doc_list.delete(0, END)
            for item in self.doc_types:
                self.doc_list.insert(END, f"{item.get('code','000')} — {item.get('label','Документ')}")
            if self.doc_types:
                self.doc_list.selection_set(0)
                self._on_doc_changed()
            messagebox.showinfo("OK", "Налаштування збережено")
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
