from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, TYPE_CHECKING

from ... import config
from .. import theme

if TYPE_CHECKING:  # pragma: no cover
    from ..app import App


class View(ttk.Frame):
    title = ""
    subtitle = ""
    icon = "home"
    view_key = ""

    def __init__(self, master: Any, app: App) -> None:
        super().__init__(master, style="TFrame")
        self.app = app
        self.sf = app.sf
        self.fonts = app.fonts
        self._shown_once = False
        self._dead = False               # la vista ya no existe en pantalla
        self._heir: View | None = None   # la vista que la sustituyó al reconstruir la interfaz

    # Se llama cada vez que se muestra la vista
    def on_show(self) -> None:
        if not self._shown_once:
            self._shown_once = True
            self.first_show()

    def first_show(self) -> None:
        pass

    def on_hide(self) -> None:
        pass

    def pending(self) -> str:
        """Texto de la operación que no conviene cortar (un borrado, una limpieza...) si hay
        una en marcha; cadena vacía si la vista se puede cerrar o reconstruir sin más."""
        return ""

    def shutdown(self) -> None:
        """La vista se va a destruir (cierre, cambio de idioma o de tamaño): se cancelan los
        análisis en segundo plano para que no sigan trabajando para nadie."""
        self.retire()
        for name in ("cancel_ev", "_an_stop", "_del_cancel"):
            ev = getattr(self, name, None)
            if ev is not None:
                ev.set()

    def retire(self) -> None:
        """La vista deja de existir en pantalla, pero no se cancela lo que tenga en marcha."""
        self.on_hide()
        self._dead = True

    # Al cambiar el tamaño de la interfaz todo se vuelve a construir, pero un análisis en
    # marcha (o ya terminado) no se pierde: la vista vieja entrega su estado a la nueva.
    def handoff(self) -> dict[str, Any] | None:
        """Lo que la vista quiere conservar al reconstruirse; None si no hay nada que guardar."""
        return None

    def adopt(self, state: dict[str, Any]) -> None:
        """Recibe lo que entregó la vista a la que sustituye (ver handoff)."""

    def succeed(self, old: View, state: dict[str, Any]) -> None:
        """Esta vista ocupa el sitio de old: recibe su estado y, desde ahora, lo que sus
        tareas en segundo plano vayan enviando."""
        self.adopt(state)
        old._heir = self

    def heir(self) -> View | None:
        """La vista que hoy ocupa el sitio de esta, o None si ya no hay ninguna."""
        view = self
        while view._heir is not None:
            view = view._heir
        return None if view._dead else view

    def send(self, name: str, *args: Any) -> None:
        """Llama al método name de la vista que hoy ocupa el sitio de esta (hilo de la interfaz)."""
        view = self.heir()
        if view is not None:
            getattr(view, name)(*args)

    def later(self, name: str, *args: Any) -> None:
        """Como send, pero desde un hilo de trabajo: la llamada se entrega en el de la interfaz."""
        self.app.bg.call_in_ui(self.send, name, *args)

    def work(self, fn: Any, done: str, failed: str, *extra: Any) -> None:
        """Lanza fn en segundo plano. El resultado (o el error) llega al método done (o
        failed), seguido de extra, de la vista que entonces ocupe el sitio de esta."""
        self.app.bg.run(fn, on_done=lambda result: self.send(done, result, *extra),
                        on_error=lambda exc: self.send(failed, exc, *extra), survive=True)

    # Utilidades
    def px(self, n: int | float) -> int:
        return int(n * self.sf)

    def toolbar(self, parent: Any = None) -> ttk.Frame:
        bar = ttk.Frame(parent or self)
        bar.pack(fill="x", pady=(0, self.px(10)))
        return bar

    def status(self, text: str) -> None:
        self.app.set_status(text)

    def note(self, parent: Any, text: str) -> tk.Label:
        lbl = tk.Label(parent, text=text, bg=theme.BG, fg=theme.MUTED, font=self.fonts.small,
                       anchor="w", justify="left", wraplength=self.px(900))
        # El texto se ajusta al ancho real: en ventanas estrechas no se corta por la derecha.
        lbl.bind("<Configure>", lambda e: lbl.configure(wraplength=max(self.px(200), e.width - 4)))
        return lbl

    def persist_sash(self, pw: ttk.PanedWindow, name: str, default_px: int) -> None:
        """Recuerda y restaura la posición de un divisor arrastrable de esta vista."""
        key = self.view_key or type(self).__name__

        def restore() -> None:
            try:
                pw.sashpos(0, int(config.get_sash(key, name, self.px(default_px))))
            except tk.TclError:
                pass

        def save(_e: Any = None) -> None:
            try:
                config.set_sash(key, name, pw.sashpos(0))
            except tk.TclError:
                pass

        pw.after(80, restore)
        pw.bind("<ButtonRelease-1>", save, add="+")
