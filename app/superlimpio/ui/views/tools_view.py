"""Herramientas del sistema: comandos oficiales de Windows con confirmación explícita."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ... import i18n
from ...safety import Risk
from ...systools import SysTool, run_tool, tools
from .. import dialogs, theme
from ..widgets import Card, badge, bind_wheel, risk_badge
from .base import View


class ToolsView(View):
    icon = "tools"
    view_key = "tools"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.title = i18n.t("tools.title")
        self.subtitle = i18n.t("tools.subtitle")
        canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        holder = ttk.Frame(canvas)
        holder.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=holder, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        bind_wheel(canvas)

        for tool in tools():
            card = Card(holder, self.sf, padding=12)
            card.pack(fill="x", pady=(0, self.px(8)), padx=(0, self.px(8)))
            top = tk.Frame(card.inner, bg=theme.CARD)
            top.pack(fill="x")
            tk.Label(top, text=tool.title, font=self.fonts.h2, bg=theme.CARD, fg=theme.TEXT).pack(side="left")
            risk_badge(top, tool.risk, self.fonts.small).pack(side="left", padx=self.px(10))
            if tool.admin:
                badge(top, i18n.t("tools.requires_admin"), theme.WARN, "#fdf1df",
                      self.fonts.small).pack(side="left")
            ttk.Button(top, text=i18n.t("tools.run") if tool.risk > Risk.BAJO else i18n.t("tools.open"),
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
                msg += i18n.t("tools.admin_note")
            if not dialogs.confirm(self, tool.title, msg, tool.command_line, risk=tool.risk,
                                   ok_text=i18n.t("tools.run_btn")):
                return
        ok, m = run_tool(tool)
        self.status(i18n.t("tools.status", title=tool.title, msg=m))
        if not ok:
            dialogs.error(self, tool.title, m)
