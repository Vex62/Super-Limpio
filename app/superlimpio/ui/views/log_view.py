from __future__ import annotations

from tkinter import ttk

from ... import winapi
from ...safety import read_log
from ...util import LOG_DIR
from ..widgets import ScrollTree, SortableTable
from .base import View


class LogView(View):
    title = "Registro de acciones"
    subtitle = "Todo lo que Super Limpio ha hecho en este equipo (se guarda en la carpeta logs, junto a la app)."
    icon = "log"

    def __init__(self, master, app):
        super().__init__(master, app)
        bar = self.toolbar()
        ttk.Button(bar, text="Actualizar", command=self.load).pack(side="left")
        ttk.Button(bar, text="Abrir carpeta de registros", command=self._open).pack(side="left", padx=self.px(6))
        cols = [("fecha", "Fecha", 150, "w"), ("accion", "Acción", 150, "w"), ("ok", "OK", 50, "center"),
                ("objetivo", "Objetivo", 420, "w"), ("resultado", "Resultado", 340, "w")]
        box = ScrollTree(self, cols, sf=self.sf)
        box.pack(fill="both", expand=True)
        self.table = SortableTable(
            box.tree,
            render=lambda r: (r.get("fecha", "").replace("T", " "), r.get("accion", ""),
                              "✔" if r.get("ok") else "✖", r.get("objetivo", ""), r.get("resultado", "")),
            sort_keys={"fecha": lambda r: r.get("fecha", ""), "accion": lambda r: r.get("accion", "")},
            default_sort="fecha", tag_fn=lambda r: () if r.get("ok") else ("warn",))

    def on_show(self) -> None:
        super().on_show()
        self.load()

    def load(self) -> None:
        self.table.set_rows(read_log(1000))

    def _open(self) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        winapi.open_in_explorer(str(LOG_DIR))
