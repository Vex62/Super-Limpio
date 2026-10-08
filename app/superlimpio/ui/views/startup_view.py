"""Programas que se inician con Windows (consumen memoria desde el arranque)."""

from __future__ import annotations

from tkinter import ttk

from ... import startup, winapi
from ...systools import TOOLS, run_tool
from .. import theme
from ..widgets import ScrollTree, SortableTable
from .base import View


class StartupView(View):
    title = "Inicio de Windows"
    subtitle = "Programas que arrancan solos y ocupan memoria desde que enciendes el equipo."
    icon = "startup"

    def __init__(self, master, app):
        super().__init__(master, app)
        bar = self.toolbar()
        ttk.Button(bar, text="Actualizar", command=self.load).pack(side="left")
        ttk.Button(bar, text="Abrir ubicación", command=self.open_location).pack(side="left", padx=self.px(6))
        ttk.Button(bar, text="Administrar en el Administrador de tareas", style="Accent.TButton",
                   command=lambda: run_tool(next(t for t in TOOLS if t.id == "taskmgr_startup"))) \
            .pack(side="right")

        cols = [("name", "Nombre", 230, "w"), ("state", "Estado", 95, "w"), ("location", "Origen", 170, "w"),
                ("command", "Comando", 520, "w")]
        box = ScrollTree(self, cols, sf=self.sf)
        box.pack(fill="both", expand=True)
        self.tree = box.tree
        self.tree.tag_configure("off", foreground=theme.MUTED)
        self.table = SortableTable(
            self.tree,
            render=lambda r: (r.name, _state(r), r.location,
                              r.command + ("" if r.exists or not r.exe else "   ⚠ el archivo no existe")),
            sort_keys={"name": lambda r: r.name.lower(), "state": lambda r: str(r.enabled),
                       "location": lambda r: r.location},
            default_sort="name", descending=False,
            tag_fn=lambda r: ("off",) if r.enabled is False else (("warn",) if r.exe and not r.exists else ()))
        self.note(self, "Por seguridad, Super Limpio solo muestra esta lista. Para desactivar un programa usa el "
                        "Administrador de tareas (pestaña Inicio): es la vía oficial de Windows y se puede revertir "
                        "en cualquier momento. Las entradas marcadas con ⚠ apuntan a programas ya borrados.") \
            .pack(fill="x", pady=(self.px(6), 0))

    def first_show(self) -> None:
        self.load()

    def load(self) -> None:
        self.app.bg.run(startup.list_startup, on_done=self._loaded)

    def _loaded(self, items) -> None:
        self.table.set_rows(items)
        on = sum(1 for i in items if i.enabled is not False)
        self.status(f"{len(items)} entradas de inicio · {on} activadas")

    def open_location(self) -> None:
        sel = self.table.selected()
        if sel and sel[0].exe:
            ok, msg = winapi.open_in_explorer(sel[0].exe)
            if not ok:
                self.status(msg)


def _state(r) -> str:
    if r.enabled is None:
        return "Una vez"
    return "Activado" if r.enabled else "Desactivado"

