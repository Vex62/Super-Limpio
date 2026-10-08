"""Memoria y procesos: qué programas consumen RAM y CPU ahora mismo."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ... import winapi
from ...processes import ProcessMonitor, group_by_program
from ...safety import Risk, check_process_kill, log_action
from ...util import fmt_count, fmt_size
from .. import dialogs, theme
from ..widgets import ScrollTree, SortableTable, UsageBar
from .base import View


class MemoryView(View):
    title = "Memoria y procesos"
    subtitle = "Programas en ejecución ordenados por la memoria que reservan."
    icon = "memory"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.monitor = ProcessMonitor()
        self.busy = False
        self._after = None

        top = tk.Frame(self, bg=theme.CARD, highlightthickness=1, highlightbackground=theme.BORDER)
        top.pack(fill="x", pady=(0, self.px(10)))
        inner = tk.Frame(top, bg=theme.CARD)
        inner.pack(fill="x", padx=self.px(14), pady=self.px(10))
        self.ram_lbl = tk.Label(inner, text="RAM", font=self.fonts.h2, bg=theme.CARD, fg=theme.TEXT)
        self.ram_lbl.pack(anchor="w")
        self.ram_bar = UsageBar(inner, self.sf, height=12)
        self.ram_bar.pack(fill="x", pady=self.px(6))
        self.ram_txt = tk.Label(inner, text="", font=self.fonts.small, bg=theme.CARD, fg=theme.MUTED, anchor="w")
        self.ram_txt.pack(fill="x")

        bar = self.toolbar()
        ttk.Button(bar, text="Actualizar", command=self.refresh).pack(side="left")
        self.auto = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Actualizar cada 3 s", variable=self.auto, style="Bg.TCheckbutton",
                        command=self._schedule).pack(side="left", padx=self.px(10))
        self.grouped = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Agrupar por programa", variable=self.grouped, style="Bg.TCheckbutton",
                        command=self.refresh).pack(side="left")
        ttk.Label(bar, text="Buscar").pack(side="left", padx=(self.px(14), self.px(6)))
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *_: self.table.refresh())
        ttk.Entry(bar, textvariable=self.q, width=22).pack(side="left")
        ttk.Button(bar, text="Finalizar…", style="Danger.TButton", command=self.kill).pack(side="right")
        ttk.Button(bar, text="Abrir ubicación", command=self.open_location).pack(side="right", padx=self.px(6))

        cols = [("name", "Programa", 240, "w"), ("count", "Procesos", 75, "e"),
                ("private", "Memoria privada", 120, "e"), ("ws", "En RAM ahora", 110, "e"),
                ("cpu", "CPU", 70, "e"), ("threads", "Hilos", 70, "e"), ("path", "Ruta", 380, "w")]
        box = ScrollTree(self, cols, sf=self.sf)
        box.pack(fill="both", expand=True)
        self.tree = box.tree
        self.table = SortableTable(
            self.tree,
            render=lambda r: (r.name, fmt_count(r.count) if self.grouped.get() else str(r.pid),
                              fmt_size(r.private) if r.accessible else "sin acceso",
                              fmt_size(r.working_set) if r.accessible else "",
                              f"{r.cpu_pct:.1f} %".replace(".", ","), fmt_count(r.threads), r.path),
            sort_keys={"name": lambda r: r.name.lower(), "private": lambda r: r.private,
                       "ws": lambda r: r.working_set, "cpu": lambda r: r.cpu_pct, "count": lambda r: r.count},
            default_sort="private",
            tag_fn=lambda r: (_mem_tag(r.private),) if r.accessible else ("muted",),
            key_fn=lambda r: (r.path or r.name).lower() if self.grouped.get() else str(r.pid))
        self.table.filter_fn = self._match
        self.tree.tag_configure("m_huge", background=theme.ROW_HUGE)
        self.tree.tag_configure("m_big", background=theme.ROW_BIG)
        self.tree.tag_configure("m_mid", background=theme.ROW_MID)

        self.note(self, "«Memoria privada» es la memoria que el programa ha reservado solo para él (la cifra "
                        "que mejor indica su consumo). «En RAM ahora» es la parte que ocupa físicamente en este "
                        "momento. Los procesos del sistema sin acceso necesitan ejecutar como administrador.") \
            .pack(fill="x", pady=(self.px(6), 0))

    def _match(self, r) -> bool:
        q = self.q.get().strip().lower()
        return not q or q in r.name.lower() or q in (r.path or "").lower()

    def on_show(self) -> None:
        super().on_show()
        self.refresh()

    def on_hide(self) -> None:
        if self._after:
            self.after_cancel(self._after)
            self._after = None

    def _schedule(self) -> None:
        if self._after:
            self.after_cancel(self._after)
            self._after = None
        if self.auto.get() and self.app.current == "memory":
            self._after = self.after(3000, self.refresh)

    def refresh(self) -> None:
        if self.busy:
            return
        self.busy = True

        def work():
            procs = self.monitor.sample()
            return procs, winapi.memory_status()

        self.app.bg.run(work, on_done=self._render, on_error=lambda e: setattr(self, "busy", False))

    def _render(self, data) -> None:
        self.busy = False
        procs, mem = data
        procs = [p for p in procs if p.pid != 0]
        rows = group_by_program(procs) if self.grouped.get() else procs
        self.table.set_rows(rows)
        if mem:
            self.ram_bar.set(mem.used / mem.total if mem.total else 0)
            self.ram_lbl.configure(text=f"Memoria RAM · {mem.load_pct} % en uso")
            commit = ""
            if mem.commit_total:
                commit = (f" · Memoria comprometida (RAM + archivo de paginación): "
                          f"{fmt_size(mem.commit_total - mem.commit_available)} de {fmt_size(mem.commit_total)}")
            self.ram_txt.configure(text=f"{fmt_size(mem.used)} usados de {fmt_size(mem.total)} · "
                                        f"{fmt_size(mem.available)} disponibles{commit}")
        self.status(f"{len(procs)} procesos")
        self._schedule()

    def open_location(self) -> None:
        sel = self.table.selected()
        if sel and sel[0].path:
            winapi.open_in_explorer(sel[0].path)

    def kill(self) -> None:
        sel = self.table.selected()
        if not sel:
            return
        targets = []
        blocked = []
        risk = Risk.MEDIO
        reasons = set()
        for r in sel:
            for pid in r.pids:
                allowed, rk, why = check_process_kill(r.name, pid)
                if not allowed:
                    blocked.append(f"{r.name} (PID {pid}): {why}")
                    continue
                targets.append((pid, r.name))
                risk = max(risk, rk)
                reasons.add(why)
        if blocked and not targets:
            dialogs.error(self, "Protegido", "Super Limpio no finaliza procesos esenciales:\n\n" + "\n".join(blocked[:10]))
            return
        details = "\n".join(f"PID {pid:>6}  {name}" for pid, name in targets[:60])
        if len(targets) > 60:
            details += f"\n... y {len(targets) - 60} más"
        if blocked:
            details += "\n\nSe omitirán (protegidos):\n" + "\n".join(blocked[:10])
        msg = ("Se forzará el cierre de los procesos indicados (equivale a «Finalizar tarea»). "
               + " ".join(sorted(reasons)))
        if not dialogs.confirm(self, "Finalizar procesos", msg, details, risk=risk, ok_text="Finalizar"):
            return
        fails = []
        for pid, name in targets:
            ok, m = winapi.terminate_process(pid)
            log_action("finalizar_proceso", f"{name} ({pid})", m, ok=ok)
            if not ok:
                fails.append(f"{name} ({pid}): {m}")
        if fails:
            dialogs.error(self, "Algunos procesos no se cerraron", "\n".join(fails[:15]))
        self.status(f"{len(targets) - len(fails)} procesos finalizados")
        self.after(500, self.refresh)


def _mem_tag(b: int) -> str:
    if b >= 4 * 1024 ** 3:
        return "m_huge"
    if b >= 1024 ** 3:
        return "m_big"
    if b >= 300 * 1024 ** 2:
        return "m_mid"
    return ""

