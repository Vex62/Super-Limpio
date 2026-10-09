from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from ... import config
from .. import theme

if TYPE_CHECKING:  # pragma: no cover
    from ..app import App


class View(ttk.Frame):
    title = ""
    subtitle = ""
    icon = "home"
    view_key = ""

    def __init__(self, master, app: "App"):
        super().__init__(master, style="TFrame")
        self.app = app
        self.sf = app.sf
        self.fonts = app.fonts
        self._shown_once = False

    # Se llama cada vez que se muestra la vista
    def on_show(self) -> None:
        if not self._shown_once:
            self._shown_once = True
            self.first_show()

    def first_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass

    # Utilidades
    def px(self, n: int | float) -> int:
        return int(n * self.sf)

    def toolbar(self, parent=None) -> ttk.Frame:
        bar = ttk.Frame(parent or self)
        bar.pack(fill="x", pady=(0, self.px(10)))
        return bar

    def status(self, text: str) -> None:
        self.app.set_status(text)

    def note(self, parent, text: str) -> tk.Label:
        return tk.Label(parent, text=text, bg=theme.BG, fg=theme.MUTED, font=self.fonts.small,
                        anchor="w", justify="left", wraplength=self.px(900))

    def persist_sash(self, pw: ttk.PanedWindow, name: str, default_px: int) -> None:
        """Recuerda y restaura la posición de un divisor arrastrable de esta vista."""
        key = self.view_key or type(self).__name__

        def restore():
            try:
                pw.sashpos(0, int(config.get_sash(key, name, self.px(default_px))))
            except tk.TclError:
                pass

        def save(_e=None):
            try:
                config.set_sash(key, name, pw.sashpos(0))
            except tk.TclError:
                pass

        pw.after(80, restore)
        pw.bind("<ButtonRelease-1>", save, add="+")
