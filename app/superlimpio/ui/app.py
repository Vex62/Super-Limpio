"""Ventana principal: barra lateral de navegación + páginas."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk

from .. import APP_NAME, __version__, config, i18n, optimizer, winapi
from ..safety import Risk, log_action
from ..util import IS_WINDOWS
from . import dialogs, theme, winframe
from .widgets import ASSETS_DIR, Background, make_icons

# (clave de navegación, clase de vista, clave i18n de la etiqueta)
_PAGES_SPEC = [
    ("summary", "SummaryView", "nav.summary"),
    ("disk", "DiskView", "nav.disk"),
    ("programs", "ProgramsView", "nav.programs"),
    ("memory", "MemoryView", "nav.memory"),
    ("optimizer", "OptimizerView", "nav.optimizer"),
    ("startup", "StartupView", "nav.startup"),
    ("cleaner", "CleanerView", "nav.cleaner"),
    ("devdeps", "DevDepsView", "nav.devdeps"),
    ("tools", "ToolsView", "nav.tools"),
    ("log", "LogView", "nav.log"),
]


class NavItem(tk.Frame):
    def __init__(self, master, app: "App", key: str, glyph: str, text: str):
        super().__init__(master, bg=theme.SIDEBAR_BG, cursor="hand2")
        self.app, self.key = app, key
        self.active = False
        sf = app.sf
        self.marker = tk.Frame(self, bg=theme.SIDEBAR_BG, width=int(4 * sf))
        self.marker.pack(side="left", fill="y")
        self.icon = tk.Label(self, text=glyph, font=app.fonts.icon, bg=theme.SIDEBAR_BG,
                             fg=theme.SIDEBAR_FG, width=2)
        self.icon.pack(side="left", padx=(int(14 * sf), int(8 * sf)), pady=int(9 * sf))
        self.label = tk.Label(self, text=text, font=app.fonts.base, bg=theme.SIDEBAR_BG,
                              fg=theme.SIDEBAR_FG, anchor="w")
        self.label.pack(side="left", fill="x", expand=True)
        for w in (self, self.icon, self.label, self.marker):
            w.bind("<Button-1>", lambda e: app.show(key))
            w.bind("<Enter>", lambda e: self._hover(True))
            w.bind("<Leave>", lambda e: self._hover(False))

    def _paint(self, bg: str, fg: str, marker: str) -> None:
        for w in (self, self.icon, self.label):
            w.configure(bg=bg)
        self.icon.configure(fg=fg)
        self.label.configure(fg=fg)
        self.marker.configure(bg=marker)

    def _hover(self, inside: bool) -> None:
        if self.active:
            return
        self._paint(theme.SIDEBAR_HOVER if inside else theme.SIDEBAR_BG, theme.SIDEBAR_FG, theme.SIDEBAR_BG)

    def set_active(self, on: bool) -> None:
        self.active = on
        if on:
            self._paint(theme.SIDEBAR_ACTIVE, theme.SIDEBAR_FG_ACTIVE, theme.HIGHLIGHT)
        else:
            self._paint(theme.SIDEBAR_BG, theme.SIDEBAR_FG, theme.SIDEBAR_BG)


class App:
    def __init__(self) -> None:
        self.root = tk.Tk(className="SuperLimpio")
        self.root._superlimpio_app = self  # para que los diálogos encuentren fuentes/escala
        self.is_admin = winapi.is_admin()
        self.bg = Background(self.root)
        self.current: str | None = None

        try:  # mismo icono que SuperLimpio.exe, en la barra de título y en la de tareas
            self.root.iconbitmap(default=os.path.join(ASSETS_DIR, "superlimpio.ico"))
        except tk.TclError:
            pass

        self.root.minsize(int(760), int(520))
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._build_everything(first=True)

        log_action("inicio", sys.executable, f"admin={self.is_admin}")
        self.show("summary")

    # ------------------------------------------------------------ construcción
    def _build_everything(self, first: bool = False) -> None:
        """Crea (o recrea) fuentes, estilo, iconos y toda la interfaz con el zoom e idioma actuales."""
        self.zoom = config.get_scale()
        self.sf = theme.scale_factor(self.root) * self.zoom
        self.fonts = theme.Fonts(self.root, self.zoom)
        self.style = theme.apply_style(self.root, self.fonts, self.sf)
        self.icons = make_icons(self.root, self.sf)

        # El nombre y la versión ya salen en la barra lateral: el título se deja limpio.
        self.root.title(APP_NAME)
        try:
            self.root.iconphoto(True, self.icons["app"])
        except tk.TclError:
            pass
        # Barra de título y borde con los colores de la marca (Windows 11).
        winframe.apply(self.root, caption=theme.SIDEBAR_BG, text=theme.BLANCO, border=theme.ACCENT)

        if first:
            w, h = int(1280 * self.sf), int(800 * self.sf)
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            w, h = min(w, sw - 40), min(h, sh - 80)
            self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 3)}")

        self.pages: dict = {}
        self._build_shell()
        self._build_pages()

    def rebuild(self) -> None:
        """Reconstruye la interfaz tras cambiar el idioma o el tamaño. Se pierde el análisis en curso."""
        keep = self.current
        self.current = None
        for child in list(self.root.winfo_children()):
            child.destroy()
        self._build_everything(first=False)
        self.show(keep or "summary")

    # ------------------------------------------------------------------ marco
    def _build_shell(self) -> None:
        sf = self.sf
        self.sidebar = tk.Frame(self.root, bg=theme.SIDEBAR_BG, width=int(232 * sf))
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=theme.SIDEBAR_BG)
        brand.pack(fill="x", pady=(int(18 * sf), int(18 * sf)), padx=int(16 * sf))
        tk.Label(brand, image=self.icons["app"], bg=theme.SIDEBAR_BG).pack(side="left")
        txt = tk.Frame(brand, bg=theme.SIDEBAR_BG)
        txt.pack(side="left", padx=int(10 * sf))
        tk.Label(txt, text="Super Limpio", font=self.fonts.brand, fg="#ffffff",
                 bg=theme.SIDEBAR_BG).pack(anchor="w")
        tk.Label(txt, text=i18n.t("app.brand_sub", v=__version__), font=self.fonts.small,
                 fg=theme.SIDEBAR_MUTED, bg=theme.SIDEBAR_BG).pack(anchor="w")

        self.nav_frame = tk.Frame(self.sidebar, bg=theme.SIDEBAR_BG)
        self.nav_frame.pack(fill="x")

        bottom = tk.Frame(self.sidebar, bg=theme.SIDEBAR_BG)
        bottom.pack(side="bottom", fill="x", padx=int(16 * sf), pady=int(16 * sf))
        self._build_settings(bottom)

        color = theme.WARN if self.is_admin else theme.HIGHLIGHT
        state = i18n.t("app.role.admin") if self.is_admin else i18n.t("app.role.user")
        tk.Label(bottom, text=f"{self.fonts.glyph('shield')}  {state}", font=self.fonts.small,
                 fg=color, bg=theme.SIDEBAR_BG, anchor="w").pack(fill="x", pady=(int(10 * sf), 0))
        if not self.is_admin and IS_WINDOWS:
            lnk = tk.Label(bottom, text=i18n.t("app.relaunch_admin_link"), font=self.fonts.small,
                           fg=theme.AGUA, bg=theme.SIDEBAR_BG, cursor="hand2", anchor="w")
            lnk.pack(fill="x", pady=(4, 0))
            lnk.bind("<Button-1>", lambda e: self.relaunch_admin())

        self.main = ttk.Frame(self.root, style="TFrame")
        self.main.pack(side="left", fill="both", expand=True)

        header = ttk.Frame(self.main)
        header.pack(fill="x", padx=int(26 * sf), pady=(int(20 * sf), int(12 * sf)))
        self.h_title = ttk.Label(header, text="", style="H1.TLabel")
        self.h_title.pack(anchor="w")
        self.h_sub = ttk.Label(header, text="", style="Muted.TLabel")
        self.h_sub.pack(anchor="w")

        status = tk.Frame(self.main, bg="#e6eee8", height=int(26 * sf))
        status.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value=i18n.t("common.ready"))
        tk.Label(status, textvariable=self.status_var, bg="#e6eee8", fg=theme.MUTED,
                 font=self.fonts.small, anchor="w").pack(side="left", padx=int(12 * sf), pady=int(3 * sf))
        tk.Label(status, text=i18n.t("app.status_hint"),
                 bg="#e6eee8", fg=theme.MUTED, font=self.fonts.small).pack(side="right", padx=int(12 * sf))

        self.content = ttk.Frame(self.main)
        self.content.pack(fill="both", expand=True, padx=int(26 * sf), pady=(0, int(8 * sf)))

    def _build_settings(self, parent: tk.Frame) -> None:
        """Selector de idioma y control de tamaño de la interfaz (barra lateral, abajo)."""
        sf = self.sf
        # Idioma
        tk.Label(parent, text=i18n.t("app.language"), font=self.fonts.small, fg=theme.SIDEBAR_MUTED,
                 bg=theme.SIDEBAR_BG, anchor="w").pack(fill="x")
        names = [name for _code, name in i18n.available()]
        codes = [code for code, _name in i18n.available()]
        self._lang_codes = codes
        self.lang_var = tk.StringVar(value=dict(i18n.available())[i18n.current()])
        cb = ttk.Combobox(parent, values=names, textvariable=self.lang_var, state="readonly", width=14)
        cb.pack(fill="x", pady=(2, int(8 * sf)))
        cb.bind("<<ComboboxSelected>>", self._on_language)

        # Tamaño de la interfaz (zoom)
        tk.Label(parent, text=i18n.t("app.ui_size"), font=self.fonts.small, fg=theme.SIDEBAR_MUTED,
                 bg=theme.SIDEBAR_BG, anchor="w").pack(fill="x")
        row = tk.Frame(parent, bg=theme.SIDEBAR_BG)
        row.pack(fill="x", pady=(2, 0))
        ttk.Button(row, text="−", width=3,
                   command=lambda: self._change_zoom(-config.SCALE_STEP)).pack(side="left")
        self.zoom_lbl = tk.Label(row, text=f"{round(self.zoom * 100)} %", font=self.fonts.small,
                                 fg=theme.SIDEBAR_FG, bg=theme.SIDEBAR_BG, width=6)
        self.zoom_lbl.pack(side="left", padx=4)
        ttk.Button(row, text="+", width=3,
                   command=lambda: self._change_zoom(config.SCALE_STEP)).pack(side="left")

    def _on_language(self, _e=None) -> None:
        name = self.lang_var.get()
        for code, cname in i18n.available():
            if cname == name and code != i18n.current():
                config.set("language", code)
                i18n.set_language(code)
                log_action("idioma", code)
                self.rebuild()
                return

    def _change_zoom(self, delta: float) -> None:
        new = config.clamp_scale(self.zoom + delta)
        if abs(new - self.zoom) < 1e-6:
            return
        config.set_scale(new)
        log_action("tamano_ui", f"{new:.2f}")
        self.rebuild()

    def _build_pages(self) -> None:
        from .views.cleaner_view import CleanerView
        from .views.devdeps_view import DevDepsView
        from .views.disk_view import DiskView
        from .views.log_view import LogView
        from .views.memory_view import MemoryView
        from .views.optimizer_view import OptimizerView
        from .views.programs_view import ProgramsView
        from .views.startup_view import StartupView
        from .views.summary_view import SummaryView
        from .views.tools_view import ToolsView

        classes = {
            "SummaryView": SummaryView, "DiskView": DiskView, "ProgramsView": ProgramsView,
            "MemoryView": MemoryView, "OptimizerView": OptimizerView, "StartupView": StartupView,
            "CleanerView": CleanerView,
            "DevDepsView": DevDepsView, "ToolsView": ToolsView, "LogView": LogView,
        }
        # Cada página se construye la primera vez que se visita: la ventana abre antes.
        self._page_classes = {key: classes[cls] for key, cls, _k in _PAGES_SPEC}
        self.nav = {}
        for key, cls, label_key in _PAGES_SPEC:
            item = NavItem(self.nav_frame, self, key, self.fonts.glyph(classes[cls].icon), i18n.t(label_key))
            item.pack(fill="x")
            self.nav[key] = item

    def page(self, key: str):
        page = self.pages.get(key)
        if page is None:
            page = self.pages[key] = self._page_classes[key](self.content, self)
        return page

    # -------------------------------------------------------------- navegación
    def show(self, key: str) -> None:
        if self.current == key:
            return
        if self.current:
            self.pages[self.current].on_hide()
            self.pages[self.current].pack_forget()
            self.nav[self.current].set_active(False)
        self.current = key
        page = self.page(key)
        self.h_title.configure(text=page.title)
        self.h_sub.configure(text=page.subtitle)
        page.pack(fill="both", expand=True)
        self.nav[key].set_active(True)
        page.on_show()

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def relaunch_admin(self) -> None:
        script = os.path.abspath(sys.argv[0])
        ok = dialogs.confirm(
            self.root, i18n.t("app.relaunch.title"), i18n.t("app.relaunch.body"),
            details='"{}" {}'.format(*winapi.admin_command(script)).strip(), risk=Risk.ALTO,
            ok_text=i18n.t("app.relaunch.ok"))
        if not ok:
            return
        done, msg = winapi.relaunch_as_admin(script)
        log_action("reiniciar_admin", script, msg, ok=done)
        if done:
            self.root.after(300, self.root.destroy)
        else:
            dialogs.error(self.root, i18n.t("app.relaunch.failed"), msg)

    def close(self) -> None:
        """Al cerrar con el Modo eficiente activo se pregunta si deshacerlo antes de salir."""
        session = optimizer.SESSION
        session.prune()
        if session.active:
            from tkinter import messagebox
            answer = messagebox.askyesnocancel(
                i18n.t("opt.exit.title"),
                i18n.t("opt.exit.body", n=len(session.throttled) + len(session.boosted)), parent=self.root)
            if answer is None:
                return
            if answer:
                optimizer.restore()
            else:
                log_action("modo_eficiente_salir_sin_restaurar", "",
                           str(len(session.throttled) + len(session.boosted)))
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run() -> None:
    App().run()
