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
from .widgets import ASSETS_DIR, Background, ZoomStepper, bind_wheel, make_icons

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

    def set_pad(self, pady: int) -> None:
        self.icon.pack_configure(pady=pady)

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

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._closing = False
        self._monitor: tuple | None = None   # (monitor, resolución, área útil, marco de la ventana)
        self._build_everything(first=True)
        self._bind_shortcuts()

        log_action("inicio", sys.executable, f"admin={self.is_admin}")
        self.show("summary")
        self.root.after(800, self._watch_window)

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
            self._place_initial()

        self.pages: dict = {}
        self._build_shell()
        self._build_pages()

    def rebuild(self) -> None:
        """Reconstruye la interfaz tras cambiar el idioma o el tamaño. Se pierde el análisis en curso."""
        keep = self.current
        self._stop_pages()
        self.current = None
        for child in list(self.root.winfo_children()):
            child.destroy()
        self._build_everything(first=False)
        self.show(keep or "summary")

    def _stop_pages(self) -> None:
        """Detiene lo que las páginas tengan en marcha y descarta sus resultados pendientes."""
        for page in list(self.pages.values()):
            try:
                page.shutdown()
            except Exception:  # noqa: BLE001 - una página rota no debe impedir cerrar o reconstruir
                pass
        self.bg.reset()

    def _pending(self) -> list[str]:
        """Operaciones que no conviene cortar (borrados, limpiezas...) ahora mismo en marcha."""
        return [text for text in (page.pending() for page in self.pages.values()) if text]

    def _can_rebuild(self) -> bool:
        busy = self._pending()
        if busy:
            self.root.bell()
            self.set_status(i18n.t("app.busy_wait", what=", ".join(busy)))
        return not busy

    # ------------------------------------------------------- ventana y pantalla
    def _apply_minsize(self, area: tuple[int, int, int, int]) -> None:
        """Tamaño mínimo de la ventana, sin pasarse nunca del sitio que hay en pantalla."""
        self.root.minsize(max(320, min(760, area[2] - area[0] - 32)), max(240, min(520, area[3] - area[1] - 64)))

    def _place_initial(self) -> None:
        """Tamaño y posición iniciales, proporcionales a la pantalla en la que se abre."""
        self.root.update_idletasks()
        _name, _full, area = winframe.monitor_info(self.root)
        aw, ah = area[2] - area[0], area[3] - area[1]
        w, h = min(int(1280 * self.sf), int(aw * 0.92)), min(int(800 * self.sf), int(ah * 0.88))
        self.root.geometry(f"{w}x{h}+{area[0] + (aw - w) // 2}+{area[1] + max(0, (ah - h) // 3)}")
        self._apply_minsize(area)

    def _watch_window(self) -> None:
        """Vigila la ventana dos veces por segundo (ver _check_window)."""
        try:
            self._check_window()
        except tk.TclError:
            return   # la ventana ya no existe
        self.root.after(500, self._watch_window)

    def _check_window(self) -> None:
        """Si cambia la resolución de la pantalla, la ventana se recoloca ocupando la misma
        proporción y el mismo sitio relativo. Si se arrastra hasta dejarla fuera de la
        pantalla, vuelve a un lugar donde se puede agarrar."""
        root = self.root
        if root.state() != "normal":
            self._monitor = None   # maximizada o minimizada: de eso se ocupa Windows
            return
        if winframe.mouse_button_down():
            return                 # a mitad de un arrastre no se toca nada
        name, full, area = winframe.monitor_info(root)
        (x, y, w, h), border, caption = winframe.outer_rect(root)
        # Windows deja un borde invisible a los lados y abajo: puede sobresalir sin verse.
        room = (area[0] - border, area[1], area[2] + border, area[3] + border)
        prev = self._monitor
        if prev is not None and prev[0] == name and prev[1] != full:
            self._apply_minsize(area)
            min_w, min_h = root.minsize()
            x, y, w, h = winframe.rescale_rect(*prev[3], prev[2], room,
                                               (min_w + 2 * border, min_h + caption + border))
            winframe.set_outer_rect(root, x, y, w, h, border, caption)
            log_action("resolucion", f"{full[2] - full[0]}x{full[3] - full[1]}", f"{w}x{h}+{x}+{y}")
        else:
            if w > room[2] - room[0] or h > room[3] - room[1]:
                x, y, w, h = winframe.fit_rect(x, y, w, h, room)
                winframe.set_outer_rect(root, x, y, w, h, border, caption)
            dpi = theme.scale_factor(root)
            nx, ny = winframe.keep_reachable(x, y, w, h, room, grab=int(260 * dpi), title=int(110 * dpi))
            if (nx, ny) != (x, y):
                x, y = nx, ny
                root.geometry(f"+{x}+{y}")
        self._monitor = (name, full, room, (x, y, w, h))

    def _bind_shortcuts(self) -> None:
        """Ctrl + / Ctrl − / Ctrl 0 cambian el tamaño aunque la barra lateral no quepa entera."""
        def key(seqs: tuple[str, ...], fn) -> None:
            def handler(_e):
                fn()
                return "break"
            for seq in seqs:
                self.root.bind(seq, handler)

        key(("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"),
            lambda: self._set_zoom(self.zoom + config.SCALE_STEP))
        key(("<Control-minus>", "<Control-KP_Subtract>"), lambda: self._set_zoom(self.zoom - config.SCALE_STEP))
        key(("<Control-Key-0>", "<Control-KP_0>"), lambda: self._set_zoom(1.0))
        key(("<Control-q>", "<Control-Q>"), self.close)

    # ------------------------------------------------------------------ marco
    def _build_shell(self) -> None:
        sf = self.sf
        self.sidebar = tk.Frame(self.root, bg=theme.SIDEBAR_BG, width=int(232 * sf))
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = self._brand = tk.Frame(self.sidebar, bg=theme.SIDEBAR_BG)
        brand.pack(fill="x", pady=(int(18 * sf), int(18 * sf)), padx=int(16 * sf))
        tk.Label(brand, image=self.icons["app"], bg=theme.SIDEBAR_BG).pack(side="left")
        txt = tk.Frame(brand, bg=theme.SIDEBAR_BG)
        txt.pack(side="left", padx=int(10 * sf))
        tk.Label(txt, text="Super Limpio", font=self.fonts.brand, fg="#ffffff",
                 bg=theme.SIDEBAR_BG).pack(anchor="w")
        tk.Label(txt, text=i18n.t("app.brand_sub", v=__version__), font=self.fonts.small,
                 fg=theme.SIDEBAR_MUTED, bg=theme.SIDEBAR_BG).pack(anchor="w")

        # El pie (idioma, tamaño) se coloca antes que la navegación: si la ventana es baja,
        # lo que se recorta es la lista de secciones y no el control con el que arreglarlo.
        bottom = self._bottom = tk.Frame(self.sidebar, bg=theme.SIDEBAR_BG)
        bottom.pack(side="bottom", fill="x", padx=int(16 * sf), pady=int(16 * sf))
        self._build_settings(bottom)

        # La lista de secciones va en un lienzo desplazable: si no cabe a lo alto se compacta
        # y, si ni así, se recorre con la rueda o con la flecha que aparece debajo.
        self.nav_more = tk.Label(self.sidebar, text="▾", font=self.fonts.base, bg=theme.SIDEBAR_BG,
                                 fg=theme.SIDEBAR_MUTED, cursor="hand2")
        self.nav_more.bind("<Button-1>", lambda e: self._nav_page())
        self.nav_canvas = tk.Canvas(self.sidebar, bg=theme.SIDEBAR_BG, highlightthickness=0, height=1)
        self.nav_canvas.pack(fill="both", expand=True)
        self.nav_frame = tk.Frame(self.nav_canvas, bg=theme.SIDEBAR_BG)
        win = self.nav_canvas.create_window((0, 0), window=self.nav_frame, anchor="nw")
        self.nav_frame.bind("<Configure>",
                            lambda e: self.nav_canvas.configure(scrollregion=(0, 0, e.width, e.height)))
        self.nav_canvas.bind("<Configure>", lambda e: self.nav_canvas.itemconfigure(win, width=e.width))
        self.nav_canvas.configure(yscrollcommand=self._nav_scrolled)
        bind_wheel(self.nav_canvas)
        self.nav: dict[str, NavItem] = {}
        self._nav_pad = int(9 * sf)
        self.sidebar.bind("<Configure>", self._fit_nav)

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
        ZoomStepper(parent, self.fonts, sf, self.zoom, config.MIN_SCALE, config.MAX_SCALE,
                    on_step=lambda d: self._set_zoom(self.zoom + d * config.SCALE_STEP),
                    on_reset=lambda: self._set_zoom(1.0), on_hover=self._zoom_hint).pack(fill="x", pady=(3, 0))

    def _zoom_hint(self, inside: bool) -> None:
        """Al pasar por el control de tamaño, la barra de estado recuerda los atajos."""
        if inside:
            self._status_before = self.status_var.get()
            self.set_status(i18n.t("app.ui_size_hint"))
        elif self.status_var.get() == i18n.t("app.ui_size_hint"):
            self.set_status(getattr(self, "_status_before", i18n.t("common.ready")))

    def _on_language(self, _e=None) -> None:
        name = self.lang_var.get()
        if not self._can_rebuild():
            self.lang_var.set(dict(i18n.available())[i18n.current()])
            return
        for code, cname in i18n.available():
            if cname == name and code != i18n.current():
                config.set("language", code)
                i18n.set_language(code)
                log_action("idioma", code)
                self.rebuild()
                return

    def _set_zoom(self, value: float) -> None:
        new = config.clamp_scale(value)
        if abs(new - self.zoom) < 1e-6 or not self._can_rebuild():
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
        self.root.after_idle(self._fit_nav)

    def _fit_nav(self, _e=None) -> None:
        """Si las secciones no caben a lo alto (ventana baja o tamaño grande), se aprietan
        en vez de quedar tapadas: el espacio entre ellas se reparte según el sitio que hay."""
        items = list(self.nav.values())
        if not items or not self.sidebar.winfo_exists():
            return
        sf = self.sf
        free = (self.sidebar.winfo_height() - self._brand.winfo_reqheight() - int(36 * sf)
                - self._bottom.winfo_reqheight() - int(32 * sf))
        line = max(items[0].icon.winfo_reqheight(), items[0].label.winfo_reqheight())
        pad = int(max(3 * sf, min(9 * sf, (free / len(items) - line) / 2)))
        if pad != self._nav_pad:
            self._nav_pad = pad
            for item in items:
                item.set_pad(pad)
        overflow = len(items) * (line + 2 * pad) > free
        shown = self.nav_more.winfo_manager() == "pack"
        if overflow and not shown:
            self.nav_more.pack(side="bottom", fill="x", before=self.nav_canvas)
        elif not overflow and shown:
            self.nav_more.pack_forget()
            self.nav_canvas.yview_moveto(0)
        if overflow and self.current:
            self.root.after_idle(self._reveal_nav, self.current)

    def _nav_scrolled(self, first: str, last: str) -> None:
        """La flecha apunta hacia donde queda lista por ver."""
        self.nav_more.configure(text="▾" if float(last) < 0.999 else "▴")

    def _nav_page(self) -> None:
        if self.nav_canvas.yview()[1] < 0.999:
            self.nav_canvas.yview_scroll(1, "pages")
        else:
            self.nav_canvas.yview_moveto(0)

    def _reveal_nav(self, key: str) -> None:
        """Deja a la vista la sección activa cuando la lista está desplazada."""
        item = self.nav.get(key)
        if item is None or not item.winfo_exists():
            return
        total, view = self.nav_frame.winfo_height(), self.nav_canvas.winfo_height()
        if total <= view or total <= 1:
            return
        top, bottom = item.winfo_y(), item.winfo_y() + item.winfo_height()
        first = self.nav_canvas.canvasy(0)
        if top < first:
            self.nav_canvas.yview_moveto(top / total)
        elif bottom > first + view:
            self.nav_canvas.yview_moveto((bottom - view) / total)

    def page(self, key: str):
        page = self.pages.get(key)
        if page is None:
            page = self.pages[key] = self._page_classes[key](self.content, self)
        return page

    # -------------------------------------------------------------- navegación
    def show(self, key: str) -> None:
        if self.current == key:
            return
        page = self.page(key)   # si la página fallara al construirse, se sigue en la actual
        if self.current:
            self.pages[self.current].on_hide()
            self.pages[self.current].pack_forget()
            self.nav[self.current].set_active(False)
        self.current = key
        self.h_title.configure(text=page.title)
        self.h_sub.configure(text=page.subtitle)
        page.pack(fill="both", expand=True)
        self.nav[key].set_active(True)
        self._reveal_nav(key)
        page.on_show()

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def relaunch_admin(self) -> None:
        script = os.path.abspath(sys.argv[0])
        ok = dialogs.confirm(
            self.root, i18n.t("app.relaunch.title"), i18n.t("app.relaunch.body"),
            details='"{}" {}'.format(*winapi.admin_command(script)).strip(), risk=Risk.ALTO,
            ok_text=i18n.t("app.relaunch.ok"))
        if not ok or not self._confirm_exit():   # esta ventana se va a cerrar: mismas preguntas que al salir
            return
        done, msg = winapi.relaunch_as_admin(script)
        log_action("reiniciar_admin", script, msg, ok=done)
        if done:
            self.root.after(300, self._shutdown)
        else:
            dialogs.error(self.root, i18n.t("app.relaunch.failed"), msg)

    # -------------------------------------------------------------------- salir
    def request_close(self, parent: tk.Misc | None = None) -> None:
        """El usuario ha pedido finalizar el proceso de la propia aplicación: en vez de
        matarlo se ofrece el cierre ordenado, que es seguro."""
        if dialogs.confirm(parent or self.root, i18n.t("app.exit.self_title"), i18n.t("app.exit.self_body"),
                           risk=Risk.BAJO, ok_text=i18n.t("app.exit.self_ok")):
            self.close()

    def close(self) -> None:
        """Cierre ordenado: avisa si hay algo a medias, ofrece deshacer el Modo eficiente,
        detiene los análisis en curso y solo entonces destruye la ventana."""
        if self._closing or not self._confirm_exit():
            return
        self._shutdown()

    def _confirm_exit(self) -> bool:
        from tkinter import messagebox
        busy = self._pending()
        if busy and not messagebox.askyesno(
                i18n.t("app.exit.busy_title"), i18n.t("app.exit.busy_body", what="\n".join(f"• {b}" for b in busy)),
                icon="warning", default="no", parent=self.root):
            return False
        session = optimizer.SESSION
        session.prune()
        if session.active:
            answer = messagebox.askyesnocancel(
                i18n.t("opt.exit.title"),
                i18n.t("opt.exit.body", n=len(session.throttled) + len(session.boosted)), parent=self.root)
            if answer is None:
                return False
            if answer:
                optimizer.restore()
            else:
                log_action("modo_eficiente_salir_sin_restaurar", "",
                           str(len(session.throttled) + len(session.boosted)))
        return True

    def _shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._stop_pages()
        log_action("cierre", sys.executable, "ordenado")
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run() -> None:
    App().run()
