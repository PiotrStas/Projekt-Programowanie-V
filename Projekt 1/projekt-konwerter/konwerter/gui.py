"""Interfejs graficzny (Tkinter/ttk) – Lab 4.

GUI nie zawiera żadnej logiki konwersji. Korzysta wyłącznie z rdzenia:
- available_targets()  -> jakie formaty pokazać na liście,
- ConversionRequest    -> walidacja i planowana nazwa wyniku,
- execute()            -> sama konwersja (w wątku roboczym).

Funkcje pomocnicze na górze pliku nie używają okna, więc da się je testować automatycznie.
"""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import ConversionRequest, available_targets, execute, supported_pairs
from .errors import ConversionError

log = logging.getLogger(__name__)

APP_TITLE = "Uniwersalny konwerter plików"
POLL_MS = 100          # co ile ms okno sprawdza, czy wątek roboczy skończył
COLOR_OK = "#1a7f37"
COLOR_ERROR = "#c62828"
COLOR_INFO = "#555555"


# ---------------------------------------------------------------- logika bez okna

def source_formats() -> list[str]:
    """Formaty, które da się wybrać jako wejście (z rejestru, bez wpisywania na sztywno)."""
    return sorted({src for src, _ in supported_pairs()})


def file_types() -> list[tuple[str, str]]:
    """Filtry do okna 'Otwórz': najpierw wszystkie obsługiwane, potem każdy format osobno."""
    formats = source_formats()
    all_patterns = " ".join(f"*.{f}" for f in formats)
    return (
        [("Wszystkie obsługiwane", all_patterns)]
        + [(f.upper(), f"*.{f}") for f in formats]
        + [("Wszystkie pliki", "*.*")]
    )


def targets_for(source: str) -> list[str]:
    """Formaty docelowe dla tekstu z pola 'Plik wejściowy' (pusty tekst -> brak)."""
    if not source.strip():
        return []
    return available_targets(Path(source))


def planned_output(source: str, output_dir: str, target: str) -> Path | None:
    """Ścieżka wyniku, jeśli wszystkie pola są wypełnione – do podglądu w oknie."""
    if not (source.strip() and output_dir.strip() and target.strip()):
        return None
    return ConversionRequest(Path(source), target, Path(output_dir)).planned_output()


def can_convert(source: str, output_dir: str, target: str, busy: bool) -> bool:
    """Czy przycisk 'Konwertuj' ma być aktywny."""
    return (
        not busy
        and bool(source.strip() and output_dir.strip())
        and target in targets_for(source)
    )


def unsupported_message(source: str) -> str:
    ext = Path(source).suffix.lower() or "(brak rozszerzenia)"
    return f"Nieobsługiwany typ pliku: {ext}. Obsługiwane: {', '.join(source_formats())}."


def error_text(exc: ConversionError) -> str:
    return f"{exc.message}\n\nCo zrobić: {exc.hint}" if exc.hint else exc.message


