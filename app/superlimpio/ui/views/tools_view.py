"""Herramientas del sistema: comandos oficiales de Windows con confirmación explícita."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ...safety import Risk
from ...systools import TOOLS, SysTool, run_tool
from .. import dialogs, theme
from ..widgets import Card, badge, risk_badge
from .base import View


class ToolsView(View):
    title = "Herramientas del sistema"
    subtitle = "Accesos a herramientas oficiales de Windows. Ves el comando exacto antes de ejecutarlo."
    icon = "tools"

    def __init__(self, master, app):
        super().__init__(master, app)
        canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        holder = ttk.Frame(canvas)
        holder.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=holder, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<Enter>", lambda e: canvas.bind_all(
            "<MouseWheel>", lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        for tool in TOOLS:
            card = Card(holder, self.sf, padding=12)
            card.pack(fill="x", pady=(0, self.px(8)), padx=(0, self.px(8)))
            top = tk.Frame(card.inner, bg=theme.CARD)
            top.pack(fill="x")
            tk.Label(top, text=tool.title, font=self.fonts.h2, bg=theme.CARD, fg=theme.TEXT).pack(side="left")
            risk_badge(top, tool.risk, self.fonts.small).pack(side="left", padx=self.px(10))
            if tool.admin:
                badge(top, "Requiere administrador", theme.WARN, "#fdf1df", self.fonts.small).pack(side="left")
            ttk.Button(top, text="Ejecutar…" if tool.risk > Risk.BAJO else "Abrir",
                       style="Danger.TButton" if tool.risk >= Risk.CRITICO else "TButton",
                       command=lambda t=tool: self.run(t)).pack(side="right")
            tk.Label(card.inner, text=tool.description, font=self.fonts.base, bg=theme.CARD, fg=theme.MUTED,
                     anchor="w", justify="left", wraplength=self.px(820)).pack(fill="x", pady=(self.px(4), 0))
            tk.Label(card.inner, text=f"> {tool.command_line}", font=self.fonts.mono, bg="#f5f8f6",
                     fg=theme.TEXT, anchor="w", padx=6, pady=3).pack(fill="x", pady=(self.px(6), 0))

    def run(self, tool: SysTool) -> None:
        if tool.risk > Risk.BAJO:
            msg = tool.effect or tool.description
            if tool.admin:
                msg += ("\n\nWindows mostrará además el aviso de Control de cuentas de usuario (UAC). "
                        "La consola quedará abierta para que veas el resultado.")
            if not dialogs.confirm(self, tool.title, msg, tool.command_line, risk=tool.risk, ok_text="Ejecutar"):
                return
        ok, m = run_tool(tool)
        self.status(f"{tool.title}: {m}")
        if not ok:
            dialogs.error(self, tool.title, m)
