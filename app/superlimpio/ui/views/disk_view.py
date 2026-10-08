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

from ... import fileops, scanner, winapi
from ...safety import Risk
from ...util import fmt_count, fmt_date, fmt_pct, fmt_size, text_bar
from .. import dialogs, theme
from ..widgets import ScrollTree, SortableTable
from .base import View

DUMMY = "__dummy__"
PAGE = 400   # filas que se añaden de una vez al desplegar una carpeta


class DiskView(View):
    title = "Analizador de disco"
    subtitle = "Cuánto pesa realmente cada carpeta, ordenado de mayor a menor."
    icon = "drive"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.result: scanner.ScanResult | None = None
        self.cancel_ev: threading.Event | None = None
        self.items: dict[str, tuple] = {}   # iid -> ("dir", node) | ("file", node, rec) | ("rest", node)
        self.node_iid: dict[int, str] = {}  # id(node) -> iid

        # ---- barra de direcciones (estilo Explorador)
        bar = self.toolbar()
        drives = winapi.list_drives()
        self.path_var = tk.StringVar(value=drives[0] if drives else os.path.expanduser("~"))
        ttk.Label(bar, text="Ubicación").pack(side="left", padx=(0, self.px(6)))
        self.drive_cb = ttk.Combobox(bar, values=drives, width=6, state="readonly")
        if drives:
            self.drive_cb.set(drives[0])
        self.drive_cb.bind("<<ComboboxSelected>>", lambda e: self.path_var.set(self.drive_cb.get()))
        self.drive_cb.pack(side="left")
        ent = ttk.Entry(bar, textvariable=self.path_var)
        ent.pack(side="left", fill="x", expand=True, padx=self.px(6))
        ent.bind("<Return>", lambda e: self.start_scan(self.path_var.get()))
        ttk.Button(bar, text="Examinar…", command=self._browse).pack(side="left")
        self.scan_btn = ttk.Button(bar, text="Analizar", style="Accent.TButton",
                                   command=lambda: self.start_scan(self.path_var.get()))
        self.scan_btn.pack(side="left", padx=(self.px(6), 0))
        self.cancel_btn = ttk.Button(bar, text="Detener", command=self._cancel)
        self.cancel_btn.pack(side="left", padx=(self.px(6), 0))
        self.cancel_btn.state(["disabled"])

        prog = ttk.Frame(self)
        prog.pack(fill="x", pady=(0, self.px(8)))
        self.pbar = ttk.Progressbar(prog, mode="indeterminate", length=self.px(160))
        self.pbar.pack(side="left")
        self.prog_lbl = ttk.Label(prog, text="Elige una unidad o carpeta y pulsa Analizar.", style="Muted.TLabel")
        self.prog_lbl.pack(side="left", padx=self.px(10), fill="x", expand=True)
        legend = tk.Frame(prog, bg=theme.BG)
        legend.pack(side="right")
        for color, txt in ((theme.ROW_MID, "≥100 MB"), (theme.ROW_BIG, "≥1 GB"), (theme.ROW_HUGE, "≥10 GB")):
            tk.Label(legend, text="   ", bg=color, highlightthickness=1,
                     highlightbackground=theme.BORDER).pack(side="left", padx=(self.px(8), 3))
            tk.Label(legend, text=txt, bg=theme.BG, fg=theme.MUTED, font=self.fonts.small).pack(side="left")

        # ---- pestañas
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        cols = [("size", "Tamaño", 95, "e"), ("bar", "Uso", 120, "w"), ("pct", "%", 60, "e"),
                ("files", "Archivos", 85, "e"), ("mtime", "Modificado", 125, "w"),
                ("hint", "Qué es", 300, "w")]
        self.tree_box = ScrollTree(self.nb, cols, show_tree=True, sf=self.sf, tree_heading="Nombre",
                                   tree_width=340)
        self.tree = self.tree_box.tree
        self.nb.add(self.tree_box, text="  Carpetas  ")
        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Button-3>", self._context_menu)
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Delete>", lambda e: self._recycle())

        fcols = [("name", "Archivo", 260, "w"), ("size", "Tamaño", 95, "e"), ("type", "Tipo", 150, "w"),
                 ("mtime", "Modificado", 125, "w"), ("folder", "Carpeta", 420, "w")]
        self.files_box = ScrollTree(self.nb, fcols, sf=self.sf)
        self.files_tbl = SortableTable(
            self.files_box.tree,
            render=lambda r: (r["name"], fmt_size(r["size"]), r["type"], fmt_date(r["mtime"]), r["folder"]),
            sort_keys={"name": lambda r: r["name"].lower(), "size": lambda r: r["size"],
                       "mtime": lambda r: r["mtime"], "folder": lambda r: r["folder"].lower(),
                       "type": lambda r: r["type"]},
            default_sort="size", tag_fn=lambda r: (theme.size_tag(r["size"]),), key_fn=lambda r: r["path"])
        self.nb.add(self.files_box, text="  Archivos más grandes  ")
        self.files_box.tree.bind("<Button-3>", self._context_menu)
        self.files_box.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.files_box.tree.bind("<Delete>", lambda e: self._recycle())

        tcols = [("ext", "Tipo", 160, "w"), ("size", "Tamaño", 100, "e"), ("bar", "Uso", 140, "w"),
                 ("pct", "%", 70, "e"), ("count", "Archivos", 100, "e"), ("desc", "Descripción", 300, "w")]
        self.types_box = ScrollTree(self.nb, tcols, sf=self.sf, selectmode="browse")
        self.types_tbl = SortableTable(
            self.types_box.tree,
            render=lambda r: (r["ext"], fmt_size(r["size"]), text_bar(r["size"], r["total"], 14),
                              fmt_pct(r["size"], r["total"]), fmt_count(r["count"]), r["desc"]),
            sort_keys={"ext": lambda r: r["ext"], "size": lambda r: r["size"], "count": lambda r: r["count"]},
            default_sort="size")
        self.nb.add(self.types_box, text="  Por tipo de archivo  ")

        # ---- panel de detalles / acciones
        det = tk.Frame(self, bg=theme.CARD, highlightthickness=1, highlightbackground=theme.BORDER)
        det.pack(fill="x", pady=(self.px(8), 0))
        inner = tk.Frame(det, bg=theme.CARD)
        inner.pack(fill="x", padx=self.px(12), pady=self.px(8))
        self.sel_name = tk.Label(inner, text="Nada seleccionado", font=self.fonts.bold, bg=theme.CARD,
                                 fg=theme.TEXT, anchor="w")
        self.sel_name.pack(side="left")
        self.sel_info = tk.Label(inner, text="", font=self.fonts.small, bg=theme.CARD, fg=theme.MUTED,
                                 anchor="w")
        self.sel_info.pack(side="left", padx=self.px(10), fill="x", expand=True)
        self.btn_del = ttk.Button(inner, text="Eliminar definitivamente…", style="Danger.TButton",
                                  command=self._delete_perm)
        self.btn_del.pack(side="right")
        self.btn_rec = ttk.Button(inner, text="Enviar a la Papelera…", command=self._recycle)
        self.btn_rec.pack(side="right", padx=self.px(6))
        self.btn_scan_here = ttk.Button(inner, text="Analizar aquí", command=self._scan_here)
        self.btn_scan_here.pack(side="right")
        self.btn_open = ttk.Button(inner, text="Abrir en Explorador", command=self._open)
        self.btn_open.pack(side="right", padx=self.px(6))
        self._set_actions(False)

        self.menu = tk.Menu(self, tearoff=False)
        self.menu.add_command(label="Abrir en el Explorador", command=self._open)
        self.menu.add_command(label="Copiar ruta", command=self._copy_path)
        self.menu.add_command(label="Analizar esta carpeta", command=self._scan_here)
        self.menu.add_separator()
        self.menu.add_command(label="Enviar a la Papelera…", command=self._recycle)
        self.menu.add_command(label="Eliminar definitivamente…", command=self._delete_perm)

    # ================================================================ escaneo
    def _browse(self) -> None:
        d = filedialog.askdirectory(parent=self, initialdir=self.path_var.get() or None,
                                    title="Carpeta a analizar")
        if d:
            self.path_var.set(os.path.normpath(d))

    def start_scan(self, path: str) -> None:
        path = (path or "").strip().strip('"')
        if not path or not os.path.isdir(path):
            dialogs.error(self, "Ruta no válida", f"No existe la carpeta:\n{path}")
            return
        if self.cancel_ev:
            self.cancel_ev.set()
        self.path_var.set(path)
        self.cancel_ev = threading.Event()
        self.scan_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.pbar.start(12)
        self.prog_lbl.configure(text=f"Analizando {path} …")
        self.status(f"Analizando {path}")
        ev = self.cancel_ev

        def progress(p: scanner.ScanProgress):
            txt = (f"{fmt_count(p.files)} archivos · {fmt_count(p.dirs)} carpetas · {fmt_size(p.bytes)} · "
                   f"{p.elapsed:.0f} s   {p.current[-90:]}")
            self.app.bg.call_in_ui(self.prog_lbl.configure, {"text": txt})

        self.app.bg.run(lambda: scanner.scan(path, progress, ev),
                        on_done=self._scan_done, on_error=self._scan_failed)

    def _cancel(self) -> None:
        if self.cancel_ev:
            self.cancel_ev.set()
            self.prog_lbl.configure(text="Deteniendo…")

    def _scan_failed(self, exc: BaseException) -> None:
        self._end_progress()
        dialogs.error(self, "Error al analizar", str(exc))

    def _end_progress(self) -> None:
        self.pbar.stop()
        self.scan_btn.state(["!disabled"])
        self.cancel_btn.state(["disabled"])

    def _scan_done(self, res: scanner.ScanResult) -> None:
        self._end_progress()
        self.result = res
        extra = []
        if res.cancelled:
            extra.append("análisis detenido: resultados parciales")
        if res.errors:
            extra.append(f"{fmt_count(res.errors)} elementos sin permiso de lectura"
                         + ("" if self.app.is_admin else " (prueba como administrador)"))
        if res.cloud_size:
            extra.append(f"{fmt_size(res.cloud_size)} solo en la nube (no ocupan disco)")
        if res.skipped_links:
            extra.append(f"{fmt_count(res.skipped_links)} enlaces/junctions no seguidos")
        self.prog_lbl.configure(
            text=f"{fmt_size(res.root.size)} en {fmt_count(res.root.files)} archivos y "
                 f"{fmt_count(res.root.dirs)} carpetas · {res.elapsed:.1f} s"
                 + ("   ·   " + " · ".join(extra) if extra else ""))
        self.status(f"Análisis completado: {res.root.path}")
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
        hint = scanner.hint_for(node.name, True)
        if node.errors and not hint:
            hint = "Algunas subcarpetas no se pudieron leer"
        if node.cloud_size and not hint:
            hint = f"+{fmt_size(node.cloud_size)} solo en la nube"
        return (fmt_size(node.size), text_bar(node.size, parent_size), fmt_pct(node.size, parent_size),
                fmt_count(node.files), fmt_date(node.mtime), hint)

    def _insert_dir(self, parent: str, node: scanner.DirNode, parent_size: int, index="end") -> str:
        iid = self.tree.insert(parent, index, text=f" {node.name}", image=self.app.icons["folder"],
                               values=self._dir_values(node, parent_size),
                               tags=(theme.size_tag(node.size), "bar"))
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

    def _insert_page(self, iid: str, node: scanner.DirNode, entries: list) -> None:
        """Inserta las PAGE filas siguientes. Las carpetas con miles de elementos (WinSxS,
        node_modules…) se cargan por tramos para que la ventana no se quede parada."""
        for _size, kind, obj in entries[:PAGE]:
            if kind == "dir":
                self._insert_dir(iid, obj, node.size)
            elif obj in node.top_files:  # puede haberse borrado desde «Archivos más grandes»
                fsize, fname, fmtime = obj
                fid = self.tree.insert(iid, "end", text=f" {fname}", image=self.app.icons["file"],
                                       values=(fmt_size(fsize), text_bar(fsize, node.size),
                                               fmt_pct(fsize, node.size), "", fmt_date(fmtime),
                                               scanner.hint_for(fname, False)),
                                       tags=(theme.size_tag(fsize), "bar"))
                self.items[fid] = ("file", node, obj)
        rest = entries[PAGE:]
        if rest:
            left = sum(e[0] for e in rest)
            mid = self.tree.insert(iid, "end", text=f" Mostrar más ({fmt_count(len(rest))} restantes)…",
                                   image=self.app.icons["group"],
                                   values=(fmt_size(left), text_bar(left, node.size), fmt_pct(left, node.size),
                                           "", "", "Pulsa aquí para cargar los siguientes"),
                                   tags=("muted", "bar"))
            self.items[mid] = ("more", node, rest)
            return
        if node.small_files_count:
            rid = self.tree.insert(iid, "end", text=f" ({fmt_count(node.small_files_count)} archivos pequeños)",
                                   image=self.app.icons["group"],
                                   values=(fmt_size(node.small_files_size),
                                           text_bar(node.small_files_size, node.size),
                                           fmt_pct(node.small_files_size, node.size),
                                           fmt_count(node.small_files_count), "", "Agrupados para ahorrar memoria"),
                                   tags=("muted", "bar"))
            self.items[rid] = ("rest", node)

    def _on_open(self, _e=None) -> None:
        iid = self.tree.focus()
        if iid in self.items and self.items[iid][0] == "dir":
            self._populate(iid)

    def _on_double(self, e) -> None:
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
                         "path": path, "type": scanner.EXT_HINTS.get(ext, ext.lstrip(".").upper() or "Archivo")})
        self.files_tbl.set_rows(rows)

    def _fill_types(self) -> None:
        total = sum(v[0] for v in self.result.by_extension.values()) or 1
        rows = [{"ext": ext, "size": v[0], "count": v[1], "total": total, "desc": scanner.EXT_HINTS.get(ext, "")}
                for ext, v in self.result.by_extension.items()]
        rows.sort(key=lambda r: r["size"], reverse=True)
        self.types_tbl.set_rows(rows[:400])

    # ========================================================== selección
    def _active_tree(self) -> ttk.Treeview:
        return self.files_box.tree if self.nb.index(self.nb.select()) == 1 else self.tree

    def _selected(self) -> list[dict]:
        """Elementos seleccionados como {path, size, is_dir, ref}."""
        out = []
        tree = self._active_tree()
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

    def _on_select(self, _e=None) -> None:
        picked = self.tree.selection()
        if len(picked) == 1 and self.items.get(picked[0], ("",))[0] == "more":
            self._load_more(picked[0])
            return
        sel = self._selected()
        if not sel:
            self.sel_name.configure(text="Nada seleccionado")
            self.sel_info.configure(text="")
            self._set_actions(False)
            return
        if len(sel) == 1:
            s = sel[0]
            self.sel_name.configure(text=f"{os.path.basename(s['path'].rstrip(os.sep)) or s['path']}  ·  "
                                         f"{fmt_size(s['size'])}")
            self.sel_info.configure(text=s["path"])
        else:
            total = sum(s["size"] for s in sel)
            self.sel_name.configure(text=f"{len(sel)} elementos  ·  {fmt_size(total)}")
            self.sel_info.configure(text="")
        self._set_actions(True, single_dir=len(sel) == 1 and sel[0]["is_dir"])

    def _set_actions(self, on: bool, single_dir: bool = False) -> None:
        for b in (self.btn_del, self.btn_rec, self.btn_open):
            b.state(["!disabled"] if on else ["disabled"])
        self.btn_scan_here.state(["!disabled"] if single_dir else ["disabled"])

    def _context_menu(self, e) -> None:
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
            ok, msg = winapi.open_in_explorer(sel[0]["path"])
            if not ok:
                self.status(msg)

    def _copy_path(self) -> None:
        sel = self._selected()
        if sel:
            self.clipboard_clear()
            self.clipboard_append("\n".join(s["path"] for s in sel))
            self.status("Ruta copiada al portapapeles")

    def _scan_here(self) -> None:
        sel = self._selected()
        if sel and sel[0]["is_dir"]:
            self.start_scan(sel[0]["path"])

    def _check_blocked(self, sel: list[dict]) -> bool:
        _ok, blocked = fileops.validate([s["path"] for s in sel])
        if blocked:
            dialogs.error(self, "Protegido", "Super Limpio no permite borrar esto:\n\n" +
                          "\n".join(f"• {p}\n   {r}" for p, r in blocked[:10]))
            return True
        return False

    def _recycle(self) -> None:
        sel = self._selected()
        if not sel or self._check_blocked(sel):
            return
        total = sum(s["size"] for s in sel)
        if not dialogs.confirm(
                self, "Enviar a la Papelera",
                f"Se moverán {len(sel)} elementos ({fmt_size(total)}) a la Papelera de reciclaje. "
                "Podrás restaurarlos desde la Papelera mientras no la vacíes.\n"
                "Si la unidad no tiene Papelera (p. ej. algunos discos externos), Windows te avisará antes.",
                dialogs.summarize_paths([s["path"] for s in sel], [s["size"] for s in sel]),
                risk=Risk.MEDIO, ok_text="Enviar a la Papelera"):
            return
        self._do_delete(sel, fileops.recycle)

    def _delete_perm(self) -> None:
        sel = self._selected()
        if not sel or self._check_blocked(sel):
            return
        total = sum(s["size"] for s in sel)
        if not dialogs.confirm(
                self, "Eliminar definitivamente",
                f"Se borrarán PARA SIEMPRE {len(sel)} elementos ({fmt_size(total)}), sin pasar por la Papelera. "
                "No se podrán recuperar.",
                dialogs.summarize_paths([s["path"] for s in sel], [s["size"] for s in sel]),
                risk=Risk.CRITICO, ok_text="Eliminar para siempre"):
            return
        self._do_delete(sel, fileops.delete_permanently)

    def _do_delete(self, sel: list[dict], fn) -> None:
        self.status("Eliminando…")
        self.app.bg.run(lambda: fn([s["path"] for s in sel]),
                        on_done=lambda r: self._after_delete(sel, r))

    def _after_delete(self, sel: list[dict], res: tuple[bool, str]) -> None:
        ok, msg = res
        removed = [s for s in sel if not os.path.exists(s["path"])]
        for s in removed:
            self._remove_from_model(s)
        freed = sum(s["size"] for s in removed)
        self.status(f"{msg} · {fmt_size(freed)} liberados ({len(removed)}/{len(sel)})")
        if not ok:
            dialogs.error(self, "Resultado", msg)
        self._on_select()

    def _remove_from_model(self, s: dict) -> None:
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
                    self.tree.item(piid, values=self._dir_values(p, pp), tags=(theme.size_tag(p.size), "bar"))
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
                        self.tree.item(piid, values=self._dir_values(p, pp))
                    p = p.parent

    def _find_node(self, path: str) -> scanner.DirNode | None:
        root = self.result.root
        rel = os.path.relpath(path, root.path)
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
