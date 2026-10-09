"""Programas instalados: tamaño declarado vs. tamaño real y desinstalación oficial."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk

from ... import i18n, programs, plat
from ...safety import Risk, log_action
from ...scanner import quick_folder_size
from ...util import fmt_size
from .. import dialogs, theme
from ..widgets import ScrollTree, SortableTable
from .base import View


class ProgramsView(View):
    icon = "apps"
    view_key = "programs"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.title = i18n.t("programs.title")
        self.subtitle = i18n.t("programs.subtitle")
        self.cancel_ev: threading.Event | None = None

        bar = self.toolbar()
        ttk.Label(bar, text=i18n.t("common.search")).pack(side="left", padx=(0, self.px(6)))
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(bar, textvariable=self.q, width=32).pack(side="left")
        ttk.Button(bar, text=i18n.t("common.refresh"), command=self.load).pack(side="left", padx=(self.px(8), 0))
        self.measure_btn = ttk.Button(bar, text=i18n.t("programs.measure"), style="Info.TButton",
                                      command=self.measure)
        self.measure_btn.pack(side="left", padx=(self.px(6), 0))
        self.uninstall_btn = ttk.Button(bar, text=i18n.t("programs.uninstall"), style="Danger.TButton",
                                        command=self.uninstall)
        self.uninstall_btn.pack(side="right")
        ttk.Button(bar, text=i18n.t("common.open_location"), command=self.open_location).pack(
            side="right", padx=self.px(6))
        if plat.capabilities()["apps_settings"]:
            ttk.Button(bar, text=i18n.t("programs.store_apps"),
                       command=plat.open_apps_settings).pack(side="right")

        self.summary = ttk.Label(self, text="", style="Muted.TLabel")
        self.summary.pack(anchor="w", pady=(0, self.px(6)))

        cols = [("name", i18n.t("programs.col.name"), 300, "w"), ("size", i18n.t("programs.col.real"), 100, "e"),
                ("declared", i18n.t("programs.col.declared"), 95, "e"),
                ("publisher", i18n.t("programs.col.publisher"), 180, "w"),
                ("version", i18n.t("programs.col.version"), 110, "w"),
                ("date", i18n.t("programs.col.installed"), 90, "w"),
                ("scope", i18n.t("programs.col.scope"), 120, "w"),
                ("path", i18n.t("programs.col.location"), 300, "w")]
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
        self.detail = tk.Label(det, text=i18n.t("programs.detail_hint"),
                               font=self.fonts.mono, bg=theme.CARD, fg=theme.MUTED, anchor="w", justify="left")
        self.detail.pack(fill="x", padx=self.px(12), pady=self.px(8))

    @staticmethod
    def _render(r) -> tuple:
        p: programs.Program = r["p"]
        real = fmt_size(p.real_size) if p.real_size is not None else ("…" if r.get("measuring") else "—")
        return (p.name, real, fmt_size(p.estimated_size) if p.estimated_size else "—", p.publisher,
                p.version, p.install_date, p.scope_label, r["loc"])

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
        self.status(i18n.t("programs.reading"))
        self.app.bg.run(programs.list_installed, on_done=self._loaded,
                        on_error=lambda e: dialogs.error(self, i18n.t("common.error"), str(e)))

    def _loaded(self, progs: list[programs.Program]) -> None:
        rows = [{"p": p, "loc": p.location_guess} for p in progs]
        self.table.set_rows(rows)
        self._update_summary()
        self.status(i18n.t("programs.found", n=len(rows)))

    def _update_summary(self) -> None:
        rows = [r for r in self.table.rows if self._match(r)]
        total = sum(r["p"].best_size for r in rows)
        measured = sum(1 for r in rows if r["p"].real_size is not None)
        self.summary.configure(
            text=i18n.t("programs.summary", n=len(rows), total=fmt_size(total), measured=measured))

    # -------------------------------------------------------------- medir
    def measure(self) -> None:
        if self.cancel_ev and not self.cancel_ev.is_set():
            self.cancel_ev.set()
            self.measure_btn.configure(text=i18n.t("programs.measure"))
            return
        rows = [r for r in self.table.rows if r["loc"]]
        if not rows:
            return
        self.cancel_ev = ev = threading.Event()
        self.measure_btn.configure(text=i18n.t("programs.measure_stop"))
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

        self.app.bg.run(work, on_done=lambda _r: self._measure_end(ev), on_error=lambda _e: self._measure_end(ev))

    def _measured(self, r, size: int, i: int, n: int) -> None:
        r["p"].real_size = size
        r["measuring"] = False
        if i % 5 == 0 or i == n:
            self.table.refresh()
            self._update_summary()
        self.status(i18n.t("programs.measuring", i=i, n=n, name=r['p'].name))

    def _measure_end(self, ev: threading.Event) -> None:
        if self.cancel_ev is not None and self.cancel_ev is not ev:
            return   # se detuvo y ya hay otra medición en marcha: esa es la que manda
        for r in self.table.rows:
            r["measuring"] = False
        self.cancel_ev = None
        self.measure_btn.configure(text=i18n.t("programs.measure"))
        self.table.refresh()
        self._update_summary()
        self.status(i18n.t("programs.measure_done"))

    # ------------------------------------------------------------ acciones
    def _on_select(self, _e=None) -> None:
        sel = self.table.selected()
        if not sel:
            return
        p = sel[0]["p"]
        plan = programs.build_uninstall_plan(p)
        self.detail.configure(text=i18n.t("programs.detail", cmd=plan.display, key=p.reg_key), fg=theme.TEXT)

    def open_location(self) -> None:
        sel = self.table.selected()
        if sel and sel[0]["loc"]:
            plat.open_in_explorer(sel[0]["loc"])
        elif sel:
            self.status(i18n.t("programs.no_location"))

    def uninstall(self) -> None:
        sel = self.table.selected()
        if not sel:
            dialogs.info(self, i18n.t("programs.uninstall").rstrip("…"), i18n.t("programs.select_one"))
            return
        if len(sel) > 1:
            dialogs.info(self, i18n.t("programs.uninstall").rstrip("…"), i18n.t("programs.one_at_a_time"))
            return
        p: programs.Program = sel[0]["p"]
        plan = programs.build_uninstall_plan(p)
        if not plan.exe:   # esta plataforma no tiene una vía oficial para quitarlo
            dialogs.info(self, i18n.t("programs.uninstall").rstrip("…"),
                         "\n\n".join(plan.warnings + ([plan.display] if plan.display else [])))
            return
        risk = Risk.CRITICO if plan.critical else Risk.ALTO
        details = i18n.t("programs.uninstall.detail", name=p.name, version=p.version,
                         publisher=p.publisher or "—", size=fmt_size(p.best_size), cmd=plan.display)
        if plan.warnings:
            details += i18n.t("programs.uninstall.warnings", items="\n".join(f"  • {w}" for w in plan.warnings))
        if not dialogs.confirm(
                self, i18n.t("programs.uninstall_dialog.title", name=p.name),
                i18n.t("programs.uninstall_dialog.body"),
                details, risk=risk, ok_text=i18n.t("programs.uninstall_dialog.ok")):
            return
        ok, msg = plat.shell_execute(plan.exe, plan.params or None, verb="open")
        log_action("desinstalar", p.name, f"{plan.display} -> {msg}", ok=ok)
        if ok:
            self.status(i18n.t("programs.uninstall.opened", name=p.name))
        else:
            dialogs.error(self, i18n.t("programs.uninstall.failed_title"),
                          i18n.t("programs.uninstall.failed_body", msg=msg))


def _date_key(s: str) -> str:
    # Las fechas de instalación ya vienen en ISO (aaaa-mm-dd), que ordena solo.
    return s
