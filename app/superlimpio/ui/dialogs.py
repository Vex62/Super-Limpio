"""Diálogos de confirmación explícita.

Toda acción que borre, desinstale, finalice procesos o ejecute comandos pasa
por `confirm()`. El botón por defecto es siempre «Cancelar». Según el riesgo:
  * Medio:   confirmación simple.
  * Alto:    además hay que marcar «He revisado...».
  * Crítico: además hay que escribir CONFIRMAR.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import i18n
from ..safety import Risk, confirm_word
from . import theme, winframe


class ConfirmDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str, message: str, details: str, risk: Risk,
                 ok_text: str, fonts: theme.Fonts, sf: float) -> None:
        super().__init__(parent)
        self.result = False
        self.risk = risk
        self.title(title)
        self.configure(bg=theme.CARD)
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        fg, soft = theme.RISK_COLORS[risk]
        pad = int(18 * sf)

        head = tk.Frame(self, bg=soft)
        head.pack(fill="x")
        tk.Frame(head, bg=fg, width=int(6 * sf)).pack(side="left", fill="y")
        tk.Label(head, text=fonts.glyph("warning" if risk >= Risk.ALTO else "shield"), font=fonts.icon,
                 bg=soft, fg=fg).pack(side="left", padx=(pad, 6), pady=pad)
        htxt = tk.Frame(head, bg=soft)
        htxt.pack(side="left", fill="x", expand=True, pady=int(12 * sf))
        tk.Label(htxt, text=title, font=fonts.h2, bg=soft, fg=theme.TEXT, anchor="w").pack(fill="x")
        tk.Label(htxt, text=i18n.t("dialog.risk_level", label=risk.label), font=fonts.small, bg=soft, fg=fg,
                 anchor="w").pack(fill="x")

        # Los botones se colocan antes que el cuerpo: si el diálogo no cabe entero en la
        # pantalla, lo que encoge es la lista de detalles y «Cancelar» sigue a la vista.
        btns = tk.Frame(self, bg=theme.CARD)
        btns.pack(side="bottom", fill="x", padx=pad, pady=pad)
        body = tk.Frame(self, bg=theme.CARD)
        body.pack(fill="both", expand=True, padx=pad, pady=(int(12 * sf), 0))
        tk.Label(body, text=message, font=fonts.base, bg=theme.CARD, fg=theme.TEXT, justify="left",
                 anchor="w", wraplength=int(560 * sf)).pack(fill="x")

        if details:
            tk.Label(body, text=i18n.t("dialog.exact_target"), font=fonts.small,
                     bg=theme.CARD, fg=theme.MUTED, anchor="w").pack(fill="x", pady=(int(10 * sf), 2))
            frame = tk.Frame(body, bg=theme.BORDER)
            frame.pack(fill="both", expand=True)
            lines = details.count("\n") + 1
            txt = tk.Text(frame, height=min(12, max(3, lines)), wrap="none", font=fonts.mono,
                          bg="#f5f8f6", fg=theme.TEXT, relief="flat", padx=8, pady=6,
                          width=80)
            sb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=sb.set)
            txt.insert("1.0", details)
            txt.configure(state="disabled")
            sb.pack(side="right", fill="y", padx=(0, 1), pady=1)
            txt.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)

        self.ack = tk.BooleanVar(value=False)
        self.word = tk.StringVar()
        if risk >= Risk.ALTO:
            tk.Checkbutton(body, text=i18n.t("dialog.ack"),
                           variable=self.ack, bg=theme.CARD, activebackground=theme.CARD,
                           font=fonts.base, command=self._update, anchor="w").pack(fill="x", pady=(10, 0))
        if risk >= Risk.CRITICO:
            row = tk.Frame(body, bg=theme.CARD)
            row.pack(fill="x", pady=(8, 0))
            tk.Label(row, text=i18n.t("dialog.critical_type", word=confirm_word()),
                     font=fonts.bold, bg=theme.CARD, fg=theme.DANGER).pack(side="left")
            ent = ttk.Entry(row, textvariable=self.word, width=14)
            ent.pack(side="left", padx=8)
            self.word.trace_add("write", lambda *_: self._update())

        btns.lift()   # tras el cuerpo en el orden de tabulación
        self.cancel_btn = ttk.Button(btns, text=i18n.t("common.cancel"), command=self._cancel)
        self.cancel_btn.pack(side="right")
        style = "Danger.TButton" if risk >= Risk.ALTO else "Accent.TButton"
        self.ok_btn = ttk.Button(btns, text=ok_text, style=style, command=self._ok)
        self.ok_btn.pack(side="right", padx=(0, 8))
        tk.Label(btns, text=i18n.t("dialog.nothing_without_permission"), font=fonts.small, bg=theme.CARD,
                 fg=theme.MUTED).pack(side="left")

        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._update()
        self.cancel_btn.focus_set()

        winframe.place_dialog(self, parent)
        self.grab_set()

    def _update(self) -> None:
        ok = True
        if self.risk >= Risk.ALTO and not self.ack.get():
            ok = False
        if self.risk >= Risk.CRITICO and self.word.get().strip().upper() != confirm_word().upper():
            ok = False
        self.ok_btn.state(["!disabled"] if ok else ["disabled"])

    def _ok(self) -> None:
        if "disabled" in self.ok_btn.state():
            return
        self.result = True
        self.destroy()

    def _cancel(self) -> None:
        self.result = False
        self.destroy()


def confirm(parent: tk.Misc, title: str, message: str, details: str = "", risk: Risk = Risk.MEDIO,
            ok_text: str | None = None, fonts: theme.Fonts | None = None, sf: float = 1.0) -> bool:
    app = getattr(parent.winfo_toplevel(), "_superlimpio_app", None)
    if fonts is None and app is not None:
        fonts, sf = app.fonts, app.sf
    dlg = ConfirmDialog(parent, title, message, details, risk, ok_text or i18n.t("common.continue"), fonts, sf)
    parent.wait_window(dlg)
    return dlg.result


def info(parent: tk.Misc, title: str, message: str) -> None:
    from tkinter import messagebox
    messagebox.showinfo(title, message, parent=parent.winfo_toplevel())


def error(parent: tk.Misc, title: str, message: str) -> None:
    from tkinter import messagebox
    messagebox.showerror(title, message, parent=parent.winfo_toplevel())


def summarize_paths(paths: list[str], sizes: list[int] | None = None, limit: int = 40) -> str:
    from ..util import fmt_size
    lines = []
    for i, p in enumerate(paths[:limit]):
        if sizes:
            lines.append(f"{fmt_size(sizes[i]):>10}  {p}")
        else:
            lines.append(p)
    if len(paths) > limit:
        lines.append(i18n.t("dialog.more_items", n=len(paths) - limit))
    return "\n".join(lines)
