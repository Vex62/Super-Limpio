"""Widgets reutilizables y ejecución en segundo plano."""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import traceback
from tkinter import ttk
from typing import Any, Callable

from .. import i18n
from . import theme

# Icono y logo generados por tools/crear_exe.py a partir de launcher/logo.png
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# =========================================================================
# Tareas en segundo plano (la interfaz nunca se congela)
# =========================================================================

class Background:
    """Ejecuta funciones en hilos y entrega resultados en el hilo de la interfaz."""

    def __init__(self, root: tk.Misc, poll_ms: int = 60):
        self.root = root
        self.q: "queue.Queue[tuple[int, Callable, tuple]]" = queue.Queue()
        self.poll_ms = poll_ms
        self._gen = 0
        self._local = threading.local()
        self._poll()

    def reset(self) -> None:
        """Descarta lo pendiente: se llama al reconstruir la interfaz, para que el resultado
        de una tarea antigua no llegue a ventanas que ya no existen."""
        self._gen += 1

    def _poll(self) -> None:
        try:
            while True:
                gen, cb, args = self.q.get_nowait()
                if gen != self._gen:
                    continue
                try:
                    cb(*args)
                except Exception:  # noqa: BLE001 - nunca romper el bucle de la UI
                    _log_error(traceback.format_exc())
        except queue.Empty:
            pass
        self.root.after(self.poll_ms, self._poll)

    def call_in_ui(self, cb: Callable, *args) -> None:
        self.q.put((getattr(self._local, "gen", self._gen), cb, args))

    def run(self, fn: Callable[..., Any], *args,
            on_done: Callable[[Any], None] | None = None,
            on_error: Callable[[BaseException], None] | None = None) -> threading.Thread:
        gen = self._gen

        def worker():
            self._local.gen = gen
            try:
                result = fn(*args)
            except BaseException as exc:  # noqa: BLE001
                _log_error(traceback.format_exc())
                if on_error:
                    self.q.put((gen, on_error, (exc,)))
                return
            if on_done:
                self.q.put((gen, on_done, (result,)))

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t


def _log_error(text: str) -> None:
    """Un fallo en segundo plano no se enseña en un diálogo, pero sí queda en el registro."""
    from ..safety import log_action
    log_action("error_interno", "", text[-1500:], ok=False)
    try:
        print(text)
    except Exception:  # noqa: BLE001 - con pythonw no hay consola
        pass


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
        self.create_rectangle(0, 0, w, h, fill="#e1e9e3", width=0)
        color = theme.ACCENT if self._frac < 0.75 else (theme.WARN if self._frac < 0.9 else theme.DANGER)
        if self._frac > 0:
            self.create_rectangle(0, 0, max(2, int(w * self._frac)), h, fill=color, width=0)


def badge(master, text: str, fg: str, bg: str, font) -> tk.Label:
    return tk.Label(master, text=f" {text} ", fg=fg, bg=bg, font=font, padx=4, pady=1)


def risk_badge(master, risk, font) -> tk.Label:
    fg, bg = theme.RISK_COLORS[risk]
    label = risk.label.lower() if i18n.current() == "es" else risk.label
    return badge(master, i18n.t("risk.badge", label=label), fg, bg, font)


