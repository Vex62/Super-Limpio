"""Tema visual: barra lateral oscura tipo CCleaner + área de contenido tipo Explorador."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from ..safety import Risk

# Paleta
SIDEBAR_BG = "#18202e"
SIDEBAR_HOVER = "#222c3e"
SIDEBAR_ACTIVE = "#2a3650"
SIDEBAR_FG = "#b9c3d6"
SIDEBAR_FG_ACTIVE = "#ffffff"
ACCENT = "#2fb36b"          # verde «limpieza»
ACCENT_DARK = "#24965a"
ACCENT_SOFT = "#e5f6ec"
BG = "#f3f4f7"
CARD = "#ffffff"
BORDER = "#dde1e8"
TEXT = "#1d2433"
MUTED = "#6a7387"
INFO = "#2f6fdb"
WARN = "#e3962b"
DANGER = "#d64545"
DANGER_DARK = "#b83636"
SELECT = "#cce4f7"          # azul de selección del Explorador

ROW_HUGE = "#fde3e3"        # >= 10 GB
ROW_BIG = "#fff0da"         # >= 1 GB
ROW_MID = "#fffaeb"         # >= 100 MB

RISK_COLORS = {
    Risk.BAJO: ("#2fb36b", "#e5f6ec"),
    Risk.MEDIO: ("#2f6fdb", "#e6eefc"),
    Risk.ALTO: ("#e3962b", "#fdf1df"),
    Risk.CRITICO: ("#d64545", "#fbe5e5"),
}

# Glifos de «Segoe Fluent Icons» / «Segoe MDL2 Assets» (incluidas en Windows 11)
GLYPHS = {
    "home": "", "drive": "", "apps": "", "memory": "",
    "startup": "", "clean": "", "code": "", "tools": "",
    "log": "", "folder": "", "shield": "", "warning": "",
}
FALLBACK_GLYPHS = {
    "home": "⌂", "drive": "◫", "apps": "▦", "memory": "▤", "startup": "⏻", "clean": "✧",
    "code": "‹›", "tools": "⚙", "log": "≡", "folder": "▭", "shield": "◈", "warning": "!",
}


class Fonts:
    def __init__(self, root: tk.Misc):
        fams = set(tkfont.families(root))
        base = "Segoe UI" if "Segoe UI" in fams else "TkDefaultFont"
        semi = "Segoe UI Semibold" if "Segoe UI Semibold" in fams else base
        mono = "Cascadia Mono" if "Cascadia Mono" in fams else ("Consolas" if "Consolas" in fams else "TkFixedFont")
        self.icon_family = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in fams), None)
        self.base = (base, 10)
        self.small = (base, 9)
        self.bold = (semi, 10)
        self.h1 = (semi, 17)
        self.h2 = (semi, 12)
        self.big = (semi, 22)
        self.mono = (mono, 9)
        self.brand = (semi, 14)
        self.icon = (self.icon_family, 13) if self.icon_family else (base, 12)

    def glyph(self, name: str) -> str:
        return (GLYPHS if self.icon_family else FALLBACK_GLYPHS).get(name, "•")


def scale_factor(root: tk.Misc) -> float:
    try:
        return max(1.0, root.winfo_fpixels("1i") / 96.0)
    except tk.TclError:
        return 1.0


def apply_style(root: tk.Tk, fonts: Fonts, sf: float) -> ttk.Style:
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=BG)
    root.option_add("*Font", fonts.base)
    root.option_add("*TCombobox*Listbox.font", fonts.base)

    style.configure(".", background=BG, foreground=TEXT, font=fonts.base,
                    bordercolor=BORDER, lightcolor=BG, darkcolor=BG, focuscolor=SELECT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=CARD)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED)
    style.configure("H1.TLabel", font=fonts.h1)
    style.configure("H2.TLabel", font=fonts.h2, background=CARD)
    style.configure("Big.TLabel", font=fonts.big, background=CARD, foreground=ACCENT_DARK)
    style.configure("TCheckbutton", background=CARD)
    style.configure("Bg.TCheckbutton", background=BG)

    pad = (int(12 * sf), int(6 * sf))
    style.configure("TButton", padding=pad, background="#ffffff", bordercolor=BORDER,
                    lightcolor="#ffffff", darkcolor="#ffffff", relief="flat")
    style.map("TButton", background=[("pressed", "#e4e8ef"), ("active", "#eef1f6"), ("disabled", "#f3f4f6")],
              foreground=[("disabled", "#a0a7b5")])
    for name, bg, dark in (("Accent", ACCENT, ACCENT_DARK), ("Danger", DANGER, DANGER_DARK),
                           ("Info", INFO, "#2559b5")):
        style.configure(f"{name}.TButton", background=bg, foreground="#ffffff", bordercolor=bg,
                        lightcolor=bg, darkcolor=bg, font=fonts.bold)
        style.map(f"{name}.TButton",
                  background=[("disabled", "#c9ced8"), ("pressed", dark), ("active", dark)],
                  foreground=[("disabled", "#f4f5f7")],
                  bordercolor=[("active", dark)])

    style.configure("TEntry", fieldbackground="#ffffff", padding=int(5 * sf), bordercolor=BORDER,
                    lightcolor="#ffffff")
    style.map("TEntry", bordercolor=[("focus", INFO)], lightcolor=[("focus", INFO)])
    style.configure("TCombobox", fieldbackground="#ffffff", padding=int(4 * sf), arrowsize=int(12 * sf))

    rowh = int(26 * sf)
    style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground=TEXT,
                    rowheight=rowh, bordercolor=BORDER, borderwidth=1, font=fonts.base)
    style.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", background="#ffffff", foreground=MUTED, relief="flat",
                    font=fonts.small, padding=(int(6 * sf), int(5 * sf)), bordercolor=BORDER,
                    lightcolor="#ffffff", darkcolor=BORDER)
    style.map("Treeview.Heading", background=[("active", "#eef3fb")])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", padding=(int(14 * sf), int(6 * sf)), background=BG,
                    foreground=MUTED, borderwidth=0, font=fonts.bold)
    style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", TEXT)],
              expand=[("selected", (0, 0, 0, 0))])

    style.configure("Horizontal.TProgressbar", troughcolor="#e6e9ef", background=ACCENT,
                    bordercolor="#e6e9ef", lightcolor=ACCENT, darkcolor=ACCENT,
                    thickness=int(6 * sf))
    style.configure("Vertical.TScrollbar", background="#e9ecf1", troughcolor="#ffffff",
                    bordercolor="#ffffff", arrowcolor=MUTED, gripcount=0, arrowsize=int(12 * sf))
    style.configure("Horizontal.TScrollbar", background="#e9ecf1", troughcolor="#ffffff",
                    bordercolor="#ffffff", arrowcolor=MUTED, gripcount=0, arrowsize=int(12 * sf))
    style.configure("TLabelframe", background=CARD, bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=CARD, foreground=MUTED, font=fonts.bold)
    style.configure("TPanedwindow", background=BG)
    return style


def size_tag(size: int) -> str:
    if size >= 10 * 1024 ** 3:
        return "huge"
    if size >= 1024 ** 3:
        return "big"
    if size >= 100 * 1024 ** 2:
        return "mid"
    return ""


def configure_size_tags(tree: ttk.Treeview) -> None:
    tree.tag_configure("huge", background=ROW_HUGE)
    tree.tag_configure("big", background=ROW_BIG)
    tree.tag_configure("mid", background=ROW_MID)
    tree.tag_configure("muted", foreground=MUTED)
    tree.tag_configure("warn", foreground=DANGER)
