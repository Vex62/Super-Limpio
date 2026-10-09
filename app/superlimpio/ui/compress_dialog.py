"""Ventana «Comprimir»: opciones al estilo de 7-Zip/WinRAR y progreso en curso.

La propia ventana es la autorización: no se crea nada hasta pulsar «Comprimir», los
originales solo se leen y, si se detiene o falla, no queda ningún archivo a medias.
"""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import archiver, i18n, winapi
from ..safety import log_action
from ..util import fmt_count, fmt_size
from . import theme


class CompressDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, app, paths: list[str]):
        super().__init__(parent)
        self.app, self.paths = app, paths
        self.fonts, self.sf = app.fonts, app.sf
        self.result: archiver.Result | None = None
        self.want_recycle = False           # el usuario pidió enviar los originales a la Papelera
        self.collection: archiver.Collection | None = None
        self.stop = threading.Event()
        self.running = False
        self._started = 0.0
        mem = winapi.memory_status()
        self._ram = (mem.total, mem.available) if mem else (0, 0)

        self.title(i18n.t("zip.title"))
        self.configure(bg=theme.CARD)
        self.resizable(True, False)
        self.transient(parent.winfo_toplevel())
        px = self._px
        pad = px(16)

        head = tk.Frame(self, bg=theme.ACCENT_SOFT)
        head.pack(fill="x")
        tk.Frame(head, bg=theme.ACCENT, width=px(6)).pack(side="left", fill="y")
        box = tk.Frame(head, bg=theme.ACCENT_SOFT)
        box.pack(side="left", fill="x", expand=True, padx=pad, pady=px(10))
        tk.Label(box, text=i18n.t("zip.title"), font=self.fonts.h2, bg=theme.ACCENT_SOFT, fg=theme.TEXT,
                 anchor="w").pack(fill="x")
        self.sel_lbl = tk.Label(box, text=i18n.t("zip.counting", n=len(paths)), font=self.fonts.small,
                                bg=theme.ACCENT_SOFT, fg=theme.ACCENT_DARK, anchor="w")
        self.sel_lbl.pack(fill="x")

        body = tk.Frame(self, bg=theme.CARD)
        body.pack(fill="both", expand=True, padx=pad, pady=(px(12), 0))
        body.columnconfigure(1, weight=1)
        self._inputs: list[tk.Widget] = []

        def label(row: int, key: str) -> None:
            tk.Label(body, text=i18n.t(key), font=self.fonts.base, bg=theme.CARD, fg=theme.TEXT,
                     anchor="w").grid(row=row, column=0, sticky="w", padx=(0, px(10)), pady=px(4))

        def note(row: int) -> tk.Label:
            lbl = tk.Label(body, text="", font=self.fonts.small, bg=theme.CARD, fg=theme.MUTED, anchor="w",
                           justify="left", wraplength=px(520))
            lbl.grid(row=row, column=1, columnspan=2, sticky="we", pady=(0, px(6)))
            return lbl

        # Destino
        label(0, "zip.dest")
        self.dest = tk.StringVar(value=archiver.default_dest(paths, "7z"))
        ent = ttk.Entry(body, textvariable=self.dest, width=58)
        ent.grid(row=0, column=1, sticky="we", pady=px(4))
        browse = ttk.Button(body, text=i18n.t("common.browse"), command=self._browse)
        browse.grid(row=0, column=2, padx=(px(8), 0))

        # Formato y nivel
        label(1, "zip.format")
        row = tk.Frame(body, bg=theme.CARD)
        row.grid(row=1, column=1, columnspan=2, sticky="w", pady=px(4))
        self._fmt_labels = [i18n.t(f"zip.fmt.{f}") for f in archiver.FORMATS]
        self.fmt = tk.StringVar(value=self._fmt_labels[0])
        fmt_cb = ttk.Combobox(row, values=self._fmt_labels, textvariable=self.fmt, state="readonly", width=30)
        fmt_cb.pack(side="left")
        fmt_cb.bind("<<ComboboxSelected>>", lambda e: self._on_format())
        tk.Label(row, text=i18n.t("zip.level"), font=self.fonts.base, bg=theme.CARD).pack(
            side="left", padx=(px(14), px(8)))
        self._level_labels = [i18n.t(f"zip.level.{lv}") for lv in archiver.LEVELS]
        self.level = tk.StringVar(value=self._level_labels[0])
        level_cb = ttk.Combobox(row, values=self._level_labels, textvariable=self.level, state="readonly", width=16)
        level_cb.pack(side="left")
        level_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_notes())
        self.fmt_note = note(2)

        # Contraseña
        label(3, "zip.password")
        row = tk.Frame(body, bg=theme.CARD)
        row.grid(row=3, column=1, columnspan=2, sticky="w", pady=px(4))
        self.pw1, self.pw2, self.show = tk.StringVar(), tk.StringVar(), tk.BooleanVar(value=False)
        self.pw1_ent = ttk.Entry(row, textvariable=self.pw1, show="•", width=22)
        self.pw1_ent.pack(side="left")
        tk.Label(row, text=i18n.t("zip.password_again"), font=self.fonts.base, bg=theme.CARD).pack(
            side="left", padx=(px(12), px(8)))
        self.pw2_ent = ttk.Entry(row, textvariable=self.pw2, show="•", width=22)
        self.pw2_ent.pack(side="left")
        show = tk.Checkbutton(row, text=i18n.t("zip.show"), variable=self.show, bg=theme.CARD,
                              activebackground=theme.CARD, font=self.fonts.base, command=self._toggle_show)
        show.pack(side="left", padx=(px(10), 0))
        self.pw_note = note(4)

        # Opciones
        self.verify = tk.BooleanVar(value=True)
        self.recycle = tk.BooleanVar(value=False)
        self.verify_chk = tk.Checkbutton(body, text=i18n.t("zip.opt.verify"), variable=self.verify, bg=theme.CARD,
                                         activebackground=theme.CARD, font=self.fonts.base, anchor="w")
        self.verify_chk.grid(row=5, column=1, columnspan=2, sticky="w")
        recycle_chk = tk.Checkbutton(body, text=i18n.t("zip.opt.recycle"), variable=self.recycle, bg=theme.CARD,
                                     activebackground=theme.CARD, font=self.fonts.base, anchor="w",
                                     command=self._on_recycle)
        recycle_chk.grid(row=6, column=1, columnspan=2, sticky="w")
        self._inputs += [ent, browse, fmt_cb, level_cb, self.pw1_ent, self.pw2_ent, show, self.verify_chk,
                         recycle_chk]

        # Progreso / resultado
        self.prog = tk.Frame(self, bg=theme.CARD)
        self.pbar = ttk.Progressbar(self.prog, mode="determinate", maximum=1000)
        self.pbar.pack(fill="x")
        self.prog_main = tk.Label(self.prog, text="", font=self.fonts.bold, bg=theme.CARD, fg=theme.TEXT,
                                  anchor="w")
        self.prog_main.pack(fill="x", pady=(px(6), 0))
        self.prog_detail = tk.Label(self.prog, text="", font=self.fonts.small, bg=theme.CARD, fg=theme.MUTED,
                                    anchor="w", justify="left", wraplength=px(640))
        self.prog_detail.pack(fill="x")

        btns = tk.Frame(self, bg=theme.CARD)
        btns.pack(side="bottom", fill="x", padx=pad, pady=pad)
        self.cancel_btn = ttk.Button(btns, text=i18n.t("common.cancel"), command=self._cancel)
        self.cancel_btn.pack(side="right")
        self.ok_btn = ttk.Button(btns, text=i18n.t("zip.go"), style="Accent.TButton", command=self._start)
        self.ok_btn.pack(side="right", padx=(0, px(8)))
        self.open_btn = ttk.Button(btns, text=i18n.t("common.open_location"), command=self._open_folder)
        tk.Label(btns, text=i18n.t("zip.read_only"), font=self.fonts.small, bg=theme.CARD,
                 fg=theme.MUTED).pack(side="left")

        for var in (self.dest, self.pw1, self.pw2):
            var.trace_add("write", lambda *_: self._validate())
        self.bind("<Escape>", lambda e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._refresh_notes()

        self.update_idletasks()
        top = parent.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - self.winfo_reqwidth()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - self.winfo_reqheight()) // 4
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.grab_set()
        ent.focus_set()

        app.bg.run(lambda: archiver.collect(paths, self.stop.is_set), on_done=self._collected,
                   on_error=lambda e: self._collected(None))

    # ----------------------------------------------------------------- utilidades
    def _px(self, n: float) -> int:
        return int(n * self.sf)

    def _format(self) -> str:
        return archiver.FORMATS[self._fmt_labels.index(self.fmt.get())]

    def _level(self) -> str:
        return archiver.LEVELS[self._level_labels.index(self.level.get())]

    def _alive(self) -> bool:
        try:
            return bool(self.winfo_exists())
        except tk.TclError:
            return False

    # ------------------------------------------------------------------- opciones
    def _collected(self, col) -> None:
        if not self._alive():
            return
        self.collection = col
        if col is None:
            self.sel_lbl.configure(text=i18n.t("zip.err.nothing"), fg=theme.DANGER)
            return
        text = i18n.t("zip.selection", files=fmt_count(col.files), dirs=fmt_count(col.dirs),
                      size=fmt_size(col.total))
        if col.skipped:
            text += i18n.t("zip.selection_skipped", n=fmt_count(len(col.skipped)))
        self.sel_lbl.configure(text=text)
        self._refresh_notes()

    def _browse(self) -> None:
        fmt = self._format()
        current = self.dest.get().strip()
        path = filedialog.asksaveasfilename(
            parent=self, title=i18n.t("zip.dest"), defaultextension=f".{fmt}", confirmoverwrite=False,
            initialdir=os.path.dirname(current) or None, initialfile=os.path.basename(current),
            filetypes=[(i18n.t(f"zip.fmt.{fmt}"), f"*.{fmt}")])
        if path:
            self.dest.set(os.path.normpath(path))

    def _on_format(self) -> None:
        fmt = self._format()
        stem, ext = os.path.splitext(self.dest.get().strip())
        if stem and ext.lower() in (".7z", ".zip"):
            self.dest.set(f"{stem}.{fmt}")
        self._refresh_notes()

    def _toggle_show(self) -> None:
        for ent in (self.pw1_ent, self.pw2_ent):
            ent.configure(show="" if self.show.get() else "•")

    def _on_recycle(self) -> None:
        if self.recycle.get():      # solo se tocan los originales si el archivo se ha comprobado
            self.verify.set(True)
            self.verify_chk.configure(state="disabled")
        else:
            self.verify_chk.configure(state="normal")

    def _refresh_notes(self) -> None:
        fmt, level = self._format(), self._level()
        text = i18n.t(f"zip.fmt.{fmt}.note")
        if fmt == "7z":
            total = self.collection.total if self.collection else 0
            how = archiver.plan(fmt, level, total or 1 << 40, *self._ram)
            text += "\n" + i18n.t("zip.plan", dict=fmt_size(how.dict_size), threads=how.threads,
                                  mem=fmt_size(how.memory))
        self.fmt_note.configure(text=text)
        self._validate()

    def _validate(self) -> bool:
        fmt = self._format()
        pw1, pw2 = self.pw1.get(), self.pw2.get()
        problem = ""
        if pw1 != pw2:
            problem = i18n.t("zip.pw.mismatch")
        elif pw1 and not archiver.password_ok(fmt, pw1):
            problem = i18n.t("zip.err.ascii_password")
        if problem:
            self.pw_note.configure(text=problem, fg=theme.DANGER)
        else:
            self.pw_note.configure(text=i18n.t(f"zip.pw.note.{fmt}" if pw1 else "zip.pw.none"), fg=theme.MUTED)
        ok = (not problem and not self.running and self.result is None and bool(self.dest.get().strip())
              and self.collection is not None and bool(self.collection.entries))
        self.ok_btn.state(["!disabled"] if ok else ["disabled"])
        return ok

    def _set_inputs(self, enabled: bool) -> None:
        for w in self._inputs:
            if isinstance(w, ttk.Combobox):
                w.configure(state="readonly" if enabled else "disabled")
            else:
                w.configure(state="normal" if enabled else "disabled")
        if enabled:
            self._on_recycle()

    # ------------------------------------------------------------------ ejecución
    def _start(self) -> None:
        if not self._validate():
            return
        fmt = self._format()
        dest = os.path.abspath(os.path.expandvars(self.dest.get().strip().strip('"')))
        if not dest.lower().endswith(f".{fmt}"):
            dest += f".{fmt}"
        if not os.path.isdir(os.path.dirname(dest)):
            self._fail(i18n.t("zip.err.no_folder", path=os.path.dirname(dest)))
            return
        if os.path.isdir(dest):
            self._fail(i18n.t("zip.err.no_folder", path=dest))
            return
        if os.path.exists(dest) and not messagebox.askyesno(
                i18n.t("zip.title"), i18n.t("zip.overwrite", path=dest), parent=self, default="no"):
            return
        self.dest.set(dest)
        opt = archiver.Options(dest, fmt, self._level(), self.pw1.get(), self.verify.get(), *self._ram)
        self.want_recycle = self.recycle.get()
        self.running, self._started = True, time.monotonic()
        self.stop.clear()
        self._set_inputs(False)
        self.ok_btn.state(["disabled"])
        self.cancel_btn.configure(text=i18n.t("common.stop"))
        self.prog.pack(fill="x", padx=self._px(16), pady=(self._px(12), 0))
        self.pbar.configure(value=0)
        self.prog_main.configure(text=i18n.t("zip.phase.start"), fg=theme.TEXT)
        self.prog_detail.configure(text=i18n.t("zip.phase.start_detail") if opt.password and fmt == "7z" else "")
        col = self.collection

        def progress(p: archiver.Progress) -> None:
            self.app.bg.call_in_ui(self._on_progress, p)

        self.app.bg.run(lambda: archiver.compress(col, opt, progress, self.stop.is_set),
                        on_done=lambda res: self._finished(opt, res, None),
                        on_error=lambda exc: self._finished(opt, None, exc))

    def _on_progress(self, p: archiver.Progress) -> None:
        if not self._alive() or not self.running:
            return
        frac = p.done / p.total if p.total else 1.0
        self.pbar.configure(value=int(frac * 1000))
        elapsed = time.monotonic() - self._started
        name = os.path.basename(p.current)
        if p.phase == "verify":
            self.prog_main.configure(text=i18n.t("zip.phase.verify", pct=f"{frac * 100:.0f}"))
            self.prog_detail.configure(text=i18n.t("zip.progress.verify", done=fmt_size(p.done),
                                                   total=fmt_size(p.total), elapsed=_duration(elapsed)))
            return
        self.prog_main.configure(text=i18n.t("zip.phase.compress", pct=f"{frac * 100:.0f}", name=name[-70:]))
        speed = p.done / elapsed if elapsed > 0.5 else 0
        ratio = f"{p.written / p.done * 100:.0f}" if p.done else "—"
        eta = _duration((p.total - p.done) / speed) if speed and p.done > p.total * 0.01 else "…"
        self.prog_detail.configure(text=i18n.t(
            "zip.progress.compress", done=fmt_size(p.done), total=fmt_size(p.total), out=fmt_size(p.written),
            ratio=ratio, speed=fmt_size(speed), elapsed=_duration(elapsed), eta=eta))

    def _finished(self, opt: archiver.Options, res, exc) -> None:
        self.running = False
        self.pw1.set("")
        self.pw2.set("")
        encrypted = bool(opt.password)
        opt.password = ""
        if isinstance(exc, archiver.Cancelled):
            log_action("comprimir", opt.dest, "cancelado", ok=False, formato=opt.fmt)
        elif exc is not None:
            log_action("comprimir", opt.dest, str(exc)[:300], ok=False, formato=opt.fmt)
        else:
            log_action("comprimir", opt.dest, "ok", formato=opt.fmt, nivel=opt.level, cifrado=encrypted,
                       archivos=res.files, original=res.in_bytes, final=res.out_bytes,
                       verificado=bool(res.verified), omitidos=len(res.skipped))
        if not self._alive():
            return
        self.cancel_btn.configure(text=i18n.t("common.cancel"))
        if exc is not None:
            self._set_inputs(True)
            self.pbar.configure(value=0)
            self._fail(i18n.t("zip.cancelled") if isinstance(exc, archiver.Cancelled)
                       else i18n.t("zip.failed", why=str(exc)))
            self._validate()
            return
        self.result = res
        self.pbar.configure(value=1000)
        saved = res.in_bytes - res.out_bytes
        self.prog_main.configure(
            text=i18n.t("zip.done", name=os.path.basename(res.dest)), fg=theme.ACCENT_DARK)
        lines = [i18n.t("zip.done.sizes", files=fmt_count(res.files), before=fmt_size(res.in_bytes),
                        after=fmt_size(res.out_bytes), pct=f"{res.ratio * 100:.0f}",
                        time=_duration(res.seconds))]
        lines.append(i18n.t("zip.done.saved", size=fmt_size(saved)) if saved > 0 else i18n.t("zip.done.no_gain"))
        if res.verified:
            lines.append(i18n.t("zip.done.verified"))
        if encrypted:
            lines.append(i18n.t("zip.done.encrypted"))
        if res.skipped:
            shown = "\n".join(f"   {p}: {why}" for p, why in res.skipped[:4])
            lines.append(i18n.t("zip.done.skipped", n=fmt_count(len(res.skipped)), items=shown))
            if self.want_recycle:
                lines.append(i18n.t("zip.done.no_recycle"))
                self.want_recycle = False
        self.prog_detail.configure(text="\n".join(lines))
        self.ok_btn.pack_forget()
        self.open_btn.pack(side="right", padx=(0, self._px(8)))
        self.cancel_btn.configure(text=i18n.t("zip.close"))
        self.cancel_btn.focus_set()

    def _fail(self, message: str) -> None:
        self.prog.pack(fill="x", padx=self._px(16), pady=(self._px(12), 0))
        self.prog_main.configure(text=message, fg=theme.DANGER)
        self.prog_detail.configure(text="")

    def _cancel(self) -> None:
        if self.running:        # detener: el motor borra el archivo a medias y avisa
            self.stop.set()
            self.prog_main.configure(text=i18n.t("zip.stopping"))
            return
        self.stop.set()
        self.destroy()

    def _open_folder(self) -> None:
        if self.result:
            winapi.open_in_explorer(self.result.dest)


def _duration(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds >= 3600:
        return f"{seconds // 3600} h {seconds % 3600 // 60:02d} min"
    if seconds >= 60:
        return f"{seconds // 60} min {seconds % 60:02d} s"
    return f"{seconds} s"


def ask(parent: tk.Misc, paths: list[str]) -> CompressDialog:
    """Abre la ventana y espera a que se cierre. Devuelve el diálogo (con .result)."""
    app = parent.winfo_toplevel()._superlimpio_app
    dlg = CompressDialog(parent, app, paths)
    parent.wait_window(dlg)
    return dlg
