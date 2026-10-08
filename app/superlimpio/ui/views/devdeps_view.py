"""Librerías de desarrollo regenerables (node_modules, .venv, target…)."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from ... import devdeps, fileops, winapi
from ...safety import Risk
from ...util import fmt_count, fmt_date, fmt_size
from .. import dialogs, theme
from ..widgets import ScrollTree, SortableTable
from .base import View

ON, OFF = "☑", "☐"


class DevDepsView(View):
    title = "Librerías de desarrollo"
    subtitle = "Dependencias y compilaciones que se pueden regenerar: node_modules, entornos virtuales, target…"
    icon = "code"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.cancel_ev: threading.Event | None = None
        self.checked: set[str] = set()

        bar = self.toolbar()
        ttk.Label(bar, text="Buscar en").pack(side="left", padx=(0, self.px(6)))
        self.path = tk.StringVar(value=os.path.expanduser("~"))
        ttk.Entry(bar, textvariable=self.path).pack(side="left", fill="x", expand=True)
        ttk.Button(bar, text="Examinar…", command=self._browse).pack(side="left", padx=self.px(6))
        self.go = ttk.Button(bar, text="Buscar", style="Accent.TButton", command=self.search)
        self.go.pack(side="left")

        self.info = ttk.Label(self, text="Busca carpetas de dependencias en tus proyectos. "
                                         "Marca las de proyectos que ya no uses.", style="Muted.TLabel")
        self.info.pack(anchor="w", pady=(0, self.px(6)))

        cols = [("sel", "", 34, "center"), ("size", "Tamaño", 95, "e"), ("kind", "Tipo", 210, "w"),
                ("mtime", "Modificado", 125, "w"), ("files", "Archivos", 85, "e"), ("project", "Proyecto", 420, "w")]
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
        self.tree.heading("project", text="Ruta")
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<space>", lambda e: self._toggle(self.tree.selection()))

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(self.px(10), 0))
        ttk.Button(btns, text="Marcar todo", command=lambda: self._mark(True)).pack(side="left")
        ttk.Button(btns, text="Desmarcar", command=lambda: self._mark(False)).pack(side="left", padx=self.px(6))
        ttk.Button(btns, text="Marcar > 6 meses sin tocar", command=self._mark_old).pack(side="left")
        ttk.Button(btns, text="Abrir ubicación", command=self._open).pack(side="left", padx=self.px(6))
        self.del_btn = ttk.Button(btns, text="Eliminar definitivamente…", style="Danger.TButton",
                                  command=lambda: self._delete(True))
        self.del_btn.pack(side="right")
        self.rec_btn = ttk.Button(btns, text="Enviar marcadas a la Papelera…", style="Accent.TButton",
                                  command=lambda: self._delete(False))
        self.rec_btn.pack(side="right", padx=self.px(6))
        self.note(self, "Consejo: node_modules suele tener decenas de miles de archivos pequeños; borrarlo "
                        "definitivamente es mucho más rápido que enviarlo a la Papelera. Se regenera con "
                        "«npm install» / «pip install -r requirements.txt» / «cargo build».") \
            .pack(fill="x", pady=(self.px(6), 0))

    def _browse(self) -> None:
        d = filedialog.askdirectory(parent=self, initialdir=self.path.get(), title="Carpeta de proyectos")
        if d:
            self.path.set(os.path.normpath(d))

    def search(self) -> None:
        if self.cancel_ev and not self.cancel_ev.is_set():
            self.cancel_ev.set()
            return
        root = self.path.get().strip().strip('"')
        if not os.path.isdir(root):
            dialogs.error(self, "Ruta no válida", root)
            return
        self.cancel_ev = ev = threading.Event()
        self.go.configure(text="Detener")
        self.checked.clear()
        self.table.set_rows([])

        def progress(cur, n):
            self.app.bg.call_in_ui(self.info.configure, {"text": f"Buscando… {n} encontradas · {cur[-100:]}"})

        self.app.bg.run(lambda: devdeps.find_artifacts(root, progress, ev), on_done=self._done)

    def _done(self, arts) -> None:
        self.cancel_ev = None
        self.go.configure(text="Buscar")
        self.table.set_rows(arts)
        total = sum(a.size for a in arts)
        self.info.configure(text=f"{len(arts)} carpetas regenerables · {fmt_size(total)} en total")
        self.status(f"Librerías de desarrollo: {fmt_size(total)}")

    # ----------------------------------------------------------- marcas
    def _click(self, e):
        if self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            iid = self.tree.identify_row(e.y)
            if iid:
                self._toggle([iid])
                return "break"
        return None

    def _toggle(self, iids) -> None:
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
        self.info.configure(text=f"{len(sel)} marcadas · {fmt_size(sum(a.size for a in sel))} a liberar")

    def _open(self) -> None:
        s = self.table.selected()
        if s:
            winapi.open_in_explorer(s[0].path)

    def _delete(self, permanent: bool) -> None:
        sel = [a for a in self.table.rows if a.path in self.checked]
        if not sel:
            dialogs.info(self, "Nada marcado", "Marca las carpetas pulsando en la casilla ☐ de cada fila.")
            return
        _ok, blocked = fileops.validate([a.path for a in sel])
        if blocked:
            dialogs.error(self, "Protegido", "\n".join(f"{p}: {r}" for p, r in blocked[:10]))
            return
        total = sum(a.size for a in sel)
        details = dialogs.summarize_paths([a.path for a in sel], [a.size for a in sel])
        if permanent:
            ok = dialogs.confirm(self, "Eliminar definitivamente",
                                 f"Se borrarán para siempre {len(sel)} carpetas ({fmt_size(total)}). "
                                 "Son regenerables, pero no se podrán recuperar de la Papelera.",
                                 details, risk=Risk.CRITICO, ok_text="Eliminar para siempre")
        else:
            ok = dialogs.confirm(self, "Enviar a la Papelera",
                                 f"Se moverán {len(sel)} carpetas ({fmt_size(total)}) a la Papelera.",
                                 details, risk=Risk.MEDIO, ok_text="Enviar a la Papelera")
        if not ok:
            return
        fn = fileops.delete_permanently if permanent else fileops.recycle
        self.status("Eliminando…")
        self.app.bg.run(lambda: fn([a.path for a in sel]), on_done=lambda r: self._deleted(sel, r))

    def _deleted(self, sel, res) -> None:
        ok, msg = res
        gone = {a.path for a in sel if not os.path.exists(a.path)}
        self.table.rows = [a for a in self.table.rows if a.path not in gone]
        self.checked -= gone
        self.table.refresh()
        freed = sum(a.size for a in sel if a.path in gone)
        self.status(f"{msg} · {fmt_size(freed)} liberados")
        self._update_info()
        if not ok:
            dialogs.error(self, "Resultado", msg)
