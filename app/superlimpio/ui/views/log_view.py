from __future__ import annotations

from tkinter import ttk
from typing import Any

from ... import i18n, plat
from ... import safety
from ...safety import read_log
from ..widgets import ScrollTree, SortableTable
from .base import View


class LogView(View):
    icon = "log"
    view_key = "log"

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, app)
        self.title = i18n.t("log.title")
        self.subtitle = i18n.t("log.subtitle")
        bar = self.toolbar()
        ttk.Button(bar, text=i18n.t("common.refresh"), command=self.load).pack(side="left")
        ttk.Button(bar, text=i18n.t("log.open_folder"), command=self._open).pack(side="left", padx=self.px(6))
        cols = [("fecha", i18n.t("log.col.date"), 150, "w"), ("accion", i18n.t("log.col.action"), 150, "w"),
                ("ok", i18n.t("log.col.ok"), 50, "center"), ("objetivo", i18n.t("log.col.target"), 420, "w"),
                ("resultado", i18n.t("log.col.result"), 340, "w")]
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
        if safety.log_failures:   # disco lleno o carpeta sin permiso: que no pase inadvertido
            self.status(i18n.t("log.write_failed", n=safety.log_failures, path=str(safety.LOG_DIR)))

    def _open(self) -> None:
        try:
            safety.LOG_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.status(f"{i18n.t('common.error')}: {exc.strerror or exc}")
            return
        plat.open_in_explorer(str(safety.LOG_DIR))
