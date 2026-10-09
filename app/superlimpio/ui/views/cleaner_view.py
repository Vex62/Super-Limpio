"""Limpieza estilo CCleaner: lista de casillas a la izquierda, resultados a la derecha."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

from ... import cleaner, i18n, winapi
from ...safety import Risk
from ...util import fmt_count, fmt_size
from .. import dialogs, theme
from ..widgets import ScrollTree
from .base import View


class CleanerView(View):
    icon = "clean"
    view_key = "cleaner"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.title = i18n.t("cleaner.title")
        self.subtitle = i18n.t("cleaner.subtitle")
        self.cats = cleaner.default_categories()
        self.vars: dict[str, tk.BooleanVar] = {}
        self.estimates: dict[str, cleaner.Estimate] = {}
        self.cancel_ev: threading.Event | None = None
        self._desc_labels: list[tk.Label] = []

        # Panel divisible: el usuario arrastra el borde para agrandar/reducir cada caja.
        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)

        # ---- izquierda: casillas por grupo (scroll)
        left = tk.Frame(body, bg=theme.CARD, highlightthickness=1, highlightbackground=theme.BORDER)
        canvas = tk.Canvas(left, bg=theme.CARD, highlightthickness=0)
        sb = ttk.Scrollbar(left, orient="vertical", command=canvas.yview)
        self.checks = tk.Frame(canvas, bg=theme.CARD)
        self.checks.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=self.checks, anchor="nw")
        canvas.bind("<Configure>", lambda e: self._on_left_resize(canvas, win, e.width))
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<Enter>", lambda e: canvas.bind_all(
            "<MouseWheel>", lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        group = None
        for c in self.cats:
            if c.group != group:
                group = c.group
                tk.Label(self.checks, text=i18n.t(f"cleaner.group.{group}").upper(), font=self.fonts.small,
                         fg=theme.MUTED, bg=theme.CARD, anchor="w").pack(
                    fill="x", padx=self.px(14), pady=(self.px(12), self.px(2)))
            v = tk.BooleanVar(value=c.default_on)
            self.vars[c.id] = v
            row = tk.Frame(self.checks, bg=theme.CARD)
            row.pack(fill="x", padx=self.px(10))
            tk.Checkbutton(row, text=c.name, variable=v, bg=theme.CARD, activebackground=theme.CARD,
                           font=self.fonts.base, anchor="w", selectcolor="#ffffff").pack(side="left")
            if c.admin:
                tk.Label(row, text=i18n.t("cleaner.admin_tag"), font=self.fonts.small, fg=theme.WARN,
                         bg=theme.CARD).pack(side="right")
            if c.risk >= Risk.ALTO:
                tk.Label(row, text=i18n.t("cleaner.irreversible_tag"), font=self.fonts.small, fg=theme.DANGER,
                         bg=theme.CARD).pack(side="right")
            desc = tk.Label(self.checks, text=c.description, font=self.fonts.small, fg=theme.MUTED,
                            bg=theme.CARD, anchor="w", justify="left", wraplength=self.px(270))
            desc.pack(fill="x", padx=self.px(36))
            self._desc_labels.append(desc)

        # ---- derecha: resultados
        right = ttk.Frame(body)
        hero = tk.Frame(right, bg=theme.CARD, highlightthickness=1, highlightbackground=theme.BORDER)
        hero.pack(fill="x")
        hin = tk.Frame(hero, bg=theme.CARD)
        hin.pack(fill="x", padx=self.px(16), pady=self.px(12))
        self.hero_big = tk.Label(hin, text="—", font=self.fonts.big, fg=theme.ACCENT_DARK, bg=theme.CARD)
        self.hero_big.pack(side="left")
        self.hero_txt = tk.Label(hin, text=i18n.t("cleaner.hero_prompt"), font=self.fonts.base,
                                 fg=theme.MUTED, bg=theme.CARD, justify="left")
        self.hero_txt.pack(side="left", padx=self.px(14))
        self.pbar = ttk.Progressbar(right, mode="determinate")
        self.pbar.pack(fill="x", pady=self.px(8))

        cols = [("cat", i18n.t("cleaner.col.category"), 260, "w"), ("size", i18n.t("cleaner.col.size"), 100, "e"),
                ("count", i18n.t("cleaner.col.files"), 90, "e"), ("note", i18n.t("cleaner.col.notes"), 360, "w")]
        box = ScrollTree(right, cols, sf=self.sf, selectmode="browse")
        box.pack(fill="both", expand=True)
        self.tree = box.tree
        self.tree.tag_configure("done", foreground=theme.ACCENT_DARK)

        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=(self.px(10), 0))
        self.clean_btn = ttk.Button(btns, text=i18n.t("cleaner.run"), style="Accent.TButton", command=self.clean)
        self.clean_btn.pack(side="right")
        self.clean_btn.state(["disabled"])
        self.an_btn = ttk.Button(btns, text=i18n.t("common.analyze"), command=self.analyze)
        self.an_btn.pack(side="right", padx=self.px(8))
        ttk.Button(btns, text=i18n.t("cleaner.mark_recommended"), command=self._defaults).pack(side="left")

        body.add(left, weight=0)
        body.add(right, weight=1)
        self.persist_sash(body, "split", 330)

    def _on_left_resize(self, canvas, win, width: int) -> None:
        canvas.itemconfigure(win, width=width)
        wrap = max(self.px(150), width - self.px(52))
        for lbl in self._desc_labels:
            lbl.configure(wraplength=wrap)

    def _defaults(self) -> None:
        for c in self.cats:
            self.vars[c.id].set(c.default_on)

    def _selected(self) -> list[cleaner.Category]:
        return [c for c in self.cats if self.vars[c.id].get()]

    # ------------------------------------------------------------ análisis
    def analyze(self) -> None:
        cats = self._selected()
        if not cats:
            return
        self.cancel_ev = ev = threading.Event()
        self.an_btn.state(["disabled"])
        self.clean_btn.state(["disabled"])
        self.tree.delete(*self.tree.get_children())
        self.estimates.clear()
        self.pbar.configure(maximum=len(cats), value=0)
        self.hero_txt.configure(text=i18n.t("cleaner.analyzing"))

        def work():
            for i, c in enumerate(cats):
                est = cleaner.analyze(c, ev)
                self.app.bg.call_in_ui(self._add_estimate, est, i + 1)
            return None

        self.app.bg.run(work, on_done=lambda _r: self._analysis_done())

    def _add_estimate(self, est: cleaner.Estimate, i: int) -> None:
        self.estimates[est.category.id] = est
        note = est.note
        if est.skipped_young:
            note = (note + " " if note else "") + i18n.t("cleaner.recent_kept", n=fmt_count(est.skipped_young))
        if not est.locations:
            note = i18n.t("cleaner.not_found")
        self.tree.insert("", "end", iid=est.category.id, values=(
            est.category.name, fmt_size(est.size), fmt_count(est.count), note),
            tags=(theme.size_tag(est.size),))
        self.pbar.configure(value=i)

    def _analysis_done(self) -> None:
        total = sum(e.size for e in self.estimates.values())
        files = sum(e.count for e in self.estimates.values())
        self.hero_big.configure(text=fmt_size(total))
        self.hero_txt.configure(text=i18n.t("cleaner.analysis_done", files=fmt_count(files)))
        self.an_btn.state(["!disabled"])
        self.clean_btn.state(["!disabled"] if total else ["disabled"])
        self.status(i18n.t("cleaner.analysis_status", size=fmt_size(total)))

    # ------------------------------------------------------------ limpieza
    def clean(self) -> None:
        cats = [c for c in self._selected() if c.id in self.estimates and self.estimates[c.id].size > 0]
        if not cats:
            return
        running = cleaner.running_process_names()
        open_apps = sorted({c.close_apps for c in cats if c.close_apps and c.close_apps.lower() in running})
        risk = max(c.risk for c in cats)
        total = sum(self.estimates[c.id].size for c in cats)
        lines = []
        for c in cats:
            e = self.estimates[c.id]
            lines.append(f"{fmt_size(e.size):>10}  {c.name}")
            for loc in e.locations[:6]:
                lines.append(f"{'':>12}{loc}")
            if len(e.locations) > 6:
                lines.append(f"{'':>12}" + i18n.t("cleaner.more_locations", n=len(e.locations) - 6))
        msg = i18n.t("cleaner.run.body", size=fmt_size(total))
        if open_apps:
            msg += i18n.t("cleaner.run.close_apps", apps=", ".join(open_apps))
        if any(c.special == "recycle_bin" for c in cats):
            msg += i18n.t("cleaner.run.recycle_warn")
        if not dialogs.confirm(self, i18n.t("cleaner.run.title"), msg, "\n".join(lines),
                               risk=max(risk, Risk.MEDIO), ok_text=i18n.t("cleaner.run.ok")):
            return
        ev = self.cancel_ev = threading.Event()
        self.an_btn.state(["disabled"])
        self.clean_btn.state(["disabled"])
        self.pbar.configure(maximum=len(cats), value=0)

        def work():
            results = []
            for i, c in enumerate(cats):
                r = cleaner.clean(c, ev)
                results.append(r)
                self.app.bg.call_in_ui(self._cleaned, r, i + 1)
            return results

        self.app.bg.run(work, on_done=self._clean_done)

    def _cleaned(self, r: cleaner.CleanResult, i: int) -> None:
        if self.tree.exists(r.category.id):
            self.tree.item(r.category.id, values=(r.category.name, fmt_size(r.freed), fmt_count(r.deleted),
                                                  i18n.t("cleaner.cleaned", note=r.note)), tags=("done",))
        self.pbar.configure(value=i)

    def _clean_done(self, results) -> None:
        freed = sum(r.freed for r in results)
        self.hero_big.configure(text=fmt_size(freed))
        self.hero_txt.configure(text=i18n.t("cleaner.done"))
        self.an_btn.state(["!disabled"])
        self.status(i18n.t("cleaner.done_status", freed=fmt_size(freed),
                           bin=fmt_size(winapi.recycle_bin_info()[0])))
