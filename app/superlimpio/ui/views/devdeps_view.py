"""Librerías de desarrollo regenerables (node_modules, .venv, target…)."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any

from ... import devdeps, fileops, i18n, plat
from ...safety import Risk
from ...util import fmt_count, fmt_date, fmt_size
from .. import dialogs, theme
from ..widgets import ScrollTree, SortableTable
from .base import View

ON, OFF = "☑", "☐"


class DevDepsView(View):
    icon = "code"
    view_key = "devdeps"

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, app)
        self.title = i18n.t("devdeps.title")
        self.subtitle = i18n.t("devdeps.subtitle")
        self.cancel_ev: threading.Event | None = None
        self.checked: set[str] = set()
        self._deleting = False

        bar = self.toolbar()
        ttk.Label(bar, text=i18n.t("devdeps.search_in")).pack(side="left", padx=(0, self.px(6)))
        self.path = tk.StringVar(value=os.path.expanduser("~"))
        ttk.Entry(bar, textvariable=self.path).pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text=i18n.t("common.browse"), command=self._browse).pack(side="left", padx=self.px(6))
        self.go = ttk.Button(bar, text=i18n.t("common.search"), style="Accent.TButton", command=self.search)
        self.go.pack(side="left")

        self.info = ttk.Label(self, text=i18n.t("devdeps.intro"), style="Muted.TLabel")
        self.info.pack(anchor="w", pady=(0, self.px(6)))

        cols = [("sel", "", 34, "center"), ("size", i18n.t("devdeps.col.size"), 95, "e"),
                ("kind", i18n.t("devdeps.col.kind"), 210, "w"), ("mtime", i18n.t("devdeps.col.modified"), 125, "w"),
                ("files", i18n.t("devdeps.col.files"), 85, "e"), ("project", i18n.t("devdeps.col.path"), 420, "w")]
        box = ScrollTree(self, cols, sf=self.sf)
        box.pack(fill="both", expand=True)
        self.tree = box.tree
        self.table = SortableTable(
            self.tree,
            render=lambda a: (ON if a.path in self.checked else OFF, fmt_size(a.size), a.kind, fmt_date(a.mtime),
                              fmt_count(a.files), a.path),
            sort_keys={"size": lambda a: a.size, "kind": lambda a: a.kind, "mtime": lambda a: a.mtime,
                       "project": lambda a: a.path.lower()},
            default_sort="size", tag_fn=lambda a: (theme.size_tag(a.size),), key_fn=lambda a: a.path)
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<space>", lambda e: self._toggle(self.tree.selection()))

        self.pbar = ttk.Progressbar(self, mode="determinate")
        self.pbar.pack(fill="x", pady=(self.px(6), 0))

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(self.px(10), 0))
        ttk.Button(btns, text=i18n.t("devdeps.mark_all"), command=lambda: self._mark(True)).pack(side="left")
        ttk.Button(btns, text=i18n.t("devdeps.unmark"), command=lambda: self._mark(False)).pack(
            side="left", padx=self.px(6))
        ttk.Button(btns, text=i18n.t("devdeps.mark_old"), command=self._mark_old).pack(side="left")
        ttk.Button(btns, text=i18n.t("common.open_location"), command=self._open).pack(side="left", padx=self.px(6))
        self.del_btn = ttk.Button(btns, text=i18n.t("common.delete_perm"), style="Danger.TButton",
                                  command=lambda: self._delete(True))
        self.del_btn.pack(side="right")
        self.rec_btn = ttk.Button(btns, text=i18n.t("devdeps.recycle_marked"), style="Accent.TButton",
                                  command=lambda: self._delete(False))
        self.rec_btn.pack(side="right", padx=self.px(6))
        self.note(self, i18n.t("devdeps.note")).pack(fill="x", pady=(self.px(6), 0))

    def _browse(self) -> None:
        d = filedialog.askdirectory(parent=self, initialdir=self.path.get(), title=i18n.t("devdeps.browse_title"))
        if d:
            self.path.set(os.path.normpath(d))

    def search(self) -> None:
        if self.cancel_ev and not self.cancel_ev.is_set():
            self.cancel_ev.set()
            return
        root = self.path.get().strip().strip('"')
        if not os.path.isdir(root):
            dialogs.error(self, i18n.t("disk.invalid_path"), root)
            return
        self.cancel_ev = ev = threading.Event()
        self.go.configure(text=i18n.t("common.stop"))
        self.checked.clear()
        self.table.set_rows([])

        def progress(cur: Any, n: Any) -> None:
            self.later("_search_progress", i18n.t("devdeps.searching", n=n, cur=cur[-100:]))

        self.work(lambda: devdeps.find_artifacts(root, progress, ev), "_done", "_search_failed")

    def _search_progress(self, text: str) -> None:
        self.info.configure(text=text)

    def pending(self) -> str:
        return i18n.t("app.pending.delete") if self._deleting else ""

    def handoff(self) -> dict[str, Any] | None:
        if not self.table.rows and self.cancel_ev is None:
            return None
        return {"path": self.path.get(), "rows": self.table.rows, "checked": self.checked,
                "cancel_ev": self.cancel_ev, "info": self.info.cget("text")}

    def adopt(self, state: dict[str, Any]) -> None:
        self.path.set(state["path"])
        self.checked = state["checked"]
        self.table.set_rows(state["rows"])
        self.info.configure(text=state["info"])
        self.cancel_ev = state["cancel_ev"]
        if self.cancel_ev is not None:   # la búsqueda sigue en marcha
            self.go.configure(text=i18n.t("common.stop"))

    def _search_failed(self, exc: BaseException) -> None:
        self.cancel_ev = None
        self.go.configure(text=i18n.t("common.search"))
        self.info.configure(text=f"{i18n.t('common.error')}: {exc}")

    def _done(self, arts: Any) -> None:
        self.cancel_ev = None
        self.go.configure(text=i18n.t("common.search"))
        self.table.set_rows(arts)
        total = sum(a.size for a in arts)
        self.info.configure(text=i18n.t("devdeps.done", n=len(arts), total=fmt_size(total)))
        self.status(i18n.t("devdeps.status", total=fmt_size(total)))

    # ----------------------------------------------------------- marcas
    def _click(self, e: Any) -> Any:
        if self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            iid = self.tree.identify_row(e.y)
            if iid:
                self._toggle([iid])
                return "break"
        return None

    def _toggle(self, iids: Any) -> None:
        for iid in iids:
            a = self.table.visible.get(iid)
            if not a:
                continue
            if a.path in self.checked:
                self.checked.discard(a.path)
            else:
                self.checked.add(a.path)
            self.tree.set(iid, "sel", ON if a.path in self.checked else OFF)
        self._update_info()

    def _mark(self, on: bool) -> None:
        self.checked = {a.path for a in self.table.rows} if on else set()
        self.table.refresh()
        self._update_info()

    def _mark_old(self) -> None:
        import time
        limit = time.time() - 182 * 86400
        self.checked = {a.path for a in self.table.rows if a.mtime and a.mtime < limit}
        self.table.refresh()
        self._update_info()

    def _update_info(self) -> None:
        sel = [a for a in self.table.rows if a.path in self.checked]
        self.info.configure(text=i18n.t("devdeps.marked", n=len(sel), size=fmt_size(sum(a.size for a in sel))))

    def _open(self) -> None:
        s = self.table.selected()
        if s:
            plat.open_in_explorer(s[0].path)

    def _delete(self, permanent: bool) -> None:
        if self._deleting:
            return
        sel = [a for a in self.table.rows if a.path in self.checked]
        if not sel:
            dialogs.info(self, i18n.t("devdeps.nothing_title"), i18n.t("devdeps.nothing_body"))
            return
        _ok, blocked = fileops.validate([a.path for a in sel])
        if blocked:
            dialogs.error(self, i18n.t("common.protected"), "\n".join(f"{p}: {r}" for p, r in blocked[:10]))
            return
        total = sum(a.size for a in sel)
        details = dialogs.summarize_paths([a.path for a in sel], [a.size for a in sel])
        if permanent:
            ok = dialogs.confirm(self, i18n.t("disk.delete.title"),
                                 i18n.t("devdeps.delete.body", n=len(sel), size=fmt_size(total)),
                                 details, risk=Risk.CRITICO, ok_text=i18n.t("devdeps.delete.ok"))
        else:
            ok = dialogs.confirm(self, i18n.t("disk.recycle.title"),
                                 i18n.t("devdeps.recycle.body", n=len(sel), size=fmt_size(total)),
                                 details, risk=Risk.MEDIO, ok_text=i18n.t("common.recycle").rstrip("…"))
        if not ok:
            return
        fn = fileops.delete_permanently if permanent else fileops.recycle
        self._deleting = True
        self.del_btn.state(["disabled"])
        self.rec_btn.state(["disabled"])
        self.pbar.configure(mode="indeterminate")
        self.pbar.start(12)
        self.status(i18n.t("common.deleting"))
        ev = self._del_cancel = threading.Event()   # View.shutdown lo activa si la ventana se cierra
        self.app.bg.run(lambda: fn([a.path for a in sel], ev), on_done=lambda r: self._deleted(sel, r),
                        on_error=lambda e: self._deleted(sel, (False, str(e))))

    def _deleted(self, sel: Any, res: Any) -> None:
        ok, msg = res
        self.pbar.stop()
        self.pbar.configure(mode="determinate", value=0)   # parada, la barra queda vacía
        self._deleting = False
        self.del_btn.state(["!disabled"])
        self.rec_btn.state(["!disabled"])
        gone = {a.path for a in sel if not os.path.exists(a.path)}
        self.table.rows = [a for a in self.table.rows if a.path not in gone]
        self.checked -= gone
        self.table.refresh()
        freed = sum(a.size for a in sel if a.path in gone)
        self.status(i18n.t("devdeps.deleted_status", msg=msg, size=fmt_size(freed)))
        self._update_info()
        if not ok:
            dialogs.error(self, i18n.t("common.result"), msg)
