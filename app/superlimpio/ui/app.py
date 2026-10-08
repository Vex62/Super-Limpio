"""Ventana principal: barra lateral de navegación + páginas."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk

from .. import APP_NAME, __version__, winapi
from ..safety import Risk, log_action
from ..util import IS_WINDOWS
from . import dialogs, theme
from .widgets import Background, make_icons


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
        self.sf = theme.scale_factor(self.root)
        self.fonts = theme.Fonts(self.root)
        self.style = theme.apply_style(self.root, self.fonts, self.sf)
        self.icons = make_icons(self.root, self.sf)
        self.bg = Background(self.root)
        self.is_admin = winapi.is_admin()

        self.root.title(f"{APP_NAME} {__version__}" + ("  —  Administrador" if self.is_admin else ""))
        self.root.iconphoto(True, self.icons["app"])
        if not os.path.basename(sys.executable).lower().startswith("python"):
            try:  # abierta con SuperLimpio.exe: la ventana usa su mismo icono
                self.root.iconbitmap(default=sys.executable)
            except tk.TclError:
                pass
        w, h = int(1280 * self.sf), int(800 * self.sf)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h = min(w, sw - 40), min(h, sh - 80)
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 3)}")
        self.root.minsize(int(980 * self.sf), int(620 * self.sf))

        self._build_shell()
        self._build_pages()
        log_action("inicio", sys.executable, f"admin={self.is_admin}")
        self.show("summary")

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
        tk.Label(txt, text=f"v{__version__} · local y sin red", font=self.fonts.small, fg=theme.SIDEBAR_MUTED,
                 bg=theme.SIDEBAR_BG).pack(anchor="w")

        self.nav_frame = tk.Frame(self.sidebar, bg=theme.SIDEBAR_BG)
        self.nav_frame.pack(fill="x")

        bottom = tk.Frame(self.sidebar, bg=theme.SIDEBAR_BG)
        bottom.pack(side="bottom", fill="x", padx=int(16 * sf), pady=int(16 * sf))
        color = theme.WARN if self.is_admin else theme.HIGHLIGHT
        state = "Administrador" if self.is_admin else "Usuario estándar"
        tk.Label(bottom, text=f"{self.fonts.glyph('shield')}  {state}", font=self.fonts.small,
                 fg=color, bg=theme.SIDEBAR_BG, anchor="w").pack(fill="x")
        if not self.is_admin and IS_WINDOWS:
            lnk = tk.Label(bottom, text="Reiniciar como administrador…", font=self.fonts.small,
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
        self.status_var = tk.StringVar(value="Listo")
        tk.Label(status, textvariable=self.status_var, bg="#e6eee8", fg=theme.MUTED,
                 font=self.fonts.small, anchor="w").pack(side="left", padx=int(12 * sf), pady=int(3 * sf))
        tk.Label(status, text="Todas las acciones piden confirmación · registro en logs\\acciones.log",
                 bg="#e6eee8", fg=theme.MUTED, font=self.fonts.small).pack(side="right", padx=int(12 * sf))

        self.content = ttk.Frame(self.main)
        self.content.pack(fill="both", expand=True, padx=int(26 * sf), pady=(0, int(8 * sf)))

    def _build_pages(self) -> None:
        from .views.cleaner_view import CleanerView
        from .views.devdeps_view import DevDepsView
        from .views.disk_view import DiskView
        from .views.log_view import LogView
        from .views.memory_view import MemoryView
        from .views.programs_view import ProgramsView
        from .views.startup_view import StartupView
        from .views.summary_view import SummaryView
        from .views.tools_view import ToolsView

        spec = [
            ("summary", SummaryView, "Resumen"),
            ("disk", DiskView, "Analizador de disco"),
            ("programs", ProgramsView, "Programas"),
            ("memory", MemoryView, "Memoria y procesos"),
            ("startup", StartupView, "Inicio de Windows"),
            ("cleaner", CleanerView, "Limpieza"),
            ("devdeps", DevDepsView, "Librerías de desarrollo"),
            ("tools", ToolsView, "Herramientas del sistema"),
            ("log", LogView, "Registro de acciones"),
        ]
        # Cada página se construye la primera vez que se visita: la ventana abre antes.
        self._page_classes = {key: cls for key, cls, _label in spec}
        self.pages = {}
        self.nav = {}
        for key, cls, label in spec:
            item = NavItem(self.nav_frame, self, key, self.fonts.glyph(cls.icon), label)
            item.pack(fill="x")
            self.nav[key] = item
        self.current: str | None = None

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
            self.root, "Reiniciar como administrador",
            "Se abrirá una nueva ventana de Super Limpio con permisos de administrador y esta se cerrará. "
            "Windows mostrará su aviso de Control de cuentas de usuario (UAC).\n\n"
            "Solo es necesario para limpiar carpetas del sistema, finalizar procesos de otros usuarios "
            "o ejecutar DISM/powercfg.",
            details='"{}" {}'.format(*winapi.admin_command(script)).strip(), risk=Risk.ALTO, ok_text="Reiniciar elevado")
        if not ok:
            return
        done, msg = winapi.relaunch_as_admin(script)
        log_action("reiniciar_admin", script, msg, ok=done)
        if done:
            self.root.after(300, self.root.destroy)
        else:
            dialogs.error(self.root, "No se pudo elevar", msg)

    def run(self) -> None:
        self.root.mainloop()


def run() -> None:
    App().run()
