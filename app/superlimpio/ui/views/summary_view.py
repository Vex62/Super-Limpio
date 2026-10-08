from __future__ import annotations

import shutil
import tkinter as tk
from tkinter import ttk

from ... import winapi
from ...processes import ProcessMonitor, group_by_program
from ...util import fmt_size
from .. import theme
from ..widgets import Card, UsageBar
from .base import View


class SummaryView(View):
    title = "Resumen"
    subtitle = "Estado de tus unidades, memoria y papelera de un vistazo."
    icon = "home"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.grid_frame = ttk.Frame(self)
        self.grid_frame.pack(fill="both", expand=True)
        for c in range(3):
            self.grid_frame.columnconfigure(c, weight=1, uniform="col")

        # Unidades
        self.drives_card = Card(self.grid_frame, self.sf)
        self.drives_card.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=(0, self.px(12)),
                              pady=(0, self.px(12)))
        ttk.Label(self.drives_card.inner, text="Unidades", style="H2.TLabel").pack(anchor="w")
        self.drives_box = tk.Frame(self.drives_card.inner, bg=theme.CARD)
        self.drives_box.pack(fill="both", expand=True, pady=(self.px(8), 0))

        # Memoria
        self.mem_card = Card(self.grid_frame, self.sf)
        self.mem_card.grid(row=0, column=2, sticky="nsew", pady=(0, self.px(12)))
        ttk.Label(self.mem_card.inner, text="Memoria RAM", style="H2.TLabel").pack(anchor="w")
        self.mem_big = ttk.Label(self.mem_card.inner, text="—", style="Big.TLabel")
        self.mem_big.pack(anchor="w", pady=(self.px(6), 0))
        self.mem_bar = UsageBar(self.mem_card.inner, self.sf, height=10)
        self.mem_bar.pack(fill="x", pady=self.px(6))
        self.mem_txt = ttk.Label(self.mem_card.inner, text="", style="CardMuted.TLabel")
        self.mem_txt.pack(anchor="w")
        ttk.Label(self.mem_card.inner, text="Lo que más memoria usa ahora", style="CardMuted.TLabel").pack(
            anchor="w", pady=(self.px(12), self.px(4)))
        self.top_box = tk.Frame(self.mem_card.inner, bg=theme.CARD)
        self.top_box.pack(fill="x")
        ttk.Button(self.mem_card.inner, text="Ver procesos",
                   command=lambda: app.show("memory")).pack(anchor="w", pady=(self.px(10), 0))

        # Papelera + accesos rápidos
        self.bin_card = Card(self.grid_frame, self.sf)
        self.bin_card.grid(row=1, column=0, sticky="nsew", padx=(0, self.px(12)))
        ttk.Label(self.bin_card.inner, text="Papelera de reciclaje", style="H2.TLabel").pack(anchor="w")
        self.bin_lbl = ttk.Label(self.bin_card.inner, text="—", style="Big.TLabel")
        self.bin_lbl.pack(anchor="w", pady=self.px(6))
        ttk.Button(self.bin_card.inner, text="Ir a Limpieza",
                   command=lambda: app.show("cleaner")).pack(anchor="w")

        quick = Card(self.grid_frame, self.sf)
        quick.grid(row=1, column=1, columnspan=2, sticky="nsew")
        ttk.Label(quick.inner, text="Por dónde empezar", style="H2.TLabel").pack(anchor="w")
        tips = [
            ("Analizador de disco", "Descubre qué carpetas pesan más, ordenadas de mayor a menor.", "disk"),
            ("Programas", "Tamaño real en disco de cada programa y desinstalación oficial.", "programs"),
            ("Librerías de desarrollo", "node_modules, .venv, target… olvidados en proyectos viejos.", "devdeps"),
            ("Limpieza", "Temporales y cachés regenerables, al estilo CCleaner.", "cleaner"),
        ]
        for title, desc, key in tips:
            row = tk.Frame(quick.inner, bg=theme.CARD, cursor="hand2")
            row.pack(fill="x", pady=self.px(4))
            t = tk.Label(row, text=f"›  {title}", font=self.fonts.bold, bg=theme.CARD, fg=theme.INFO,
                         cursor="hand2")
            t.pack(side="left")
            d = tk.Label(row, text=f"  {desc}", font=self.fonts.base, bg=theme.CARD, fg=theme.MUTED)
            d.pack(side="left")
            for w in (row, t, d):
                w.bind("<Button-1>", lambda e, k=key: app.show(k))

        self.grid_frame.rowconfigure(0, weight=1)
        self.monitor = ProcessMonitor()

    def on_show(self) -> None:
        super().on_show()
        self.refresh()

    def refresh(self) -> None:
        self.app.bg.run(self._collect, on_done=self._render)

    def _collect(self):
        drives = []
        for d in winapi.list_drives():
            try:
                u = shutil.disk_usage(d)
                drives.append((d, u.total, u.used, u.free))
            except OSError:
                continue
        mem = winapi.memory_status()
        procs = group_by_program(self.monitor.sample())
        procs.sort(key=lambda p: p.private, reverse=True)
        rb = winapi.recycle_bin_info()
        return drives, mem, procs[:5], rb

    def _render(self, data) -> None:
        drives, mem, top, rb = data
        for w in self.drives_box.winfo_children():
            w.destroy()
        for d, total, used, free in drives:
            row = tk.Frame(self.drives_box, bg=theme.CARD)
            row.pack(fill="x", pady=self.px(6))
            tk.Label(row, image=self.app.icons["drive"], bg=theme.CARD).pack(side="left", padx=(0, 8))
            mid = tk.Frame(row, bg=theme.CARD)
            mid.pack(side="left", fill="x", expand=True)
            top_line = tk.Frame(mid, bg=theme.CARD)
            top_line.pack(fill="x")
            tk.Label(top_line, text=d, font=self.fonts.bold, bg=theme.CARD).pack(side="left")
            tk.Label(top_line, text=f"{fmt_size(free)} libres de {fmt_size(total)}", font=self.fonts.small,
                     bg=theme.CARD, fg=theme.MUTED).pack(side="right")
            bar = UsageBar(mid, self.sf, height=10)
            bar.pack(fill="x", pady=(self.px(3), 0))
            bar.set(used / total if total else 0)
            ttk.Button(row, text="Analizar",
                       command=lambda p=d: self._analyze(p)).pack(side="left", padx=(self.px(12), 0))
        if mem:
            self.mem_big.configure(text=f"{mem.load_pct} %")
            self.mem_bar.set(mem.used / mem.total if mem.total else 0)
            self.mem_txt.configure(text=f"{fmt_size(mem.used)} en uso de {fmt_size(mem.total)}")
        for w in self.top_box.winfo_children():
            w.destroy()
        for p in top:
            row = tk.Frame(self.top_box, bg=theme.CARD)
            row.pack(fill="x")
            name = p.name + (f"  ×{p.count}" if p.count > 1 else "")
            tk.Label(row, text=name, bg=theme.CARD, font=self.fonts.base, anchor="w").pack(side="left")
            tk.Label(row, text=fmt_size(p.private), bg=theme.CARD, fg=theme.MUTED,
                     font=self.fonts.base).pack(side="right")
        size, items = rb
        self.bin_lbl.configure(text=fmt_size(size))
        self.status(f"Papelera: {items} elementos · {len(drives)} unidades detectadas")

    def _analyze(self, path: str) -> None:
        self.app.show("disk")
        self.app.page("disk").start_scan(path)