class ZoomStepper(tk.Frame):
    """Control «−  100 %  +» de la barra lateral, con los colores de la marca.

    Los dos botones son segmentos del mismo marco; el porcentaje del centro también se
    puede pulsar y devuelve la interfaz al 100 %. En el límite, el botón se apaga."""

    def __init__(self, master, fonts: theme.Fonts, sf: float, value: float, lo: float, hi: float,
                 on_step: Callable[[int], None], on_reset: Callable[[], None],
                 on_hover: Callable[[bool], None] | None = None):
        super().__init__(master, bg=theme.ZOOM_BORDER)
        self._hover_cb = on_hover
        line = max(1, round(sf))
        pady = int(5 * sf)
        self.columnconfigure(1, weight=1)
        minus = self._segment("\u2212", fonts.h2, value > lo + 1e-6, lambda: on_step(-1), pady)
        minus.grid(row=0, column=0, sticky="nsew", padx=(line, 0), pady=line)
        self.readout = tk.Label(self, text=i18n.percent(str(round(value * 100))), font=fonts.bold,
                                bg=theme.SIDEBAR_BG, fg=theme.BLANCO, pady=pady)
        self.readout.grid(row=0, column=1, sticky="nsew", padx=line, pady=line)
        plus = self._segment("+", fonts.h2, value < hi - 1e-6, lambda: on_step(1), pady)
        plus.grid(row=0, column=2, sticky="nsew", padx=(0, line), pady=line)
        if abs(value - 1.0) > 1e-6:   # el centro solo actúa si hay algo que restablecer
            self.readout.configure(cursor="hand2")
            self.readout.bind("<Enter>", lambda e: self.readout.configure(fg=theme.AGUA), add="+")
            self.readout.bind("<Leave>", lambda e: self.readout.configure(fg=theme.BLANCO), add="+")
            self.readout.bind("<ButtonRelease-1>", lambda e: on_reset())
        for w in (minus, plus, self.readout):
            w.bind("<Enter>", lambda e: self._hover(True), add="+")
            w.bind("<Leave>", lambda e: self._hover(False), add="+")

    def _hover(self, inside: bool) -> None:
        if self._hover_cb:
            self._hover_cb(inside)

    def _segment(self, glyph: str, font, enabled: bool, command: Callable[[], None], pady: int) -> tk.Label:
        seg = tk.Label(self, text=glyph, font=font, width=3, pady=max(0, pady - 2),
                       bg=theme.ZOOM_BTN if enabled else theme.SIDEBAR_BG,
                       fg=theme.BLANCO if enabled else theme.ZOOM_OFF)
        if not enabled:
            return seg
        seg.configure(cursor="hand2")

        def paint(bg: str, fg: str = theme.BLANCO) -> None:
            seg.configure(bg=bg, fg=fg)

        def release(e) -> None:
            inside = 0 <= e.x < seg.winfo_width() and 0 <= e.y < seg.winfo_height()
            paint(theme.ZOOM_HOVER if inside else theme.ZOOM_BTN)
            if inside:
                command()

        seg.bind("<Enter>", lambda e: paint(theme.ZOOM_HOVER), add="+")
        seg.bind("<Leave>", lambda e: paint(theme.ZOOM_BTN), add="+")
        seg.bind("<ButtonPress-1>", lambda e: paint(theme.LIMA, theme.PETROLEO))
        seg.bind("<ButtonRelease-1>", release)
        return seg


_WHEEL_EVENTS = ("<MouseWheel>", "<Button-4>", "<Button-5>")


def bind_wheel(canvas: tk.Canvas) -> None:
    """Rueda del ratón para un Canvas con contenido desplazable. Funciona también con el
    puntero sobre los widgets que hay dentro, y se desengancha sola al salir o destruirse."""
    def on_wheel(ev) -> None:
        if canvas.winfo_exists() and canvas.yview() != (0.0, 1.0):
            # En Linux (X11) la rueda no llega como <MouseWheel> sino como los botones 4 y 5.
            step = -1 if ev.num == 4 else 1 if ev.num == 5 else int(-ev.delta / 120)
            canvas.yview_scroll(step, "units")

    def hook(_e=None) -> None:
        for seq in _WHEEL_EVENTS:
            canvas.bind_all(seq, on_wheel)

    def unhook() -> None:
        for seq in _WHEEL_EVENTS:
            canvas.unbind_all(seq)

    def pointer_inside() -> bool:
        try:
            w = canvas.winfo_containing(*canvas.winfo_pointerxy())
        except (tk.TclError, KeyError):
            return False
        return w is not None and (str(w) + ".").startswith(str(canvas) + ".")

    def leave(_e=None) -> None:
        if not pointer_inside():
            unhook()

    def destroyed(e) -> None:
        if e.widget is canvas:
            try:
                unhook()
            except tk.TclError:
                pass

    canvas.bind("<Enter>", hook, add="+")
    canvas.bind("<Leave>", leave, add="+")
    canvas.bind("<Destroy>", destroyed, add="+")


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

    try:
        app = tk.PhotoImage(master=root, file=os.path.join(ASSETS_DIR, f"logo-{40 if sf < 1.4 else 60}.png"))
        return {"folder": folder, "file": file_, "group": group, "drive": drive, "app": app}
    except tk.TclError:
        pass  # sin el logo: se dibuja uno sencillo
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
