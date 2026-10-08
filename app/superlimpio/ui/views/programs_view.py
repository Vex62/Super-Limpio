"""Programas instalados: tamaño declarado vs. tamaño real y desinstalación oficial."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk

from ... import programs, winapi
from ...safety import Risk, log_action
from ...scanner import quick_folder_size
from ...util import fmt_size
from .. import dialogs, theme
from ..widgets import ScrollTree, SortableTable
from .base import View


class ProgramsView(View):
    title = "Programas"
    subtitle = "Programas instalados con su tamaño real en disco. La desinstalación usa el desinstalador oficial."
    icon = "apps"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.cancel_ev: threading.Event | None = None

        bar = self.toolbar()
        ttk.Label(bar, text="Buscar").pack(side="left", padx=(0, self.px(6)))
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(bar, textvariable=self.q, width=32).pack(side="left")
        ttk.Button(bar, text="Actualizar", command=self.load).pack(side="left", padx=(self.px(8), 0))
        self.measure_btn = ttk.Button(bar, text="Medir tamaño real", style="Info.TButton",
                                      command=self.measure)
        self.measure_btn.pack(side="left", padx=(self.px(6), 0))
        self.uninstall_btn = ttk.Button(bar, text="Desinstalar…", style="Danger.TButton",
                                        command=self.uninstall)
        self.uninstall_btn.pack(side="right")
        ttk.Button(bar, text="Abrir ubicación", command=self.open_location).pack(side="right", padx=self.px(6))
        ttk.Button(bar, text="Apps de Microsoft Store…",
                   command=lambda: winapi.shell_execute("ms-settings:appsfeatures")).pack(side="right")

        self.summary = ttk.Label(self, text="", style="Muted.TLabel")
        self.summary.pack(anchor="w", pady=(0, self.px(6)))

        cols = [("name", "Nombre", 300, "w"), ("size", "Tamaño real", 100, "e"),
                ("declared", "Declarado", 95, "e"), ("publisher", "Editor", 180, "w"),
                ("version", "Versión", 110, "w"), ("date", "Instalado", 90, "w"), ("scope", "Ámbito", 120, "w"),
                ("path", "Ubicación", 300, "w")]
        box = ScrollTree(self, cols, sf=self.sf)
        box.pack(fill="both", expand=True)
        self.tree = box.tree
        self.table = SortableTable(
            self.tree, render=self._render,
            sort_keys={"name": lambda r: r["p"].name.lower(), "size": lambda r: r["p"].best_size,
                       "declared": lambda r: r["p"].estimated_size, "publisher": lambda r: r["p"].publisher.lower(),
                       "date": lambda r: _date_key(r["p"].install_date), "scope": lambda r: r["p"].scope,
                       "path": lambda r: r["loc"].lower()},
            default_sort="size", tag_fn=lambda r: (theme.size_tag(r["p"].best_size),),
            key_fn=lambda r: r["p"].reg_key)
        self.table.filter_fn = self._match
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self.open_location())

        det = tk.Frame(self, bg=theme.CARD, highlightthickness=1, highlightbackground=theme.BORDER)
        det.pack(fill="x", pady=(self.px(8), 0))
        self.detail = tk.Label(det, text="Selecciona un programa para ver su comando de desinstalación.",
                               font=self.fonts.mono, bg=theme.CARD, fg=theme.MUTED, anchor="w", justify="left")
        self.detail.pack(fill="x", padx=self.px(12), pady=self.px(8))

    @staticmethod
    def _render(r) -> tuple:
        p: programs.Program = r["p"]
        real = fmt_size(p.real_size) if p.real_size is not None else ("…" if r.get("measuring") else "—")
        return (p.name, real, fmt_size(p.estimated_size) if p.estimated_size else "—", p.publisher,
                p.version, p.install_date, p.scope, r["loc"])

    def _match(self, r) -> bool:
        q = self.q.get().strip().lower()
        if not q:
            return True
        p = r["p"]
        return q in p.name.lower() or q in p.publisher.lower() or q in r["loc"].lower()

    def _apply_filter(self) -> None:
        self.table.refresh()
        self._update_summary()

    def first_show(self) -> None:
        self.load()

    def load(self) -> None:
        self.status("Leyendo programas instalados…")
        self.app.bg.run(programs.list_installed, on_done=self._loaded,
                        on_error=lambda e: dialogs.error(self, "Error", str(e)))

    def _loaded(self, progs: list[programs.Program]) -> None:
        rows = [{"p": p, "loc": p.location_guess} for p in progs]
        self.table.set_rows(rows)
        self._update_summary()
        self.status(f"{len(rows)} programas encontrados")

    def _update_summary(self) -> None:
        rows = [r for r in self.table.rows if self._match(r)]
        total = sum(r["p"].best_size for r in rows)
        measured = sum(1 for r in rows if r["p"].real_size is not None)
        self.summary.configure(
            text=f"{len(rows)} programas · {fmt_size(total)} en total · {measured} medidos en disco. "
                 "«Declarado» es lo que dice el instalador (a menudo inexacto); «Tamaño real» se mide "
                 "recorriendo la carpeta del programa.")

    # -------------------------------------------------------------- medir
    def measure(self) -> None:
        if self.cancel_ev and not self.cancel_ev.is_set():
            self.cancel_ev.set()
            self.measure_btn.configure(text="Medir tamaño real")
            return
        rows = [r for r in self.table.rows if r["loc"]]
        if not rows:
            return
        self.cancel_ev = ev = threading.Event()
        self.measure_btn.configure(text="Detener medición")
        for r in rows:
            r["measuring"] = True
        self.table.refresh()

        def work():
            cache: dict[str, int] = {}
            for i, r in enumerate(rows):
                if ev.is_set():
                    break
                loc = r["loc"]
                key = os.path.normcase(loc)
                if key not in cache:
                    cache[key] = quick_folder_size(loc, ev)[0]
                size = cache[key]
                self.app.bg.call_in_ui(self._measured, r, size, i + 1, len(rows))
            return None

        self.app.bg.run(work, on_done=lambda _r: self._measure_end())

    def _measured(self, r, size: int, i: int, n: int) -> None:
        r["p"].real_size = size
        r["measuring"] = False
        if i % 5 == 0 or i == n:
            self.table.refresh()
            self._update_summary()
        self.status(f"Midiendo {i}/{n}: {r['p'].name}")

    def _measure_end(self) -> None:
        for r in self.table.rows:
            r["measuring"] = False
        self.cancel_ev = None
        self.measure_btn.configure(text="Medir tamaño real")
        self.table.refresh()
        self._update_summary()
        self.status("Medición terminada")

    # ------------------------------------------------------------ acciones
    def _on_select(self, _e=None) -> None:
        sel = self.table.selected()
        if not sel:
            return
        p = sel[0]["p"]
        plan = programs.build_uninstall_plan(p)
        self.detail.configure(text=f"Desinstalador: {plan.display}\nRegistro: {p.reg_key}", fg=theme.TEXT)

    def open_location(self) -> None:
        sel = self.table.selected()
        if sel and sel[0]["loc"]:
            winapi.open_in_explorer(sel[0]["loc"])
        elif sel:
            self.status("Este programa no declara su carpeta de instalación")

    def uninstall(self) -> None:
        sel = self.table.selected()
        if not sel:
            dialogs.info(self, "Desinstalar", "Selecciona un programa de la lista.")
            return
        if len(sel) > 1:
            dialogs.info(self, "Desinstalar", "Desinstala los programas de uno en uno: cada desinstalador "
                                              "tiene su propio asistente.")
            return
        p: programs.Program = sel[0]["p"]
        plan = programs.build_uninstall_plan(p)
        risk = Risk.CRITICO if any("revisa los parámetros" in w for w in plan.warnings) else Risk.ALTO
        details = (f"Programa:  {p.name} {p.version}\nEditor:    {p.publisher or '—'}\n"
                   f"Tamaño:    {fmt_size(p.best_size)}\nComando:   {plan.display}")
        if plan.warnings:
            details += "\n\nAvisos:\n" + "\n".join(f"  • {w}" for w in plan.warnings)
        if not dialogs.confirm(
                self, f"Desinstalar {p.name}",
                "Se abrirá el desinstalador oficial de este programa (el mismo que usa Configuración de Windows). "
                "Sigue sus pasos; Super Limpio no borra archivos ni claves por su cuenta.\n\n"
                "Consejo: crea un punto de restauración antes si es un programa importante "
                "(Herramientas del sistema).",
                details, risk=risk, ok_text="Abrir desinstalador"):
            return
        ok, msg = winapi.shell_execute(plan.exe, plan.params or None, verb="open")
        log_action("desinstalar", p.name, f"{plan.display} -> {msg}", ok=ok)
        if ok:
            self.status(f"Desinstalador de {p.name} abierto. Pulsa Actualizar cuando termine.")
        else:
            dialogs.error(self, "No se pudo abrir el desinstalador",
                          f"{msg}\n\nPrueba desde Configuración > Aplicaciones.")


def _date_key(s: str) -> str:
    # dd/mm/aaaa -> aaaammdd para ordenar
    if len(s) == 10 and s[2] == "/" and s[5] == "/":
        return s[6:] + s[3:5] + s[:2]
    return s
