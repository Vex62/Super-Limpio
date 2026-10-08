"""Widgets reutilizables y ejecución en segundo plano."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
import traceback
from tkinter import ttk
from typing import Any, Callable

from . import theme


# =========================================================================
# Tareas en segundo plano (la interfaz nunca se congela)
# =========================================================================

class Background:
    """Ejecuta funciones en hilos y entrega resultados en el hilo de la interfaz."""

    def __init__(self, root: tk.Misc, poll_ms: int = 60):
        self.root = root
        self.q: "queue.Queue[tuple[Callable, tuple]]" = queue.Queue()
        self.poll_ms = poll_ms
        self._poll()

    def _poll(self) -> None:
        try:
            while True:
                cb, args = self.q.get_nowait()
                try:
                    cb(*args)
                except Exception:  # noqa: BLE001 - nunca romper el bucle de la UI
                    traceback.print_exc()
        except queue.Empty:
            pass
        self.root.after(self.poll_ms, self._poll)

    def call_in_ui(self, cb: Callable, *args) -> None:
        self.q.put((cb, args))

    def run(self, fn: Callable[..., Any], *args,
            on_done: Callable[[Any], None] | None = None,
            on_error: Callable[[BaseException], None] | None = None) -> threading.Thread:
        def worker():
            try:
                result = fn(*args)
            except BaseException as exc:  # noqa: BLE001
                traceback.print_exc()
                if on_error:
                    self.q.put((on_error, (exc,)))
                return
            if on_done:
                self.q.put((on_done, (result,)))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t


# =========================================================================
# Elementos visuales
# =========================================================================

class Card(tk.Frame):
    def __init__(self, master, sf: float = 1.0, padding: int = 16, **kw):
        super().__init__(master, bg=theme.CARD, highlightthickness=1,
                         highlightbackground=theme.BORDER, highlightcolor=theme.BORDER, **kw)
        self.inner = tk.Frame(self, bg=theme.CARD)
        p = int(padding * sf)
        self.inner.pack(fill="both", expand=True, padx=p, pady=p)


class UsageBar(tk.Canvas):
    """Barra de ocupación con color según el nivel (verde/ámbar/rojo)."""

    def __init__(self, master, sf: float = 1.0, height: int = 10, bg: str = theme.CARD, **kw):
        super().__init__(master, height=int(height * sf), bg=bg, highlightthickness=0, **kw)
        self._frac = 0.0
        self.bind("<Configure>", lambda e: self._draw())

    def set(self, frac: float) -> None:
        self._frac = max(0.0, min(1.0, frac))
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            return
        self.create_rectangle(0, 0, w, h, fill="#e6e9ef", width=0)
        color = theme.ACCENT if self._frac < 0.75 else (theme.WARN if self._frac < 0.9 else theme.DANGER)
        if self._frac > 0:
            self.create_rectangle(0, 0, max(2, int(w * self._frac)), h, fill=color, width=0)


def badge(master, text: str, fg: str, bg: str, font) -> tk.Label:
    return tk.Label(master, text=f" {text} ", fg=fg, bg=bg, font=font, padx=4, pady=1)


def risk_badge(master, risk, font) -> tk.Label:
    fg, bg = theme.RISK_COLORS[risk]
    return badge(master, f"Riesgo {risk.label.lower()}", fg, bg, font)


class ScrollTree(ttk.Frame):
    """Treeview con barras de desplazamiento."""

    def __init__(self, master, columns: list[tuple[str, str, int, str]], show_tree: bool = False,
                 sf: float = 1.0, tree_heading: str = "Nombre", tree_width: int = 320,
                 selectmode: str = "extended", style_frame: str = "TFrame"):
        super().__init__(master, style=style_frame)
        cols = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=cols, show=("tree headings" if show_tree else "headings"),
                                 selectmode=selectmode)
        if show_tree:
            self.tree.heading("#0", text=tree_heading, anchor="w")
            self.tree.column("#0", width=int(tree_width * sf), minwidth=int(120 * sf), stretch=True)
        for cid, text, width, anchor in columns:
            self.tree.heading(cid, text=text, anchor=anchor)
            self.tree.column(cid, width=int(width * sf), minwidth=int(40 * sf), anchor=anchor,
                             stretch=(cid in ("hint", "path", "name", "command", "objetivo", "resultado",
                                              "project", "folder", "desc")))
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        theme.configure_size_tags(self.tree)


class SortableTable:
    """Mantiene filas (dict) y repinta la tabla ordenando al pulsar cabeceras."""

    def __init__(self, tree: ttk.Treeview, render: Callable[[dict], tuple],
                 sort_keys: dict[str, Callable[[dict], Any]], default_sort: str, descending: bool = True,
                 tag_fn: Callable[[dict], tuple] | None = None, key_fn: Callable[[dict], str] | None = None):
        self.tree = tree
        self.render = render
        self.sort_keys = sort_keys
        self.sort_col = default_sort
        self.desc = descending
        self.tag_fn = tag_fn
        self.key_fn = key_fn
        self.rows: list[dict] = []
        self.visible: dict[str, dict] = {}
        self._iids: dict[str, str] = {}   # clave de fila -> iid (solo con key_fn)
        self.filter_fn: Callable[[dict], bool] | None = None
        self._labels = {c: tree.heading(c, "text") for c in sort_keys}
        for col in sort_keys:
            tree.heading(col, command=lambda c=col: self.sort_by(c))
        self._update_heading_marks()

    def _update_heading_marks(self) -> None:
        for col, label in self._labels.items():
            mark = (" ▼" if self.desc else " ▲") if col == self.sort_col else ""
            self.tree.heading(col, text=label + mark)

    def sort_by(self, col: str) -> None:
        if col == self.sort_col:
            self.desc = not self.desc
        else:
            self.sort_col = col
            self.desc = col not in ("name", "publisher", "path", "kind", "project", "location", "folder")
        self._update_heading_marks()
        self.refresh()

    def set_rows(self, rows: list[dict]) -> None:
        self.rows = rows
        self.refresh()

    def refresh(self) -> None:
        keyf = self.sort_keys[self.sort_col]
        rows = [r for r in self.rows if not self.filter_fn or self.filter_fn(r)]
        try:
            rows.sort(key=keyf, reverse=self.desc)
        except TypeError:
            pass
        if self.key_fn:
            self._refresh_in_place(rows)
            return
        sel_keys = {self._key(self.visible[i]) for i in self.tree.selection() if i in self.visible}
        yview = self.tree.yview()
        self.tree.delete(*self.tree.get_children())
        self.visible.clear()
        reselect = []
        for r in rows:
            tags = self.tag_fn(r) if self.tag_fn else ()
            iid = self.tree.insert("", "end", values=self.render(r), tags=tags)
            self.visible[iid] = r
            if sel_keys and self._key(r) in sel_keys:
                reselect.append(iid)
        if reselect:
            self.tree.selection_set(reselect)
        if yview:
            self.tree.yview_moveto(yview[0])

    def _refresh_in_place(self, rows: list) -> None:
        """Actualiza las filas existentes en vez de vaciar y rellenar la tabla: no hay
        parpadeo y la selección y el desplazamiento se conservan solos."""
        tree = self.tree
        old = self._iids
        new: dict[str, str] = {}
        visible: dict[str, dict] = {}
        order: list[str] = []
        for r in rows:
            key = self.key_fn(r)
            if key in new:  # clave repetida: se distingue para no pisar la fila anterior
                key = f"{key}\0{len(new)}"
            tags = self.tag_fn(r) if self.tag_fn else ()
            iid = old.get(key)
            if iid is None:
                iid = tree.insert("", "end", values=self.render(r), tags=tags)
            else:
                tree.item(iid, values=self.render(r), tags=tags)
            new[key] = iid
            visible[iid] = r
            order.append(iid)
        gone = [iid for key, iid in old.items() if key not in new]
        if gone:
            tree.delete(*gone)
        if list(tree.get_children()) != order:
            tree.set_children("", *order)
        self._iids = new
        self.visible = visible

    def _key(self, r: dict) -> str:
        return self.key_fn(r) if self.key_fn else str(id(r))

    def selected(self) -> list[dict]:
        return [self.visible[i] for i in self.tree.selection() if i in self.visible]


def make_icons(root: tk.Misc, sf: float) -> dict[str, tk.PhotoImage]:
    """Iconos de carpeta/archivo dibujados en código (sin archivos binarios)."""
    s = 16 if sf < 1.4 else 24
    k = s / 16

    def rect(img, color, x1, y1, x2, y2):
        img.put(color, to=(int(x1 * k), int(y1 * k), max(int(x1 * k) + 1, int(x2 * k)),
                           max(int(y1 * k) + 1, int(y2 * k))))

    folder = tk.PhotoImage(master=root, width=s, height=s)
    rect(folder, "#d9a520", 1, 3, 7, 5)        # pestaña
    rect(folder, "#d9a520", 1, 4, 15, 14)      # trasera
    rect(folder, "#f7c843", 1, 6, 15, 14)      # frontal
    rect(folder, "#ffd968", 2, 7, 14, 8)       # brillo

    file_ = tk.PhotoImage(master=root, width=s, height=s)
    rect(file_, "#9aa3b2", 3, 1, 13, 15)
    rect(file_, "#ffffff", 4, 2, 12, 14)
    for y in (5, 7, 9, 11):
        rect(file_, "#c3c9d4", 5, y, 11, y + 1)

    group = tk.PhotoImage(master=root, width=s, height=s)
    rect(group, "#9aa3b2", 5, 1, 14, 12)
    rect(group, "#f4f6f9", 6, 2, 13, 11)
    rect(group, "#9aa3b2", 2, 4, 11, 15)
    rect(group, "#ffffff", 3, 5, 10, 14)

    drive = tk.PhotoImage(master=root, width=s, height=s)
    rect(drive, "#5b6578", 1, 5, 15, 12)
    rect(drive, "#8a95a8", 2, 6, 14, 11)
    rect(drive, theme.ACCENT, 11, 8, 13, 9)

    app = tk.PhotoImage(master=root, width=32, height=32)
    for y in range(32):
        for x in range(32):
            dx, dy = x - 15.5, y - 15.5
            d = (dx * dx + dy * dy) ** 0.5
            if d <= 15:
                app.put(theme.ACCENT if d < 13.5 else theme.ACCENT_DARK, to=(x, y))
    # destello blanco
    for x1, y1, x2, y2 in ((15, 7, 17, 25), (7, 15, 25, 17), (12, 12, 20, 20)):
        app.put("#ffffff", to=(x1, y1, x2, y2))
    return {"folder": folder, "file": file_, "group": group, "drive": drive, "app": app}
