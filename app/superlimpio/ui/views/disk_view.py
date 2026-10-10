"""Analizador de disco con vista de árbol tipo Explorador.

Cada carpeta muestra su peso TOTAL (incluidas subcarpetas), una barra de uso
relativa a su carpeta padre y el porcentaje. Las filas de más de 100 MB, 1 GB
y 10 GB se colorean para detectarlas de un vistazo.
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any

from ... import criticality, fileops, helper, i18n, scanner, plat
from ...safety import Risk
from ...util import fmt_count, fmt_date, fmt_pct, fmt_size, text_bar
from .. import compress_dialog, dialogs, theme
from ..widgets import ScrollTree, SortableTable
from .base import View

DUMMY = "__dummy__"
WARN_MARK = "\u26a0"   # señal de aviso delante de lo que es del sistema
PAGE = 400   # filas que se añaden de una vez al desplegar una carpeta


class DiskView(View):
    icon = "drive"
    view_key = "disk"

    def __init__(self, master: Any, app: Any) -> None:
        super().__init__(master, app)
        self.title = i18n.t("disk.title")
        self.subtitle = i18n.t("disk.subtitle")
        self.result: scanner.ScanResult | None = None
        self.cancel_ev: threading.Event | None = None
        self.items: dict[str, tuple] = {}   # iid -> ("dir", node) | ("file", node, rec) | ("rest", node)
        self.node_iid: dict[int, str] = {}  # id(node) -> iid
        self._deleting = False
        self._del_cancel: threading.Event | None = None   # detiene un borrado a mitad de lote

        # ---- barra de direcciones (estilo Explorador)
        bar = self.toolbar()
        drives = plat.list_drives()
        self.path_var = tk.StringVar(value=drives[0] if drives else os.path.expanduser("~"))
        ttk.Label(bar, text=i18n.t("disk.location")).pack(side="left", padx=(0, self.px(6)))
        # En Windows son letras («C:\»); en Linux, puntos de montaje, que son más largos.
        self.drive_cb = ttk.Combobox(bar, values=drives, state="readonly",
                                     width=max(6, min(22, max((len(d) for d in drives), default=6) + 1)))
        if drives:
            self.drive_cb.set(drives[0])
        self.drive_cb.bind("<<ComboboxSelected>>", lambda e: self.path_var.set(self.drive_cb.get()))
        self.drive_cb.pack(side="left")
        ent = ttk.Entry(bar, textvariable=self.path_var)
        ent.pack(side="left", fill="x", expand=True, padx=self.px(6))
        ent.bind("<Return>", lambda e: self.start_scan(self.path_var.get()))
        ttk.Button(bar, text=i18n.t("common.browse"), command=self._browse).pack(side="left")
        self.scan_btn = ttk.Button(bar, text=i18n.t("common.analyze"), style="Accent.TButton",
                                   command=lambda: self.start_scan(self.path_var.get()))
        self.scan_btn.pack(side="left", padx=(self.px(6), 0))
        self.cancel_btn = ttk.Button(bar, text=i18n.t("common.stop"), command=self._cancel)
        self.cancel_btn.pack(side="left", padx=(self.px(6), 0))
        self.cancel_btn.state(["disabled"])

        prog = ttk.Frame(self)
        prog.pack(fill="x", pady=(0, self.px(8)))
        self.pbar = ttk.Progressbar(prog, mode="determinate", length=self.px(160))
        self.pbar.pack(side="left")
        # La leyenda se coloca antes que el texto de avance: si falta ancho, se recorta el texto.
        legend = tk.Frame(prog, bg=theme.BG)
        legend.pack(side="right")
        self.prog_lbl = ttk.Label(prog, text=i18n.t("disk.prompt"), style="Muted.TLabel")
        self.prog_lbl.pack(side="left", padx=self.px(10), fill="x", expand=True)
        for color, txt in ((theme.ROW_MID, i18n.t("disk.legend.mid")), (theme.ROW_BIG, i18n.t("disk.legend.big")),
                           (theme.ROW_HUGE, i18n.t("disk.legend.huge"))):
            tk.Label(legend, text="   ", bg=color, highlightthickness=1,
                     highlightbackground=theme.BORDER).pack(side="left", padx=(self.px(8), 3))
            tk.Label(legend, text=txt, bg=theme.BG, fg=theme.MUTED, font=self.fonts.small).pack(side="left")
        # Solo se destaca lo que es del propio sistema y cuyo borrado daña a Windows.
        for level, key in ((3, "disk.legend.vital"), (2, "disk.legend.important")):
            tk.Label(legend, text=f"{WARN_MARK} {i18n.t(key)}", bg=theme.BG, fg=theme.LEVEL_COLORS[level],
                     font=self.fonts.small).pack(side="left", padx=(self.px(12), 0))

        # ---- panel divisible: tablas arriba, detalles abajo (ambos redimensionables)
        split = ttk.PanedWindow(self, orient="vertical")
        split.pack(fill="both", expand=True)

        self.nb = ttk.Notebook(split)

        cols = [("size", i18n.t("disk.col.size"), 95, "e"), ("bar", i18n.t("disk.col.usage"), 120, "w"),
                ("pct", "%", 60, "e"), ("files", i18n.t("disk.col.files"), 85, "e"),
                ("mtime", i18n.t("disk.col.modified"), 125, "w"), ("level", i18n.t("memory.col.level"), 110, "w"),
                ("hint", i18n.t("disk.col.what"), 300, "w")]
        self.tree_box = ScrollTree(self.nb, cols, show_tree=True, sf=self.sf,
                                   tree_heading=i18n.t("disk.col.name"), tree_width=340)
        self.tree = self.tree_box.tree
        self.nb.add(self.tree_box, text=i18n.t("disk.tab.folders"))
        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Button-3>", self._context_menu)
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Delete>", lambda e: self._recycle())

        fcols = [("name", i18n.t("disk.col.file"), 260, "w"), ("size", i18n.t("disk.col.size"), 95, "e"),
                 ("level", i18n.t("memory.col.level"), 110, "w"),
                 ("type", i18n.t("disk.col.type"), 150, "w"), ("mtime", i18n.t("disk.col.modified"), 125, "w"),
                 ("folder", i18n.t("disk.col.folder"), 420, "w")]
        self.files_box = ScrollTree(self.nb, fcols, sf=self.sf)
        self.files_tbl = SortableTable(
            self.files_box.tree,
            render=lambda r: (r["name"], fmt_size(r["size"]), r["mark"][0], r["type"] or r["mark"][2],
                              fmt_date(r["mtime"]), r["folder"]),
            sort_keys={"name": lambda r: r["name"].lower(), "size": lambda r: r["size"],
                       "level": lambda r: (r["mark"][1], r["size"]),
                       "mtime": lambda r: r["mtime"], "folder": lambda r: r["folder"].lower(),
                       "type": lambda r: r["type"]},
            default_sort="size", tag_fn=lambda r: (theme.size_tag(r["size"]), r["mark"][1]),
            key_fn=lambda r: r["path"])
        self.nb.add(self.files_box, text=i18n.t("disk.tab.files"))
        self.files_box.tree.bind("<Button-3>", self._context_menu)
        self.files_box.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.files_box.tree.bind("<Delete>", lambda e: self._recycle())

        tcols = [("ext", i18n.t("disk.col.type"), 160, "w"), ("size", i18n.t("disk.col.size"), 100, "e"),
                 ("bar", i18n.t("disk.col.usage"), 140, "w"), ("pct", "%", 70, "e"),
                 ("count", i18n.t("disk.col.count"), 100, "e"), ("desc", i18n.t("disk.col.desc"), 300, "w")]
        self.types_box = ScrollTree(self.nb, tcols, sf=self.sf, selectmode="browse")
        self.types_tbl = SortableTable(
            self.types_box.tree,
            render=lambda r: (scanner.ext_display(r["ext"]), fmt_size(r["size"]),
                              text_bar(r["size"], r["total"], 14),
                              fmt_pct(r["size"], r["total"]), fmt_count(r["count"]), r["desc"]),
            sort_keys={"ext": lambda r: r["ext"], "size": lambda r: r["size"], "count": lambda r: r["count"]},
            default_sort="size")
        self.nb.add(self.types_box, text=i18n.t("disk.tab.types"))

        # ---- panel de detalles / acciones
        det = tk.Frame(split, bg=theme.CARD, highlightthickness=1, highlightbackground=theme.BORDER)
        inner = tk.Frame(det, bg=theme.CARD)
        inner.pack(fill="x", padx=self.px(12), pady=self.px(8))
        self.sel_name = tk.Label(inner, text=i18n.t("common.nothing_selected"), font=self.fonts.bold,
                                 bg=theme.CARD, fg=theme.TEXT, anchor="w")
        self.sel_name.pack(side="left")
        self.sel_info = tk.Label(inner, text="", font=self.fonts.small, bg=theme.CARD, fg=theme.MUTED,
                                 anchor="w")
        self.sel_info.pack(side="left", padx=self.px(10), fill="x", expand=True)
        # Qué es lo seleccionado para el sistema y qué riesgo tiene borrarlo.
        self.sel_risk = tk.Label(det, text="", font=self.fonts.small, bg=theme.CARD, fg=theme.MUTED,
                                 anchor="w", justify="left", wraplength=self.px(900))
        self.sel_risk.pack(fill="x", padx=self.px(12), pady=(0, self.px(6)))
        self.sel_risk.bind("<Configure>", lambda e: self.sel_risk.configure(wraplength=max(200, e.width - 4)))
        # Los botones van en su propia fila: así caben todos aunque la ventana sea estrecha.
        actions = tk.Frame(det, bg=theme.CARD)
        actions.pack(fill="x", padx=self.px(12), pady=(0, self.px(8)))
        self.btn_del = ttk.Button(actions, text=i18n.t("common.delete_perm"), style="Danger.TButton",
                                  command=self._delete_perm)
        self.btn_del.pack(side="right")
        self.btn_rec = ttk.Button(actions, text=i18n.t("common.recycle"), command=self._recycle)
        self.btn_rec.pack(side="right", padx=self.px(6))
        self.btn_scan_here = ttk.Button(actions, text=i18n.t("disk.scan_here"), command=self._scan_here)
        self.btn_scan_here.pack(side="right")
        self.btn_open = ttk.Button(actions, text=i18n.t("common.open_explorer"), command=self._open)
        self.btn_open.pack(side="right", padx=self.px(6))
        self.btn_zip = ttk.Button(actions, text=i18n.t("zip.button"), command=self._compress)
        self.btn_zip.pack(side="right")
        self._set_actions(False)

        split.add(self.nb, weight=1)
        split.add(det, weight=0)
        # Al cambiar de pestaña, el panel de abajo pasa a hablar de la tabla que se ve.
        self.nb.bind("<<NotebookTabChanged>>", self._on_select)

        self.menu = tk.Menu(self, tearoff=False)
        self.menu.add_command(label=i18n.t("common.open_explorer"), command=self._open)
        self.menu.add_command(label=i18n.t("common.copy_path"), command=self._copy_path)
        self.menu.add_command(label=i18n.t("disk.scan_this_folder"), command=self._scan_here)
        self.menu.add_command(label=i18n.t("zip.button"), command=self._compress)
        self.menu.add_separator()
        self.menu.add_command(label=i18n.t("common.recycle"), command=self._recycle)
        self.menu.add_command(label=i18n.t("common.delete_perm"), command=self._delete_perm)

    # ================================================================ escaneo
    def _browse(self) -> None:
        d = filedialog.askdirectory(parent=self, initialdir=self.path_var.get() or None,
                                    title=i18n.t("disk.browse_title"))
        if d:
            self.path_var.set(os.path.normpath(d))

    def start_scan(self, path: str) -> None:
        path = (path or "").strip().strip('"')
        if not path or not os.path.isdir(path):
            dialogs.error(self, i18n.t("disk.invalid_path"), i18n.t("disk.no_folder", path=path))
            return
        if self.cancel_ev:
            self.cancel_ev.set()
        self.path_var.set(path)
        self.cancel_ev = threading.Event()
        self.scan_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.pbar.configure(mode="indeterminate")
        self.pbar.start(12)
        self.prog_lbl.configure(text=i18n.t("disk.analyzing", path=path))
        self.status(i18n.t("disk.analyzing_status", path=path))
        ev = self.cancel_ev

        def progress_ui(kw: dict[str, Any]) -> None:
            if ev is self.cancel_ev:   # el avance de un análisis ya sustituido no se enseña
                self.prog_lbl.configure(**kw)

        def progress(p: scanner.ScanProgress) -> None:
            txt = i18n.t("disk.scan_progress", files=fmt_count(p.files), dirs=fmt_count(p.dirs),
                         bytes=fmt_size(p.bytes), secs=f"{p.elapsed:.0f}", current=p.current[-90:])
            self.app.bg.call_in_ui(progress_ui, {"text": txt})

        self.app.bg.run(lambda: scanner.scan(path, progress, ev),
                        on_done=lambda res: self._scan_done(res, ev),
                        on_error=lambda exc: self._scan_failed(exc, ev))

    def pending(self) -> str:
        return i18n.t("app.pending.delete") if self._deleting else ""

    def _cancel(self) -> None:
        if self._del_cancel is not None:   # hay un borrado en marcha: se detiene tras el elemento actual
            self._del_cancel.set()
            self.prog_lbl.configure(text=i18n.t("disk.stopping"))
        if self.cancel_ev:
            self.cancel_ev.set()
            self.prog_lbl.configure(text=i18n.t("disk.stopping"))

    def _scan_failed(self, exc: BaseException, ev: threading.Event) -> None:
        if ev is not self.cancel_ev:
            return
        self.cancel_ev = None
        self._end_progress()
        dialogs.error(self, i18n.t("disk.scan_error"), str(exc))

    def _end_progress(self) -> None:
        self._idle_bar()
        self.scan_btn.state(["!disabled"])
        self.cancel_btn.state(["disabled"])

    def _idle_bar(self) -> None:
        """En reposo la barra queda vacía (una barra indeterminada parada deja un bloque fijo)."""
        self.pbar.stop()
        self.pbar.configure(mode="determinate", value=0)

    def _scan_done(self, res: scanner.ScanResult, ev: threading.Event) -> None:
        if ev is not self.cancel_ev:
            return   # se lanzó otro análisis encima: este resultado, a medias, ya no interesa
        self.cancel_ev = None
        self._end_progress()
        self.result = res
        extra = []
        if res.cancelled:
            extra.append(i18n.t("disk.extra.cancelled"))
        if res.errors:
            extra.append(i18n.t("disk.extra.errors", n=fmt_count(res.errors)))
        if res.skipped_mounts:
            extra.append(i18n.t("disk.extra.mounts", n=fmt_count(res.skipped_mounts)))
        if res.cloud_size:
            extra.append(i18n.t("disk.extra.cloud", size=fmt_size(res.cloud_size)))
        if res.skipped_links:
            extra.append(i18n.t("disk.extra.links", n=fmt_count(res.skipped_links)))
        self.prog_lbl.configure(
            text=i18n.t("disk.result_summary", size=fmt_size(res.root.size), files=fmt_count(res.root.files),
                        dirs=fmt_count(res.root.dirs), secs=f"{res.elapsed:.1f}")
            + ("   ·   " + " · ".join(extra) if extra else ""))
        self.status(i18n.t("disk.scan_done_status", path=res.root.path))
        self._fill_tree()
        self._fill_files()
        self._fill_types()

    # ============================================================== árbol
    def _fill_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.items.clear()
        self.node_iid.clear()
        root = self.result.root
        iid = self._insert_dir("", root, root.size)
        self.tree.item(iid, open=True)
        self._populate(iid)
        self.tree.selection_set(iid)
        self.tree.focus(iid)

    def _dir_values(self, node: scanner.DirNode, parent_size: int) -> tuple:
        label, _tag, what = _system_mark(node.path)
        hint = scanner.hint_for(node.name, True) or what
        if node.errors and not hint:
            hint = i18n.t("disk.subdirs_unreadable")
        if node.cloud_size and not hint:
            hint = i18n.t("disk.cloud_extra", size=fmt_size(node.cloud_size))
        return (fmt_size(node.size), text_bar(node.size, parent_size), fmt_pct(node.size, parent_size),
                fmt_count(node.files), fmt_date(node.mtime), label, hint)

    def _dir_tags(self, node: scanner.DirNode) -> tuple:
        return theme.size_tag(node.size), "bar", _system_mark(node.path)[1]

    def _insert_dir(self, parent: str, node: scanner.DirNode, parent_size: int, index: Any = "end") -> str:
        iid = self.tree.insert(parent, index, text=f" {node.name}", image=self.app.icons["folder"],
                               values=self._dir_values(node, parent_size), tags=self._dir_tags(node))
        self.items[iid] = ("dir", node)
        self.node_iid[id(node)] = iid
        if node.children or node.top_files or node.small_files_count:
            self.tree.insert(iid, "end", iid=f"{iid}{DUMMY}", text="")
        return iid

    def _populate(self, iid: str) -> None:
        kids = self.tree.get_children(iid)
        if not (len(kids) == 1 and kids[0].endswith(DUMMY)):
            return
        self.tree.delete(kids[0])
        _kind, node = self.items[iid][:2]
        entries: list[tuple[int, str, object]] = [(c.size, "dir", c) for c in node.children]
        entries += [(f[0], "file", f) for f in node.top_files]
        entries.sort(key=lambda e: e[0], reverse=True)
        self._insert_page(iid, node, entries)

    def _insert_page(self, iid: str, node: scanner.DirNode, entries: list[Any]) -> None:
        """Inserta las PAGE filas siguientes. Las carpetas con miles de elementos (WinSxS,
        node_modules…) se cargan por tramos para que la ventana no se quede parada."""
        for _size, kind, obj in entries[:PAGE]:
            if kind == "dir":
                self._insert_dir(iid, obj, node.size)
            elif obj in node.top_files:  # puede haberse borrado desde «Archivos más grandes»
                fsize, fname, fmtime = obj
                label, tag, what = _system_mark(os.path.join(node.path, fname))
                fid = self.tree.insert(iid, "end", text=f" {fname}", image=self.app.icons["file"],
                                       values=(fmt_size(fsize), text_bar(fsize, node.size),
                                               fmt_pct(fsize, node.size), "", fmt_date(fmtime), label,
                                               scanner.hint_for(fname, False) or what),
                                       tags=(theme.size_tag(fsize), "bar", tag))
                self.items[fid] = ("file", node, obj)
        rest = entries[PAGE:]
        if rest:
            left = sum(e[0] for e in rest)
            mid = self.tree.insert(iid, "end", text=i18n.t("disk.show_more", n=fmt_count(len(rest))),
                                   image=self.app.icons["group"],
                                   values=(fmt_size(left), text_bar(left, node.size), fmt_pct(left, node.size),
                                           "", "", "", i18n.t("disk.show_more_hint")),
                                   tags=("muted", "bar"))
            self.items[mid] = ("more", node, rest)
            return
        if node.small_files_count:
            rid = self.tree.insert(iid, "end", text=i18n.t("disk.small_files", n=fmt_count(node.small_files_count)),
                                   image=self.app.icons["group"],
                                   values=(fmt_size(node.small_files_size),
                                           text_bar(node.small_files_size, node.size),
                                           fmt_pct(node.small_files_size, node.size),
                                           fmt_count(node.small_files_count), "", "",
                                           i18n.t("disk.small_files_hint")),
                                   tags=("muted", "bar"))
            self.items[rid] = ("rest", node)

    def _on_open(self, _e: Any = None) -> None:
        iid = self.tree.focus()
        if iid in self.items and self.items[iid][0] == "dir":
            self._populate(iid)

    def _on_double(self, e: Any) -> None:
        iid = self.tree.identify_row(e.y)
        if iid in self.items and self.items[iid][0] == "file":
            self._open()

    # ===================================================== otras pestañas
    def _fill_files(self) -> None:
        rows = []
        for size, path, mtime in self.result.top_files:
            name = os.path.basename(path)
            ext = os.path.splitext(name)[1].lower()
            rows.append({"name": name, "size": size, "mtime": mtime, "folder": os.path.dirname(path),
                         "path": path, "type": scanner.file_type_label(ext), "mark": _system_mark(path)})
        self.files_tbl.set_rows(rows)

    def _fill_types(self) -> None:
        total = sum(v[0] for v in self.result.by_extension.values()) or 1
        rows = [{"ext": ext, "size": v[0], "count": v[1], "total": total, "desc": scanner.ext_desc(ext)}
                for ext, v in self.result.by_extension.items()]
        rows.sort(key=lambda r: r["size"], reverse=True)
        self.types_tbl.set_rows(rows[:400])

    # ========================================================== selección
    def _active_tree(self) -> ttk.Treeview | None:
        """La tabla que se está viendo. «Por tipo» es solo informativa: ahí no hay nada que
        abrir ni borrar, y lo marcado en otra pestaña no debe poder borrarse desde ella."""
        tab = self.nb.index(self.nb.select())
        return self.tree if tab == 0 else (self.files_box.tree if tab == 1 else None)

    def _selected(self) -> list[dict[str, Any]]:
        """Elementos seleccionados como {path, size, is_dir, ref}."""
        out = []
        tree = self._active_tree()
        if tree is None:
            return out
        if tree is self.tree:
            for iid in tree.selection():
                it = self.items.get(iid)
                if not it:
                    continue
                if it[0] == "dir":
                    out.append({"path": it[1].path, "size": it[1].size, "is_dir": True, "iid": iid})
                elif it[0] == "file":
                    node, rec = it[1], it[2]
                    out.append({"path": os.path.join(node.path, rec[1]), "size": rec[0], "is_dir": False,
                                "iid": iid})
        else:
            for r in self.files_tbl.selected():
                out.append({"path": r["path"], "size": r["size"], "is_dir": False, "row": r})
        return out

    def _load_more(self, mid: str) -> None:
        _kind, node, rest = self.items.pop(mid)
        parent = self.tree.parent(mid)
        self.tree.delete(mid)
        self._insert_page(parent, node, rest)

    def _on_select(self, _e: Any = None) -> None:
        picked = self.tree.selection()
        if len(picked) == 1 and self.items.get(picked[0], ("",))[0] == "more":
            self._load_more(picked[0])
            return
        sel = self._selected()
        self._show_risk(sel)
        if not sel:
            self.sel_name.configure(text=i18n.t("common.nothing_selected"))
            self.sel_info.configure(text="")
            self._set_actions(False)
            return
        if len(sel) == 1:
            s = sel[0]
            name = os.path.basename(s['path'].rstrip(os.sep)) or s['path']
            self.sel_name.configure(text=i18n.t("disk.sel_single", name=name, size=fmt_size(s['size'])))
            self.sel_info.configure(text=s["path"])
        else:
            total = sum(s["size"] for s in sel)
            self.sel_name.configure(text=i18n.t("disk.sel_multi", n=len(sel), size=fmt_size(total)))
            self.sel_info.configure(text="")
        self._set_actions(True, single_dir=len(sel) == 1 and sel[0]["is_dir"])

    def _show_risk(self, sel: list[dict[str, Any]]) -> None:
        """Explica qué es lo seleccionado para el sistema y qué pasa si se borra."""
        if not sel:
            self.sel_risk.configure(text="", fg=theme.MUTED)
            return
        found = [criticality.assess_path(s["path"]) for s in sel[:200]]
        a = criticality.worst(found)
        text = i18n.t("disk.risk_line", level=a.label, text=a.text)
        if len(sel) > 1:
            delicate = sum(1 for f in found if f.level >= criticality.Level.CAUTION)
            if delicate:
                text = i18n.t("disk.risk_multi", n=delicate, total=len(sel)) + text
        if a.system:   # el color y el aviso, solo para lo que daña al sistema
            text = f"{WARN_MARK} {text}"
        self.sel_risk.configure(text=text, fg=theme.LEVEL_COLORS[int(a.level)] if a.system else theme.MUTED)

    def _delicate(self, sel: list[dict[str, Any]]) -> tuple[str, str]:
        """(aviso para el mensaje, líneas para el detalle) de lo seleccionado que no es un
        archivo corriente: datos de programas, perfiles de otros usuarios..."""
        lines = []
        for s in sel[:200]:
            a = criticality.assess_path(s["path"])
            if a.level >= criticality.Level.CAUTION:
                lines.append(f"[{a.label}] {s['path']}\n      {a.text}")
        if not lines:
            return "", ""
        return i18n.t("disk.delicate_warning", n=len(lines)), i18n.t("disk.delicate_details",
                                                                      items="\n".join(lines[:12]))

    def _set_actions(self, on: bool, single_dir: bool = False) -> None:
        enabled = on and not self._deleting
        for b in (self.btn_del, self.btn_rec, self.btn_open, self.btn_zip):
            b.state(["!disabled"] if enabled else ["disabled"])
        self.btn_scan_here.state(["!disabled"] if (single_dir and not self._deleting) else ["disabled"])

    def _context_menu(self, e: Any) -> None:
        tree = e.widget
        iid = tree.identify_row(e.y)
        if iid and iid not in tree.selection():
            tree.selection_set(iid)
        if tree.selection():
            self.menu.tk_popup(e.x_root, e.y_root)

    # ============================================================ acciones
    def _open(self) -> None:
        sel = self._selected()
        if sel:
            ok, msg = plat.open_in_explorer(sel[0]["path"])
            if not ok:
                self.status(msg)

    def _copy_path(self) -> None:
        sel = self._selected()
        if sel:
            self.clipboard_clear()
            self.clipboard_append("\n".join(s["path"] for s in sel))
            self.status(i18n.t("disk.path_copied"))

    def _scan_here(self) -> None:
        sel = self._selected()
        if sel and sel[0]["is_dir"]:
            self.start_scan(sel[0]["path"])

    def _compress(self) -> None:
        """Abre la ventana «Comprimir» con lo seleccionado. Los originales solo se leen; si
        el usuario pidió enviarlos después a la Papelera, se le vuelve a preguntar aquí."""
        if self._deleting:
            return
        sel = self._selected()
        if not sel:
            return
        dlg = compress_dialog.ask(self, [s["path"] for s in sel])
        res = dlg.result
        if res is None:
            return
        self.status(i18n.t("zip.status", name=os.path.basename(res.dest), before=fmt_size(res.in_bytes),
                           after=fmt_size(res.out_bytes)))
        if not (dlg.want_recycle and res.verified and not res.skipped) or self._check_blocked(sel):
            return
        total = sum(s["size"] for s in sel)
        if not dialogs.confirm(
                self, i18n.t("zip.recycle.title"),
                i18n.t("zip.recycle.body", n=len(sel), size=fmt_size(total), name=os.path.basename(res.dest)),
                dialogs.summarize_paths([s["path"] for s in sel], [s["size"] for s in sel]),
                risk=Risk.MEDIO, ok_text=i18n.t("common.recycle").rstrip("…")):
            return
        self._do_delete(sel, fileops.recycle)

    def _check_blocked(self, sel: list[dict[str, Any]]) -> bool:
        _ok, blocked = fileops.validate([s["path"] for s in sel])
        if blocked:
            dialogs.error(self, i18n.t("disk.blocked_title"),
                          i18n.t("disk.blocked_body",
                                 items="\n".join(f"• {p}\n   {r}" for p, r in blocked[:10])))
            return True
        return False

    def _recycle(self) -> None:
        if self._deleting:
            return
        sel = self._selected()
        if not sel or self._check_blocked(sel):
            return
        total = sum(s["size"] for s in sel)
        warn, extra = self._delicate(sel)
        if not dialogs.confirm(
                self, i18n.t("disk.recycle.title"),
                i18n.t("disk.recycle.body", n=len(sel), size=fmt_size(total)) + warn,
                dialogs.summarize_paths([s["path"] for s in sel], [s["size"] for s in sel]) + extra,
                risk=Risk.ALTO if warn else Risk.MEDIO, ok_text=i18n.t("common.recycle").rstrip("…")):
            return
        self._do_delete(sel, fileops.recycle)

    def _delete_perm(self) -> None:
        if self._deleting:
            return
        sel = self._selected()
        if not sel or self._check_blocked(sel):
            return
        total = sum(s["size"] for s in sel)
        warn, extra = self._delicate(sel)
        if not dialogs.confirm(
                self, i18n.t("disk.delete.title"),
                i18n.t("disk.delete.body", n=len(sel), size=fmt_size(total)) + warn,
                dialogs.summarize_paths([s["path"] for s in sel], [s["size"] for s in sel]) + extra,
                risk=Risk.CRITICO, ok_text=i18n.t("disk.delete.ok")):
            return
        self._do_delete(sel, fileops.delete_permanently)

    def _do_delete(self, sel: list[dict[str, Any]], fn: Any) -> None:
        # Indicador de operación en curso: barra indeterminada + botones deshabilitados.
        self._deleting = True
        self._set_actions(False)
        self.pbar.configure(mode="indeterminate")
        self.pbar.start(12)
        self.prog_lbl.configure(text=i18n.t("common.deleting"))
        self.status(i18n.t("common.deleting"))
        ev = self._del_cancel = threading.Event()
        self.cancel_btn.state(["!disabled"])
        permanent = fn is fileops.delete_permanently
        self.app.bg.run(lambda: fn([s["path"] for s in sel], ev),
                        on_done=lambda r: self._after_delete(sel, r, permanent),
                        on_error=lambda e: self._after_delete(sel, (False, str(e)), False))

    def _after_delete(self, sel: list[dict[str, Any]], res: tuple[bool, str], permanent: bool = False) -> None:
        ok, msg = res
        stopped = self._del_cancel is not None and self._del_cancel.is_set()
        self._del_cancel = None
        # Actualiza la pantalla cuanto antes para reflejar lo que ya no está.
        if self.cancel_ev is None:   # si hay un análisis en marcha, la barra sigue siendo suya
            self._idle_bar()
            self.cancel_btn.state(["disabled"])
        self._deleting = False
        removed = [s for s in sel if not os.path.exists(s["path"])]
        for s in removed:
            self._remove_from_model(s)
        freed = sum(s["size"] for s in removed)
        self.prog_lbl.configure(text=i18n.t("disk.delete_status", msg=msg, size=fmt_size(freed),
                                            removed=len(removed), total=len(sel)))
        self.status(i18n.t("disk.delete_status", msg=msg, size=fmt_size(freed),
                           removed=len(removed), total=len(sel)))
        if not ok:
            dialogs.error(self, i18n.t("common.result"), msg)
            left = [s for s in sel if os.path.lexists(s["path"])]
            if permanent and left and not stopped and not self.app.is_admin and helper.available():
                self._offer_elevated_delete(left)
        self._on_select()

    def _offer_elevated_delete(self, left: list[dict[str, Any]]) -> None:
        """Lo que no se pudo borrar (casi siempre por permisos) se puede encargar al auxiliar
        elevado. Es otra acción: se enseña exactamente qué rutas y se vuelve a confirmar. El
        auxiliar las comprueba de nuevo con las mismas reglas de rutas protegidas."""
        if self._check_blocked(left):
            return
        paths = [s["path"] for s in left]
        details = (dialogs.summarize_paths(paths, [s["size"] for s in left]) + "\n\n"
                   + helper.describe(helper.delete_order(paths)))
        if not dialogs.confirm(self, i18n.t("disk.elevated.title"),
                               i18n.t("disk.elevated.body", n=len(left)), details,
                               risk=Risk.CRITICO, ok_text=i18n.t("disk.delete.ok")):
            return
        self._deleting = True
        self._set_actions(False)
        self.pbar.configure(mode="indeterminate")
        self.pbar.start(12)
        self.prog_lbl.configure(text=i18n.t("common.deleting"))
        order = helper.delete_order(paths)

        def done(result: dict[str, Any]) -> None:
            self._after_delete(left, (bool(result.get("ok")), str(result.get("msg", ""))), False)

        self.app.bg.run(lambda: helper.run(order), on_done=done,
                        on_error=lambda e: self._after_delete(left, (False, str(e)), False))

    def _remove_from_model(self, s: dict[str, Any]) -> None:
        """Quita el elemento de las vistas y descuenta su tamaño de las carpetas padre."""
        path = s["path"]
        if self.result:
            self.files_tbl.rows = [r for r in self.files_tbl.rows if not
                                   (r["path"] == path or r["path"].startswith(path + os.sep))]
            self.files_tbl.refresh()
        iid = s.get("iid")
        if not iid:
            # Borrado desde «Archivos más grandes»: localizar en el árbol si ya está cargado
            parent_dir = os.path.dirname(path)
            for k, it in list(self.items.items()):
                if it[0] == "file" and it[1].path == parent_dir and it[2][1] == os.path.basename(path):
                    iid = k
                    break
        if iid and iid in self.items:
            it = self.items[iid]
            if it[0] == "dir":
                node = it[1]
                parent = node.parent
                if parent is not None and node in parent.children:
                    parent.children.remove(node)
                delta, dfiles = node.size, node.files
            else:
                parent, rec = it[1], it[2]
                if rec in parent.top_files:
                    parent.top_files.remove(rec)
                parent.own_size -= rec[0]
                delta, dfiles = rec[0], 1
            self.tree.delete(iid)
            self.items.pop(iid, None)
            p = parent if it[0] == "dir" else it[1]
            while p is not None:
                p.size -= delta
                p.files -= dfiles
                piid = self.node_iid.get(id(p))
                if piid and self.tree.exists(piid):
                    pp = p.parent.size if p.parent else p.size
                    self.tree.item(piid, values=self._dir_values(p, pp), tags=self._dir_tags(p))
                p = p.parent
        elif self.result and not s["is_dir"]:
            # Archivo aún no cargado en el árbol: solo actualizar totales
            p = self._find_node(os.path.dirname(path))
            if p:
                for rec in list(p.top_files):
                    if rec[1] == os.path.basename(path):
                        p.top_files.remove(rec)
                        break
                while p is not None:
                    p.size -= s["size"]
                    p.files -= 1
                    piid = self.node_iid.get(id(p))
                    if piid and self.tree.exists(piid):
                        pp = p.parent.size if p.parent else p.size
                        self.tree.item(piid, values=self._dir_values(p, pp), tags=self._dir_tags(p))
                    p = p.parent

    def _find_node(self, path: str) -> scanner.DirNode | None:
        root = self.result.root
        try:
            rel = os.path.relpath(path, root.path)
        except ValueError:   # otra unidad
            return None
        if rel.startswith(".."):
            return None
        node = root
        if rel == ".":
            return node
        for part in rel.split(os.sep):
            node = next((c for c in node.children if c.name == part), None)
            if node is None:
                return None
        return node


def _system_mark(path: str) -> tuple[str, str, str]:
    """(etiqueta, etiqueta de color, qué es) de una ruta para las tablas.

    La etiqueta y el color solo se dan a lo que es del propio sistema y cuyo borrado daña a
    Windows; lo demás (programas instalados, datos de programas, archivos personales) no se
    destaca, aunque «qué es» sí lo describa cuando merece cuidado."""
    a = criticality.assess_path(path, strict=False)
    if a.system and a.level >= criticality.Level.IMPORTANT:
        return f"{WARN_MARK} {a.label}", f"lvl{int(a.level)}", a.what
    return "", "", a.what if a.level >= criticality.Level.CAUTION else ""
