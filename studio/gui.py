from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import profile
from .errors import StudioError
from .gui_logic import (ALL_COLUMNS, ANY_COLUMN, OPERATION_BY_LABEL, OPERATIONS, parse_number,
                        preview_rows, run_operation, summary_lines, valid_columns)
from .rules import RangeRule
from .session import DataSession

PREVIEW_LIMIT = 200
COLOR_OK, COLOR_ERROR, COLOR_INFO = "#1a7f37", "#c62828", "#555555"


def fill_tree(tree: ttk.Treeview, columns: list[str], rows: list[tuple], width: int = 110) -> None:
    tree.delete(*tree.get_children())
    tree["columns"] = columns
    tree["show"] = "headings"
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=width, minwidth=60, stretch=True, anchor="w")
    for row in rows:
        tree.insert("", "end", values=row)


def scrolled_tree(parent: tk.Widget, height: int = 12) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    tree = ttk.Treeview(frame, height=height)
    ys = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    xs = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
    tree.grid(row=0, column=0, sticky="nsew")
    ys.grid(row=0, column=1, sticky="ns")
    xs.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return tree


class StudioApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.session: DataSession | None = None

        self.status_var = tk.StringVar(value="Wczytaj plik CSV, aby rozpocząć.")
        self.file_var = tk.StringVar(value="(nie wczytano pliku)")
        self.show_raw_var = tk.BooleanVar(value=False)
        self.q_column_var, self.q_min_var, self.q_max_var = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.q_factor_var = tk.StringVar(value="1.5")
        self.op_var = tk.StringVar(value=OPERATIONS["duplicates"].label)
        self.option_var, self.column_var = tk.StringVar(), tk.StringVar()
        self.param_vars = {name: tk.StringVar() for name in ("min", "max", "value", "factor")}
        self.param_vars["factor"].set("1.5")

        self._build()
        self.refresh_all()

    def _build(self) -> None:
        self.root.title("Studio jakości danych")
        self.root.geometry("1000x650")
        self.root.minsize(800, 500)

        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")
        ttk.Button(top, text="Wczytaj CSV…", command=self.choose_file).pack(side="left")
        self.reset_btn = ttk.Button(top, text="Reset do danych surowych", command=self.reset)
        self.reset_btn.pack(side="left", padx=8)
        ttk.Label(top, textvariable=self.file_var, foreground=COLOR_INFO).pack(side="left", padx=8)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10)
        self._build_preview_tab()
        self._build_profile_tab()
        self._build_quality_tab()
        self._build_cleaning_tab()

        self.status_label = ttk.Label(self.root, textvariable=self.status_var, padding=(10, 6), foreground=COLOR_INFO)
        self.status_label.pack(fill="x")

    def _build_preview_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Podgląd")
        self.preview_info = ttk.Label(tab, text="")
        self.preview_info.pack(anchor="w", pady=(0, 6))
        self.preview_tree = scrolled_tree(tab, height=18)

    def _build_profile_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Profil")
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        self.summary_label = ttk.Label(bar, text="", justify="left")
        self.summary_label.pack(side="left", anchor="w")
        ttk.Checkbutton(bar, text="pokaż dane surowe", variable=self.show_raw_var,
                        command=self.refresh_profile).pack(side="right", anchor="n")
        self.profile_tree = scrolled_tree(tab, height=14)

    def _build_quality_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Jakość")
        form = ttk.Frame(tab)
        form.pack(fill="x", pady=(0, 6))
        ttk.Label(form, text="Reguła zakresu – kolumna:").grid(row=0, column=0, sticky="w")
        self.q_column_combo = ttk.Combobox(form, textvariable=self.q_column_var, state="readonly", width=16)
        self.q_column_combo.grid(row=0, column=1, padx=4)
        ttk.Label(form, text="min:").grid(row=0, column=2)
        ttk.Entry(form, textvariable=self.q_min_var, width=8).grid(row=0, column=3, padx=4)
        ttk.Label(form, text="max:").grid(row=0, column=4)
        ttk.Entry(form, textvariable=self.q_max_var, width=8).grid(row=0, column=5, padx=4)
        ttk.Label(form, text="IQR k:").grid(row=0, column=6, padx=(12, 0))
        ttk.Entry(form, textvariable=self.q_factor_var, width=6).grid(row=0, column=7, padx=4)
        self.q_btn = ttk.Button(form, text="Sprawdź reguły", command=self.check_quality)
        self.q_btn.grid(row=0, column=8, padx=8)
        ttk.Label(tab, text="Raport tylko wykrywa problemy – nie zmienia danych. Zmiany wykonuje się "
                            "w zakładce „Czyszczenie”.", foreground=COLOR_INFO).pack(anchor="w", pady=(0, 6))
        self.quality_tree = scrolled_tree(tab, height=14)

    def _build_cleaning_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(tab, text="Czyszczenie")
        form = ttk.Frame(tab)
        form.pack(fill="x")

        ttk.Label(form, text="Operacja:").grid(row=0, column=0, sticky="w", pady=3)
        self.op_combo = ttk.Combobox(form, textvariable=self.op_var, state="readonly", width=34,
                                     values=[spec.label for spec in OPERATIONS.values()])
        self.op_combo.grid(row=0, column=1, sticky="w", padx=4)
        self.op_combo.bind("<<ComboboxSelected>>", lambda _e: self.on_operation_change())

        self.option_label = ttk.Label(form, text="Wariant:")
        self.option_label.grid(row=1, column=0, sticky="w", pady=3)
        self.option_combo = ttk.Combobox(form, textvariable=self.option_var, state="readonly", width=34)
        self.option_combo.grid(row=1, column=1, sticky="w", padx=4)
        self.option_combo.bind("<<ComboboxSelected>>", lambda _e: self.on_option_change())

        ttk.Label(form, text="Kolumna:").grid(row=2, column=0, sticky="w", pady=3)
        self.column_combo = ttk.Combobox(form, textvariable=self.column_var, state="readonly", width=34)
        self.column_combo.grid(row=2, column=1, sticky="w", padx=4)

        self.param_widgets: dict[str, tuple[ttk.Label, ttk.Entry]] = {}
        labels = {"min": "Minimum:", "max": "Maksimum:", "value": "Wartość stała:", "factor": "Współczynnik IQR k:"}
        for i, name in enumerate(("min", "max", "value", "factor")):
            lbl = ttk.Label(form, text=labels[name])
            ent = ttk.Entry(form, textvariable=self.param_vars[name], width=12)
            lbl.grid(row=3 + i, column=0, sticky="w", pady=3)
            ent.grid(row=3 + i, column=1, sticky="w", padx=4)
            self.param_widgets[name] = (lbl, ent)

        self.apply_btn = ttk.Button(form, text="Wykonaj operację", command=self.apply_operation)
        self.apply_btn.grid(row=7, column=1, sticky="w", padx=4, pady=8)

        ttk.Label(tab, text="Dziennik zmian (ślad wszystkich operacji):").pack(anchor="w", pady=(6, 2))
        self.log_tree = scrolled_tree(tab, height=8)
        self.on_operation_change()

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(title="Wybierz plik CSV",
                                          filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")])
        if path:
            self.load_file(Path(path))

    def load_file(self, path: Path) -> bool:
        try:
            session = DataSession.from_csv(path)
        except StudioError as exc:
            self.show_error("Nie udało się wczytać pliku", exc)
            return False
        self.session = session
        self.file_var.set(f"{path.name}  –  {len(session.raw)} wierszy × {session.raw.shape[1]} kolumn")
        self.set_status(f"Wczytano {path.name}.", COLOR_OK)
        self.refresh_all()
        return True

    def reset(self) -> None:
        if self.session is None:
            return
        self.session.reset()
        self.set_status("Przywrócono dane surowe (dziennik zachowuje wpis o resecie).", COLOR_OK)
        self.refresh_all()

    def check_quality(self) -> None:
        if self.session is None:
            return
        try:
            rules = []
            column = self.q_column_var.get()
            low = parse_number(self.q_min_var.get(), "minimum", required=False)
            high = parse_number(self.q_max_var.get(), "maksimum", required=False)
            if column and (low is not None or high is not None):
                rules.append(RangeRule(column, low, high))
            factor = parse_number(self.q_factor_var.get() or "1.5", "współczynnik IQR")
            report = self.session.quality_report(rules, profile.numeric_columns(self.session.current), factor)
        except StudioError as exc:
            self.show_error("Niepoprawne parametry reguły", exc)
            return
        fill_tree(self.quality_tree, list(report.columns), [tuple(r) for r in report.itertuples(index=False)])
        self.set_status(f"Sprawdzono reguły jakości: {len(report)} pozycji.", COLOR_OK)

    def on_operation_change(self) -> None:
        spec = OPERATIONS[self.current_operation()]
        options = list(spec.options)
        self.option_combo.configure(values=options)
        self.option_var.set(options[0] if options else "")
        visible = bool(options)
        for widget in (self.option_label, self.option_combo):
            widget.grid() if visible else widget.grid_remove()
        self.on_option_change()

    def on_option_change(self) -> None:
        spec = OPERATIONS[self.current_operation()]
        shown = set(spec.params)
        if self.current_operation() == "fill" and self.option_var.get() != "stała wartość":
            shown.discard("value")
        for name, (lbl, ent) in self.param_widgets.items():
            for widget in (lbl, ent):
                widget.grid() if name in shown else widget.grid_remove()
        self.refresh_columns()

    def apply_operation(self) -> None:
        if self.session is None:
            return
        params = {name: var.get() for name, var in self.param_vars.items()}
        try:
            op = run_operation(self.session, self.current_operation(), self.column_var.get(),
                               self.option_var.get(), params)
        except StudioError as exc:
            self.show_error("Operacja niewykonana", exc)
            return
        self.set_status(f"✔ {op.nazwa}: {op.parametry} – zmienione rekordy: {op.zmienione_rekordy}, "
                        f"wiersze {op.wiersze_przed} → {op.wiersze_po}.", COLOR_OK)
        self.refresh_all()

    def current_operation(self) -> str:
        return OPERATION_BY_LABEL[self.op_var.get()]

    def refresh_all(self) -> None:
        has_data = self.session is not None
        for widget in (self.reset_btn, self.q_btn, self.apply_btn):
            widget.configure(state="normal" if has_data else "disabled")
        self.refresh_preview()
        self.refresh_profile()
        self.refresh_columns()
        self.refresh_log()
        if not has_data:
            fill_tree(self.quality_tree, [], [])

    def refresh_preview(self) -> None:
        if self.session is None:
            fill_tree(self.preview_tree, [], [])
            self.preview_info.configure(text="Brak danych.")
            return
        df = self.session.current
        fill_tree(self.preview_tree, [str(c) for c in df.columns], preview_rows(df, PREVIEW_LIMIT), width=95)
        shown = min(PREVIEW_LIMIT, len(df))
        self.preview_info.configure(text=f"Pokazano {shown} z {len(df)} wierszy (dane bieżące, po operacjach).")

    def refresh_profile(self) -> None:
        if self.session is None:
            self.summary_label.configure(text="")
            fill_tree(self.profile_tree, [], [])
            return
        self.summary_label.configure(text="\n".join(summary_lines(self.session)))
        df = self.session.raw if self.show_raw_var.get() else self.session.current
        prof = profile.column_profile(df).reset_index()
        rows = [tuple("" if v is None or v != v else v for v in r) for r in prof.itertuples(index=False)]
        fill_tree(self.profile_tree, list(prof.columns), rows, width=85)

    def refresh_columns(self) -> None:
        df = self.session.current if self.session else None
        numeric = [str(c) for c in profile.numeric_columns(df)] if df is not None else []
        self.q_column_combo.configure(values=[""] + numeric)
        if self.q_column_var.get() not in numeric:
            self.q_column_var.set("")

        columns = valid_columns(df, self.current_operation(), self.option_var.get())
        self.column_combo.configure(values=columns)
        if self.column_var.get() not in columns:
            default = columns[0] if columns and columns[0] in (ALL_COLUMNS, ANY_COLUMN) else ""
            self.column_var.set(default)

    def refresh_log(self) -> None:
        if self.session is None:
            fill_tree(self.log_tree, [], [])
            return
        log = self.session.log_frame()
        fill_tree(self.log_tree, list(log.columns), [tuple(r) for r in log.itertuples(index=False)], width=110)
        self.log_tree.column("parametry", width=330)

    def set_status(self, text: str, color: str = COLOR_INFO) -> None:
        self.status_var.set(text)
        self.status_label.configure(foreground=color)

    def show_error(self, title: str, exc: StudioError) -> None:
        self.set_status(f"✖ {exc.message}", COLOR_ERROR)
        messagebox.showerror(title, str(exc))


def run() -> None:
    root = tk.Tk()
    StudioApp(root)
    root.mainloop()