def open_in_file_manager(path: Path) -> None:
    """Otwiera katalog w Eksploratorze / Finderze / menedżerze plików."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]  # tylko Windows
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


# ---------------------------------------------------------------- okno

class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.busy = False
        self.last_output_dir: Path | None = None
        self.results: queue.Queue = queue.Queue()  # wątek roboczy -> okno

        self.source_var = tk.StringVar()
        self.outdir_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.preview_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Wybierz plik do konwersji.")

        self._build()
        for var in (self.source_var, self.outdir_var, self.target_var):
            var.trace_add("write", lambda *_: self.refresh())
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()

    # ---------- budowa okna

    def _build(self) -> None:
        self.root.title(APP_TITLE)
        self.root.minsize(560, 0)

        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Plik wejściowy:").grid(row=0, column=0, sticky="w", pady=4)
        self.source_entry = ttk.Entry(frame, textvariable=self.source_var, state="readonly")
        self.source_entry.grid(row=0, column=1, sticky="ew", padx=8)
        self.source_btn = ttk.Button(frame, text="Wybierz…", command=self.choose_source)
        self.source_btn.grid(row=0, column=2)

        ttk.Label(frame, text="Katalog zapisu:").grid(row=1, column=0, sticky="w", pady=4)
        self.outdir_entry = ttk.Entry(frame, textvariable=self.outdir_var, state="readonly")
        self.outdir_entry.grid(row=1, column=1, sticky="ew", padx=8)
        self.outdir_btn = ttk.Button(frame, text="Wybierz…", command=self.choose_outdir)
        self.outdir_btn.grid(row=1, column=2)

        ttk.Label(frame, text="Format docelowy:").grid(row=2, column=0, sticky="w", pady=4)
        # readonly = można tylko wybrać z listy, nie da się wpisać niedozwolonego formatu
        self.target_combo = ttk.Combobox(frame, textvariable=self.target_var, state="disabled", width=12)
        self.target_combo.grid(row=2, column=1, sticky="w", padx=8)

        ttk.Label(frame, textvariable=self.preview_var, foreground=COLOR_INFO).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(8, 4)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 8))
        self.convert_btn = ttk.Button(buttons, text="Konwertuj", command=self.on_convert)
        self.convert_btn.grid(row=0, column=0)
        self.open_btn = ttk.Button(buttons, text="Otwórz katalog", command=self.open_output_dir, state="disabled")
        self.open_btn.grid(row=0, column=1, padx=8)

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew")

        ttk.Separator(frame).grid(row=6, column=0, columnspan=3, sticky="ew", pady=8)
        self.status_label = ttk.Label(frame, textvariable=self.status_var, foreground=COLOR_INFO, wraplength=520)
        self.status_label.grid(row=7, column=0, columnspan=3, sticky="w")

    # ---------- stan okna

    def set_status(self, text: str, color: str = COLOR_INFO) -> None:
        self.status_var.set(text)
        self.status_label.configure(foreground=color)

    def refresh(self) -> None:
        """Ustawia listę formatów, podgląd nazwy i aktywność przycisków na podstawie pól."""
        source = self.source_var.get()
        targets = targets_for(source)

        self.target_combo.configure(values=targets)
        current = self.target_var.get()
        if current not in targets:
            # zmiana pliku: stary format może być już niedozwolony; jedyny format wybieramy sam
            new = targets[0] if len(targets) == 1 else ""
            if new != current:
                self.target_var.set(new)
                return  # set() wywoła refresh() jeszcze raz
        self.target_combo.configure(state="readonly" if targets and not self.busy else "disabled")

        output = planned_output(source, self.outdir_var.get(), self.target_var.get())
        if output is None:
            self.preview_var.set("")
        elif output.exists():
            self.preview_var.set(f"Wynik: {output.name}   ⚠ plik już istnieje")
        else:
            self.preview_var.set(f"Wynik: {output.name}")

        ok = can_convert(source, self.outdir_var.get(), self.target_var.get(), self.busy)
        self.convert_btn.configure(state="normal" if ok else "disabled")

        state = "disabled" if self.busy else "normal"
        self.source_btn.configure(state=state)
        self.outdir_btn.configure(state=state)

    # ---------- akcje użytkownika

    def choose_source(self) -> None:
        path = filedialog.askopenfilename(title="Wybierz plik do konwersji", filetypes=file_types())
        if not path:
            return  # anulowano
        self.source_var.set(path)
        if not self.outdir_var.get():
            self.outdir_var.set(str(Path(path).parent))  # domyślnie obok pliku
        if targets_for(path):
            self.set_status("Wybierz format docelowy i kliknij „Konwertuj”.")
        else:
            self.set_status(unsupported_message(path), COLOR_ERROR)

    def choose_outdir(self) -> None:
        path = filedialog.askdirectory(title="Wybierz katalog zapisu", mustexist=True)
        if path:
            self.outdir_var.set(path)

    def on_convert(self) -> None:
        request = ConversionRequest(
            Path(self.source_var.get()), self.target_var.get(), Path(self.outdir_var.get())
        )
        try:
            request.validate()  # szybka kontrola przed startem (np. plik usunięty po wybraniu)
        except ConversionError as exc:
            self.show_error(exc)
            return

        target = request.planned_output()
        if target.exists():
            answer = messagebox.askyesnocancel(
                "Plik już istnieje",
                f"Plik {target.name} już istnieje w katalogu zapisu.\n\n"
                "Tak – nadpisz\nNie – zapisz pod nową nazwą, np. „nazwa (1)”\nAnuluj – przerwij",
            )
            if answer is None:
                self.set_status("Anulowano.")
                return
            request = ConversionRequest(request.source, request.target_format, request.output_dir, overwrite=answer)

        self.start_worker(request)

    def start_worker(self, request: ConversionRequest) -> None:
        self.busy = True
        self.refresh()
        self.open_btn.configure(state="disabled")
        self.progress.start(12)
        self.set_status(f"Konwertuję {request.source.name} → {request.target_format}…")

        def work() -> None:
            start = time.perf_counter()
            try:
                result = execute(request)
                self.results.put(("ok", result, time.perf_counter() - start))
            except ConversionError as exc:
                self.results.put(("error", exc, 0.0))
            except Exception as exc:  # execute() i tak opakowuje błędy – to tylko zabezpieczenie
                log.exception("Nieoczekiwany błąd w wątku roboczym")
                self.results.put(("error", ConversionError(f"Nieoczekiwany błąd: {exc}"), 0.0))

        # Tkinter wolno zmieniać tylko z głównego wątku – dlatego wątek roboczy wkłada wynik
        # do kolejki, a okno co POLL_MS ms sprawdza ją przez root.after().
        threading.Thread(target=work, daemon=True).start()
        self.root.after(POLL_MS, self.poll_worker)

    def poll_worker(self) -> None:
        try:
            kind, payload, seconds = self.results.get_nowait()
        except queue.Empty:
            self.root.after(POLL_MS, self.poll_worker)
            return

        self.busy = False
        self.progress.stop()
        self.progress.configure(value=0)
        if kind == "ok":
            self.last_output_dir = payload.parent
            self.open_btn.configure(state="normal")
            self.set_status(f"✔ Zapisano: {payload.name}  ({seconds:.1f} s)", COLOR_OK)
        else:
            self.show_error(payload)
        self.refresh()

    def show_error(self, exc: ConversionError) -> None:
        self.set_status(f"✖ {exc.message}", COLOR_ERROR)
        messagebox.showerror("Błąd konwersji", error_text(exc))

    def open_output_dir(self) -> None:
        if self.last_output_dir:
            open_in_file_manager(self.last_output_dir)

    def on_close(self) -> None:
        if self.busy and not messagebox.askyesno(
            "Konwersja w toku", "Konwersja jeszcze trwa. Zamknąć program mimo to?"
        ):
            return
        self.root.destroy()


def run() -> None:
    """Punkt wejścia GUI: python -m konwerter (bez argumentów)."""
    if sys.platform == "win32":
        try:  # ostry tekst na ekranach z powiększeniem (125%, 150%)
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()
