"""Tema visual: barra lateral oscura tipo CCleaner + área de contenido tipo Explorador."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from ..safety import Risk

# Paleta de la marca (paleta.txt, los colores del logo)
BOSQUE = "#087C2A"          # color principal oscuro, contornos y profundidad
ESMERALDA = "#12A832"       # fondo principal del emblema y superficies verdes
LIMA = "#42D21C"            # reflejos y acentos luminosos
BLANCO = "#FFFFFF"          # letras, brillos y contraste
AGUA = "#65D9FF"            # chorros de agua y detalles de limpieza
PETROLEO = "#004D35"        # sombras y contornos gruesos

# Uso en la interfaz. Los tonos intermedios son mezclas de los seis de arriba.
SIDEBAR_BG = PETROLEO
SIDEBAR_HOVER = "#02593a"
SIDEBAR_ACTIVE = BOSQUE
SIDEBAR_FG = "#cfe8dc"
SIDEBAR_FG_ACTIVE = BLANCO
SIDEBAR_MUTED = "#8fc4ac"
ACCENT = ESMERALDA
ACCENT_DARK = BOSQUE
ACCENT_SOFT = "#e3f6e7"
HIGHLIGHT = LIMA            # marcador de la sección activa y avisos sobre fondo oscuro
BG = "#f2f6f3"
CARD = BLANCO
BORDER = "#d9e3dc"
TEXT = "#0d2b20"
MUTED = "#5f7268"
INFO = "#0e8fbf"            # azul agua oscurecido: sobre él se lee el texto blanco
INFO_DARK = "#0b759d"
WARN = "#e3962b"            # naranja y rojo no son de la marca: avisan de riesgo
DANGER = "#d64545"
DANGER_DARK = "#b83636"
SELECT = "#cdf2ff"          # fila seleccionada, azul agua claro

# Control de zoom de la barra lateral: segmentos verdes sobre el fondo petróleo
ZOOM_BORDER = BOSQUE
ZOOM_BTN = "#06663a"        # entre PETROLEO y BOSQUE
ZOOM_HOVER = ESMERALDA
ZOOM_OFF = "#4f8f76"        # signo apagado al llegar al límite

# Importancia para el sistema (criticality.Level): color del texto en tablas y avisos
LEVEL_COLORS = {0: MUTED, 1: "#b36b00", 2: INFO_DARK, 3: DANGER_DARK}

ROW_HUGE = "#fde3e3"        # >= 10 GB
ROW_BIG = "#fff0da"         # >= 1 GB
ROW_MID = "#fffaeb"         # >= 100 MB

RISK_COLORS = {
    Risk.BAJO: (ACCENT_DARK, ACCENT_SOFT),
    Risk.MEDIO: (INFO, "#e2f6fd"),
    Risk.ALTO: ("#e3962b", "#fdf1df"),
    Risk.CRITICO: ("#d64545", "#fbe5e5"),
}

# Glifos de «Segoe Fluent Icons» / «Segoe MDL2 Assets» (incluidas en Windows 11)
GLYPHS = {
    "home": "", "drive": "", "apps": "", "memory": "",
    "startup": "", "clean": "", "code": "", "tools": "",
    "log": "", "folder": "", "shield": "", "warning": "",
    "boost": "",
}
FALLBACK_GLYPHS = {
    "home": "⌂", "drive": "◫", "apps": "▦", "memory": "▤", "startup": "▷", "clean": "✧",
    "code": "‹›", "tools": "⚙", "log": "≡", "folder": "▭", "shield": "◈", "warning": "!",
    "boost": "↯",
}


class Fonts:
    def __init__(self, root: tk.Misc, zoom: float = 1.0) -> None:
        fams = set(tkfont.families(root))

        def pick(candidates: tuple[str, ...], default: str) -> str:
            return next((f for f in candidates if f in fams), default)

        # La primera de cada lista es la de Windows; las demás, las habituales en Linux y macOS.
        base = pick(("Segoe UI", "Noto Sans", "Ubuntu", "Cantarell", "DejaVu Sans", "Liberation Sans",
                     "Helvetica Neue", "Helvetica"), "TkDefaultFont")
        semi = pick(("Segoe UI Semibold", "Noto Sans Medium", "Ubuntu Medium", "DejaVu Sans"), base)
        mono = pick(("Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Noto Sans Mono", "Ubuntu Mono",
                     "Liberation Mono", "Menlo"), "TkFixedFont")
        self._semi_is_bold = semi == base   # sin variante seminegrita: se usa la negrita de la fuente
        self.icon_family = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in fams), None)

        def pt(size: int) -> int:
            return max(7, round(size * zoom))

        def strong(size: int) -> tuple:
            return (semi, pt(size), "bold") if self._semi_is_bold else (semi, pt(size))

        self.base = (base, pt(10))
        self.small = (base, pt(9))
        self.bold = strong(10)
        self.h1 = strong(17)
        self.h2 = strong(12)
        self.big = strong(22)
        self.mono = (mono, pt(9))
        self.brand = strong(14)
        self.icon = (self.icon_family, pt(13)) if self.icon_family else (base, pt(12))

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
    style.map("TButton", background=[("pressed", "#e0eae3"), ("active", "#edf4ef"), ("disabled", "#f3f6f4")],
              foreground=[("disabled", "#a0a7b5")])
    for name, bg, dark in (("Accent", ACCENT, ACCENT_DARK), ("Danger", DANGER, DANGER_DARK),
                           ("Info", INFO, INFO_DARK)):
        style.configure(f"{name}.TButton", background=bg, foreground="#ffffff", bordercolor=bg,
                        lightcolor=bg, darkcolor=bg, font=fonts.bold)
        style.map(f"{name}.TButton",
                  background=[("disabled", "#c9ced8"), ("pressed", dark), ("active", dark)],
                  foreground=[("disabled", "#f4f5f7")],
                  bordercolor=[("active", dark)])

    style.configure("TEntry", fieldbackground="#ffffff", padding=int(5 * sf), bordercolor=BORDER,
                    lightcolor="#ffffff")
    style.map("TEntry", bordercolor=[("focus", AGUA)], lightcolor=[("focus", AGUA)])
    style.configure("TCombobox", fieldbackground="#ffffff", padding=int(4 * sf), arrowsize=int(12 * sf))

    rowh = int(26 * sf)
    style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground=TEXT,
                    rowheight=rowh, bordercolor=BORDER, borderwidth=1, font=fonts.base)
    style.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", background="#ffffff", foreground=MUTED, relief="flat",
                    font=fonts.small, padding=(int(6 * sf), int(5 * sf)), bordercolor=BORDER,
                    lightcolor="#ffffff", darkcolor=BORDER)
    style.map("Treeview.Heading", background=[("active", ACCENT_SOFT)])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", padding=(int(14 * sf), int(6 * sf)), background=BG,
                    foreground=MUTED, borderwidth=0, font=fonts.bold)
    style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", TEXT)],
              expand=[("selected", (0, 0, 0, 0))])

    style.configure("Horizontal.TProgressbar", troughcolor="#e1e9e3", background=ACCENT,
                    bordercolor="#e1e9e3", lightcolor=ACCENT, darkcolor=ACCENT,
                    thickness=int(6 * sf))
    style.configure("Vertical.TScrollbar", background="#e6eee8", troughcolor="#ffffff",
                    bordercolor="#ffffff", arrowcolor=MUTED, gripcount=0, arrowsize=int(12 * sf))
    style.configure("Horizontal.TScrollbar", background="#e6eee8", troughcolor="#ffffff",
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
    for level in (1, 2, 3):
        tree.tag_configure(f"lvl{level}", foreground=LEVEL_COLORS[level])
