"""Programas que se inician con Windows (consumen memoria desde el arranque)."""

from __future__ import annotations

from tkinter import ttk
from typing import Any

from ... import i18n, startup, plat
from .. import theme
from ..widgets import ScrollTree, SortableTable
from .base import View


class StartupView(View):
    icon = "startup"
    view_key = "startup"

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, app)
        self.title = i18n.t("startup.title")
        self.subtitle = i18n.t("startup.subtitle")
        bar = self.toolbar()
        ttk.Button(bar, text=i18n.t("common.refresh"), command=self.load).pack(side="left")
        ttk.Button(bar, text=i18n.t("common.open_location"), command=self.open_location).pack(
            side="left", padx=self.px(6))
        ttk.Button(bar, text=i18n.t("startup.manage"), style="Accent.TButton",
                   command=self.manage).pack(side="right")

        cols = [("name", i18n.t("startup.col.name"), 230, "w"), ("state", i18n.t("startup.col.state"), 95, "w"),
                ("location", i18n.t("startup.col.source"), 170, "w"),
                ("command", i18n.t("startup.col.command"), 520, "w")]
        box = ScrollTree(self, cols, sf=self.sf)
        box.pack(fill="both", expand=True)
        self.tree = box.tree
        self.tree.tag_configure("off", foreground=theme.MUTED)
        self.table = SortableTable(
            self.tree,
            render=lambda r: (r.name, _state(r), r.location,
                              r.command + ("" if r.exists or not r.exe else i18n.t("startup.missing_file"))),
            sort_keys={"name": lambda r: r.name.lower(), "state": lambda r: str(r.enabled),
                       "location": lambda r: r.location},
            default_sort="name", descending=False,
            tag_fn=lambda r: ("off",) if r.enabled is False else (("warn",) if r.exe and not r.exists else ()))
        self.note(self, i18n.t("startup.note")).pack(fill="x", pady=(self.px(6), 0))

    def first_show(self) -> None:
        self.load()

    def load(self) -> None:
        self.app.bg.run(startup.list_startup, on_done=self._loaded,
                        on_error=lambda e: self.status(f"{i18n.t('common.error')}: {e}"))

    def _loaded(self, items: Any) -> None:
        self.table.set_rows(items)
        on = sum(1 for i in items if i.enabled is not False)
        self.status(i18n.t("startup.status", n=len(items), on=on))

    def manage(self) -> None:
        ok, msg = startup.open_manager()
        if not ok:
            self.status(msg)

    def open_location(self) -> None:
        sel = self.table.selected()
        if sel and sel[0].exe:
            ok, msg = plat.open_in_explorer(sel[0].exe)
            if not ok:
                self.status(msg)


def _state(r: Any) -> str:
    if r.enabled is None:
        return i18n.t("startup.state.once")
    return i18n.t("startup.state.on") if r.enabled else i18n.t("startup.state.off")

