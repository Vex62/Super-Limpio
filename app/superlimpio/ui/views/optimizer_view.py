"""Optimizar: análisis exhaustivo de memoria/CPU y Modo eficiente.

El análisis solo lee contadores. El Modo eficiente propone, programa a programa,
mantener, ralentizar (reversible) o cerrar; nada se aplica sin pasar por la ventana
de confirmación, que enseña la lista exacta.
"""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import ttk

from ... import i18n, optimizer, startup, winapi
from ...optimizer import Action
from ...safety import Risk
from ...util import fmt_count, fmt_size
from .. import dialogs, theme
from ..widgets import ScrollTree, SortableTable
from .base import View

_ACTION_MARK = {Action.KEEP: "—", Action.THROTTLE: "▼", Action.CLOSE: "✕"}
_CYCLE = {Action.KEEP: Action.THROTTLE, Action.THROTTLE: Action.CLOSE, Action.CLOSE: Action.KEEP}


class OptimizerView(View):
    icon = "boost"
    view_key = "optimizer"

    def __init__(self, master, app):
        super().__init__(master, app)
        self.title = i18n.t("opt.title")
        self.subtitle = i18n.t("opt.subtitle")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        pad = self.px(10)
        self.tab_an = ttk.Frame(self.nb, padding=(0, pad, 0, 0))
        self.tab_eff = ttk.Frame(self.nb, padding=(0, pad, 0, 0))
        self.nb.add(self.tab_an, text=i18n.t("opt.tab.analysis"))
        self.nb.add(self.tab_eff, text=i18n.t("opt.tab.efficient"))
        self._build_analysis(self.tab_an)
        self._build_efficient(self.tab_eff)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._tab_changed())

    # ================================================================ análisis
    def _build_analysis(self, tab) -> None:
        self._an_stop: threading.Event | None = None
        self._report = None
        self._an_closing = False
        self._applying = False
        self._findings: dict[str, optimizer.Finding] = {}

        bar = self.toolbar(tab)
        self.an_btn = ttk.Button(bar, text=i18n.t("opt.an.run"), style="Accent.TButton", command=self.analyze)
        self.an_btn.pack(side="left")
        self.an_stop_btn = ttk.Button(bar, text=i18n.t("common.stop"), command=self._an_cancel)
        self.an_stop_btn.pack(side="left", padx=(self.px(6), 0))
        self.an_stop_btn.state(["disabled"])
        ttk.Label(bar, text=i18n.t("opt.an.duration")).pack(side="left", padx=(self.px(14), self.px(6)))
        self.an_secs = tk.StringVar(value="10 s")
        ttk.Combobox(bar, values=["10 s", "30 s", "60 s"], textvariable=self.an_secs, state="readonly",
                     width=6).pack(side="left")
        self.an_pbar = ttk.Progressbar(bar, mode="determinate", length=self.px(160))
        self.an_pbar.pack(side="left", padx=self.px(12))
        self.an_lbl = ttk.Label(bar, text=i18n.t("opt.an.prompt"), style="Muted.TLabel")
        self.an_lbl.pack(side="left", fill="x", expand=True)

        head = tk.Frame(tab, bg=theme.CARD, highlightthickness=1, highlightbackground=theme.BORDER)
        head.pack(fill="x", pady=(0, self.px(10)))
        inner = tk.Frame(head, bg=theme.CARD)
        inner.pack(fill="x", padx=self.px(14), pady=self.px(10))
        self.an_head = tk.Label(inner, text=i18n.t("opt.an.head.none"), font=self.fonts.h2, bg=theme.CARD,
                                fg=theme.TEXT, anchor="w")
        self.an_head.pack(fill="x")
        self.an_sum = tk.Label(inner, text=i18n.t("opt.an.explain"), font=self.fonts.small, bg=theme.CARD,
                               fg=theme.MUTED, anchor="w", justify="left", wraplength=self.px(900))
        self.an_sum.pack(fill="x")

        split = ttk.PanedWindow(tab, orient="vertical")
        split.pack(fill="both", expand=True)

        top = ttk.Frame(split)
        cols = [("sev", i18n.t("opt.an.col.level"), 100, "w"), ("name", i18n.t("opt.an.col.finding"), 430, "w"),
                ("desc", i18n.t("opt.an.col.detail"), 330, "w")]
        box = ScrollTree(top, cols, sf=self.sf, selectmode="browse")
        box.pack(fill="both", expand=True)
        self.find_tree = box.tree
        self.find_tree.tag_configure("s3", background=theme.ROW_HUGE)
        self.find_tree.tag_configure("s2", background=theme.ROW_BIG)
        self.find_tree.tag_configure("s1", background=theme.ROW_MID)
        self.find_tree.bind("<<TreeviewSelect>>", lambda e: self._show_advice())
        self.find_tree.bind("<Double-1>", lambda e: self._goto())
        adv = ttk.Frame(top)
        adv.pack(fill="x", pady=(self.px(6), self.px(6)))
        self.goto_btn = ttk.Button(adv, text=i18n.t("opt.an.goto"), command=self._goto)
        self.goto_btn.pack(side="right")
        self.goto_btn.state(["disabled"])
        self.advice = self.note(adv, "")
        self.advice.pack(side="left", fill="x", expand=True)

        pcols = [("name", i18n.t("memory.col.program"), 220, "w"), ("level", i18n.t("memory.col.level"), 105, "w"),
                 ("count", i18n.t("memory.col.processes"), 75, "e"),
                 ("private", i18n.t("memory.col.private"), 115, "e"), ("ws", i18n.t("memory.col.ws"), 105, "e"),
                 ("growth", i18n.t("opt.an.col.growth"), 105, "e"), ("cpu", i18n.t("opt.an.col.cpu_avg"), 85, "e"),
                 ("peak", i18n.t("opt.an.col.cpu_peak"), 85, "e"), ("handles", i18n.t("opt.an.col.handles"), 115, "e"),
                 ("window", i18n.t("opt.eff.col.window"), 110, "w")]
        bottom = ttk.Frame(split)
        closebar = ttk.Frame(bottom)
        closebar.pack(side="bottom", fill="x", pady=(self.px(6), 0))
        self.an_close_btn = ttk.Button(closebar, text=i18n.t("opt.an.close"), style="Danger.TButton",
                                       command=self.close_selected)
        self.an_close_btn.pack(side="right")
        self.an_close_btn.state(["disabled"])
        self.an_force = tk.BooleanVar(value=False)
        ttk.Checkbutton(closebar, text=i18n.t("opt.eff.opt.force"), variable=self.an_force,
                        style="Bg.TCheckbutton").pack(side="right", padx=self.px(12))
        # Al seleccionar un programa, aquí se explica qué es y qué pasa si se cierra.
        self.prog_note = self.note(closebar, i18n.t("opt.an.close_hint"))
        self.prog_note.pack(side="left", fill="x", expand=True)
        pbox = ScrollTree(bottom, pcols, sf=self.sf)
        pbox.pack(fill="both", expand=True)
        pbox.tree.bind("<<TreeviewSelect>>", lambda e: self._show_program())
        self.prog_tbl = SortableTable(
            pbox.tree,
            render=lambda u: (u.name + (f"  ·  {i18n.t('memory.this_app')}" if u.own else ""),
                              i18n.t(f"crit.level.{u.level}") if u.level else "", fmt_count(u.count),
                              fmt_size(u.private) if u.accessible else i18n.t("memory.no_access"),
                              fmt_size(u.working_set) if u.accessible else "", _signed(u.growth), _cpu(u.cpu_avg),
                              _cpu(u.cpu_peak), fmt_count(u.handles) if u.handles else "",
                              i18n.t("opt.eff.window.yes") if u.has_window else i18n.t("opt.eff.window.no")),
            sort_keys={"name": lambda u: u.name.lower(), "count": lambda u: u.count,
                       "level": lambda u: (u.level, u.private),
                       "private": lambda u: u.private, "ws": lambda u: u.working_set,
                       "growth": lambda u: u.growth, "cpu": lambda u: u.cpu_avg, "peak": lambda u: u.cpu_peak,
                       "handles": lambda u: u.handles},
            default_sort="private",
            tag_fn=lambda u: (f"lvl{u.level}",) if u.level else (() if u.accessible else ("muted",)),
            key_fn=lambda u: u.key)

        split.add(top, weight=1)
        split.add(bottom, weight=1)
        self.persist_sash(split, "analysis", 250)

    def analyze(self) -> None:
        if self._an_stop is not None:
            return
        seconds = int(self.an_secs.get().split()[0])
        stop = self._an_stop = threading.Event()
        self.an_btn.state(["disabled"])
        self.an_stop_btn.state(["!disabled"])
        self.an_pbar.configure(maximum=seconds + 1, value=0)
        self.an_lbl.configure(text=i18n.t("opt.an.running", s=seconds))
        is_admin = self.app.is_admin

        def work():
            samples = optimizer.take_samples(
                count=seconds + 1, interval=1.0, should_stop=stop.is_set, sleep=stop.wait,
                progress=lambda i, n: self.app.bg.call_in_ui(self._an_progress, i))
            if stop.is_set() or len(samples) < 2:
                return None
            windows = winapi.list_windows()
            try:
                enabled = sum(1 for i in startup.list_startup() if i.enabled is not False)
            except OSError:
                enabled = None
            plan = optimizer.build_plan(samples[-1][1], windows)
            return optimizer.analyze(samples, winapi.memory_status(), winapi.performance_info(),
                                     {w.pid for w in windows}, startup_enabled=enabled,
                                     reclaim=optimizer.reclaimable(plan), is_admin=is_admin)

        self.app.bg.run(work, on_done=self._an_done, on_error=lambda e: self._an_done(None))

    def _an_progress(self, i: int) -> None:
        if self.winfo_exists():
            self.an_pbar.configure(value=i)

    def _an_cancel(self) -> None:
        if self._an_stop is not None:
            self._an_stop.set()

    def _an_done(self, report) -> None:
        self._an_stop = None
        if not self.winfo_exists():
            return
        self.an_btn.state(["!disabled"])
        self.an_stop_btn.state(["disabled"])
        self.an_pbar.configure(value=0)
        if report is None:
            self.an_lbl.configure(text=i18n.t("opt.an.cancelled"))
            return
        self.an_lbl.configure(text=i18n.t("opt.an.done", s=f"{report.seconds:.0f}"))
        self.an_head.configure(text=i18n.t(f"opt.an.head.{report.severity}"),
                               fg=(theme.ACCENT_DARK, theme.ACCENT_DARK, theme.WARN, theme.DANGER)[report.severity])
        self.an_sum.configure(text=self._system_summary(report))

        self.find_tree.delete(*self.find_tree.get_children())
        self._findings.clear()
        for f in report.findings:
            iid = self.find_tree.insert("", "end", tags=(f"s{f.severity}",),
                                        values=(i18n.t(f"opt.an.level.{f.severity}"), f.title, f.detail))
            self._findings[iid] = f
        first = self.find_tree.get_children()
        if first:
            self.find_tree.selection_set(first[0])
        self._report = report
        self.prog_tbl.set_rows(report.programs)
        self.an_close_btn.state(["!disabled"])
        self.status(i18n.t("opt.an.status", n=len(report.findings), p=len(report.programs)))

    def pending(self) -> str:
        return i18n.t("app.pending.optimize") if (self._an_closing or self._applying) else ""

    def _show_program(self) -> None:
        """Qué es el programa seleccionado y qué pasa si se cierra."""
        rows = self.prog_tbl.selected()
        if not rows:
            self.prog_note.configure(text=i18n.t("opt.an.close_hint"), fg=theme.MUTED)
            return
        u = max(rows, key=lambda r: r.level)   # con varios, manda el más delicado
        head = i18n.t("memory.detail_title", name=u.name, level=i18n.t(f"crit.level.{u.level}"))
        if len(rows) > 1:
            head = i18n.t("memory.detail_multi", n=len(rows)) + head
        self.prog_note.configure(text=f"{head}. {u.what} {u.risk}",
                                 fg=theme.LEVEL_COLORS[u.level] if u.level else theme.TEXT)

    def close_selected(self) -> None:
        """Cierra los programas marcados en la tabla del resultado, previa confirmación."""
        if self._an_closing or self._report is None:
            return
        rows = self.prog_tbl.selected()
        if not rows:
            self.status(i18n.t("common.nothing_selected"))
            return
        # La propia aplicación no se finaliza como las demás: se cierra con orden, al final.
        close_self = any(u.own for u in rows)
        rows = [u for u in rows if not u.own]
        if not rows:
            self.app.request_close(self)
            return
        plan, blocked = optimizer.selection_plan(rows, self._report.procs, winapi.list_windows())
        if not plan.candidates:
            dialogs.error(self, i18n.t("common.protected"),
                          i18n.t("opt.an.close.blocked_body", items="\n".join(blocked[:12])))
            if close_self:
                self.app.request_close(self)
            return
        opts = optimizer.Options(force=self.an_force.get())
        details = optimizer.describe_plan(plan, opts)
        if blocked:
            details += i18n.t("memory.kill.skipped", items="\n".join(blocked[:10]))
        if not dialogs.confirm(self, i18n.t("opt.an.close.title"),
                               i18n.t("opt.eff.confirm.close_force" if opts.force else "opt.eff.confirm.close"),
                               details, risk=optimizer.plan_risk(plan, opts),
                               ok_text=i18n.t("opt.action.close")):
            return
        self._an_closing = True
        self.an_close_btn.state(["disabled"])
        self.status(i18n.t("opt.an.close.closing"))
        self.app.bg.run(lambda: optimizer.apply_plan(plan, opts),
                        on_done=lambda res: self._an_closed(plan, res, close_self),
                        on_error=lambda e: self._an_closed(plan, None))

    def _an_closed(self, plan, res, close_self: bool = False) -> None:
        self._an_closing = False
        if not self.winfo_exists():
            return
        self.an_close_btn.state(["!disabled"])
        if res is None:
            return
        gone = {c.key for c in plan.candidates
                if not any(winapi.process_alive(m.pid, m.create_time) for m in c.members)}
        self.prog_tbl.set_rows([u for u in self.prog_tbl.rows if u.key not in gone])
        lines = [i18n.t("opt.an.close.done", n=res.closed)]
        freed = res.available_after - res.available_before
        if freed > 0:
            lines.append(i18n.t("opt.eff.result.freed", size=fmt_size(freed)))
        if res.pending:
            lines.append(i18n.t("opt.eff.result.pending", items=", ".join(res.pending[:12])))
        if res.failures:
            lines.append(i18n.t("opt.eff.result.failures", items="\n".join(res.failures[:12])))
        self.status(lines[0])
        (dialogs.error if res.failures else dialogs.info)(self, i18n.t("opt.an.close.title"), "\n\n".join(lines))
        if close_self:
            self.app.request_close(self)

    def _system_summary(self, report) -> str:
        parts = []
        mem, perf = report.mem, report.perf
        if mem:
            parts.append(i18n.t("memory.ram_detail", used=fmt_size(mem.used), total=fmt_size(mem.total),
                                avail=fmt_size(mem.available), commit=""))
        if perf:
            parts.append(i18n.t("opt.an.sum.perf", commit=fmt_size(perf.commit_total),
                                limit=fmt_size(perf.commit_limit), cache=fmt_size(perf.system_cache),
                                kernel=fmt_size(perf.kernel_paged + perf.kernel_nonpaged),
                                procs=fmt_count(perf.processes), threads=fmt_count(perf.threads),
                                handles=fmt_count(perf.handles)))
        return "\n".join(parts)

    def _selected_finding(self):
        sel = self.find_tree.selection()
        return self._findings.get(sel[0]) if sel else None

    def _show_advice(self) -> None:
        f = self._selected_finding()
        self.advice.configure(text=f.advice if f else "")
        self.goto_btn.state(["!disabled"] if f and f.goto else ["disabled"])

    def _goto(self) -> None:
        f = self._selected_finding()
        if not f or not f.goto:
            return
        if f.goto == "efficient":
            self.nb.select(self.tab_eff)
        else:
            self.app.show(f.goto)

    # ========================================================== modo eficiente
    def _build_efficient(self, tab) -> None:
        self.plan: optimizer.Plan | None = None
        self._snapshot = None
        self._targets: list[tuple[str, str]] = [("", i18n.t("opt.eff.no_target"))]
        self.target_key = ""
        self.overrides: dict[str, Action] = {}
        self._eff_busy = False

        bar = self.toolbar(tab)
        ttk.Label(bar, text=i18n.t("opt.eff.target")).pack(side="left")
        self.target_var = tk.StringVar(value=self._targets[0][1])
        self.target_cb = ttk.Combobox(bar, textvariable=self.target_var, state="readonly", width=52,
                                      values=[label for _k, label in self._targets])
        self.target_cb.pack(side="left", padx=self.px(8))
        self.target_cb.bind("<<ComboboxSelected>>", lambda e: self._on_target())
        self.profile = tk.StringVar(value="game")
        for value in ("game", "program"):
            ttk.Radiobutton(bar, text=i18n.t(f"opt.eff.profile.{value}"), value=value, variable=self.profile,
                            command=self._on_profile).pack(side="left", padx=(self.px(6), 0))
        ttk.Button(bar, text=i18n.t("common.refresh"), command=self.refresh).pack(side="right")

        # Aviso de sesión activa (solo se muestra si hay algo que deshacer)
        self.banner = tk.Frame(tab, bg=theme.ACCENT_SOFT, highlightthickness=1,
                               highlightbackground=theme.ACCENT)
        self.banner_lbl = tk.Label(self.banner, text="", font=self.fonts.bold, bg=theme.ACCENT_SOFT,
                                   fg=theme.TEXT, anchor="w")
        self.banner_lbl.pack(side="left", padx=self.px(12), pady=self.px(8))
        self.restore_btn = ttk.Button(self.banner, text=i18n.t("opt.eff.restore"), command=self.restore)
        self.restore_btn.pack(side="right", padx=self.px(8), pady=self.px(6))
        self.reopen_btn = ttk.Button(self.banner, text=i18n.t("opt.eff.reopen"), command=self.reopen)
        self.reopen_btn.pack(side="right", pady=self.px(6))

        cols = [("name", i18n.t("memory.col.program"), 220, "w"), ("kind", i18n.t("opt.eff.col.kind"), 135, "w"),
                ("window", i18n.t("opt.eff.col.window"), 105, "w"),
                ("count", i18n.t("memory.col.processes"), 75, "e"),
                ("private", i18n.t("memory.col.private"), 110, "e"), ("cpu", i18n.t("memory.col.cpu"), 65, "e"),
                ("action", i18n.t("opt.eff.col.action"), 130, "w"), ("desc", i18n.t("opt.eff.col.reason"), 380, "w")]
        self.eff_box = ScrollTree(tab, cols, sf=self.sf)
        tree = self.eff_box.tree
        tree.tag_configure("a_close", background=theme.ROW_HUGE)
        tree.tag_configure("a_throttle", background=theme.ROW_MID)
        tree.bind("<Double-1>", self._cycle)
        tree.bind("<<TreeviewSelect>>", lambda e: self._show_reason())
        self.eff_tbl = SortableTable(
            tree,
            render=lambda c: (c.name, i18n.t(f"opt.cat.{c.category}"),
                              i18n.t("opt.eff.window.yes") if c.has_window else i18n.t("opt.eff.window.no"),
                              fmt_count(c.count), fmt_size(c.private), _cpu(c.cpu_pct),
                              f"{_ACTION_MARK[c.action]}  {i18n.t(f'opt.action.{c.action.value}')}",
                              i18n.t(c.reason)),
            sort_keys={"name": lambda c: c.name.lower(), "kind": lambda c: i18n.t(f"opt.cat.{c.category}"),
                       "window": lambda c: c.has_window, "count": lambda c: c.count,
                       "private": lambda c: c.private, "cpu": lambda c: c.cpu_pct,
                       "action": lambda c: c.action.value},
            default_sort="private", key_fn=lambda c: c.key,
            tag_fn=lambda c: {Action.CLOSE: ("a_close",), Action.THROTTLE: ("a_throttle",)}.get(c.action, ()))

        acts = ttk.Frame(tab)
        ttk.Label(acts, text=i18n.t("opt.eff.set_action")).pack(side="left")
        for action in (Action.KEEP, Action.THROTTLE, Action.CLOSE):
            ttk.Button(acts, text=f"{_ACTION_MARK[action]}  {i18n.t(f'opt.action.{action.value}')}",
                       command=lambda a=action: self._set_action(a)).pack(side="left", padx=(self.px(6), 0))
        ttk.Button(acts, text=i18n.t("opt.eff.recommended"), command=self._recommended).pack(
            side="left", padx=(self.px(14), 0))
        self.apply_btn = ttk.Button(acts, text=i18n.t("opt.eff.apply"), style="Accent.TButton", command=self.apply)
        self.apply_btn.pack(side="right")
        self.eff_pbar = ttk.Progressbar(acts, mode="indeterminate", length=self.px(110))

        opts = ttk.Frame(tab)
        self.opt_trim = tk.BooleanVar(value=False)
        self.opt_boost = tk.BooleanVar(value=False)
        self.opt_force = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text=i18n.t("opt.eff.opt.trim"), variable=self.opt_trim,
                        style="Bg.TCheckbutton").pack(side="left")
        self.boost_chk = ttk.Checkbutton(opts, text=i18n.t("opt.eff.opt.boost"), variable=self.opt_boost,
                                         style="Bg.TCheckbutton")
        self.boost_chk.pack(side="left", padx=self.px(14))
        ttk.Checkbutton(opts, text=i18n.t("opt.eff.opt.force"), variable=self.opt_force,
                        style="Bg.TCheckbutton").pack(side="left")

        self.eff_sum = self.note(tab, "")
        self.eff_sum.configure(fg=theme.TEXT)
        # Los controles se colocan antes que la tabla: en ventanas bajas es la tabla la que
        # encoge, y los botones y avisos siguen a la vista.
        self.note(tab, i18n.t("opt.eff.note")).pack(side="bottom", fill="x", pady=(self.px(2), 0))
        self.eff_sum.pack(side="bottom", fill="x", pady=(self.px(6), 0))
        opts.pack(side="bottom", fill="x", pady=(self.px(6), 0))
        acts.pack(side="bottom", fill="x", pady=(self.px(8), 0))
        self.eff_box.pack(fill="both", expand=True)

    def on_show(self) -> None:
        super().on_show()
        self._tab_changed()

    def _tab_changed(self) -> None:
        if self.app.current == "optimizer" and self.nb.select() == str(self.tab_eff):
            self.refresh()

    def refresh(self) -> None:
        if self._eff_busy:
            return
        self._eff_busy = True

        def work():
            before = winapi.list_processes()
            t0 = time.monotonic()
            time.sleep(0.5)
            procs = winapi.list_processes()
            cpu = optimizer.cpu_percent(before, procs, time.monotonic() - t0, os.cpu_count() or 1)
            return procs, winapi.list_windows(), cpu

        self.app.bg.run(work, on_done=self._loaded, on_error=lambda e: setattr(self, "_eff_busy", False))

    def _loaded(self, data) -> None:
        self._eff_busy = False
        if not self.winfo_exists():
            return
        self._snapshot = data
        procs, windows, _cpu_map = data
        self._targets = [("", i18n.t("opt.eff.no_target"))] + optimizer.window_targets(procs, windows)
        keys = [k for k, _label in self._targets]
        if self.target_key not in keys:
            self.target_key = ""
            self.overrides.clear()
        self.target_cb.configure(values=[label for _k, label in self._targets])
        self.target_cb.current(keys.index(self.target_key))
        self._rebuild_plan()

    def _rebuild_plan(self) -> None:
        if self._snapshot is None:
            return
        procs, windows, cpu = self._snapshot
        plan = self.plan = optimizer.build_plan(procs, windows, self.target_key, self.profile.get(), cpu)
        session = optimizer.SESSION
        for c in plan.candidates:
            if all(session.has(m.pid, m.create_time) for m in c.members):
                c.suggested = c.action = Action.KEEP   # ya está ralentizado en esta sesión
                c.reason = "opt.reason.throttled"
            elif c.key in self.overrides:
                c.action = self.overrides[c.key]
        self.eff_tbl.set_rows(plan.candidates)
        self.boost_chk.state(["!disabled"] if plan.target_members else ["disabled"])
        if not plan.target_members:
            self.opt_boost.set(False)
        self._update_summary()
        self._update_banner()

    def _update_summary(self) -> None:
        plan = self.plan
        if plan is None:
            return
        close, slow = plan.chosen(Action.CLOSE), plan.chosen(Action.THROTTLE)
        kept = sum(plan.kept.values())
        self.eff_sum.configure(text=i18n.t(
            "opt.eff.summary", close=len(close), slow=len(slow),
            ram=fmt_size(sum(c.working_set for c in close)), kept=fmt_count(kept),
            system=fmt_count(plan.kept.get("system", 0) + plan.kept.get("service", 0)),
            security=fmt_count(plan.kept.get("security", 0)),
            target=fmt_count(plan.kept.get("target", 0)),
            other=fmt_count(plan.kept.get("no_access", 0) + plan.kept.get("self", 0))))
        self.status(i18n.t("opt.eff.status", n=len(plan.candidates), close=len(close), slow=len(slow)))

    def _update_banner(self) -> None:
        session = optimizer.SESSION
        session.prune()
        if not (session.active or session.closed):
            self.banner.pack_forget()
            return
        self.banner_lbl.configure(text=i18n.t("opt.eff.banner", slow=len(session.throttled),
                                              boost=len(session.boosted), closed=len(session.closed)))
        self.restore_btn.state(["!disabled"] if session.active else ["disabled"])
        self.reopen_btn.state(["!disabled"] if session.closed else ["disabled"])
        self.banner.pack(fill="x", pady=(0, self.px(10)), before=self.eff_box)

    def _on_target(self) -> None:
        idx = self.target_cb.current()
        self.target_key = self._targets[idx][0] if 0 <= idx < len(self._targets) else ""
        self.target_cb.selection_clear()
        self.overrides.clear()
        self._rebuild_plan()

    def _on_profile(self) -> None:
        self.overrides.clear()
        self._rebuild_plan()

    def _set_action(self, action: Action, rows=None) -> None:
        rows = self.eff_tbl.selected() if rows is None else rows
        if not rows:
            self.status(i18n.t("common.nothing_selected"))
            return
        for c in rows:
            if c.reason == "opt.reason.throttled" and action == Action.THROTTLE:
                continue
            c.action = action
            self.overrides[c.key] = action
        self.eff_tbl.refresh()
        self._update_summary()

    def _show_reason(self) -> None:
        sel = self.eff_tbl.selected()
        if len(sel) == 1:   # el motivo completo, por si la columna no cabe
            self.status(f"{sel[0].name}: {i18n.t(sel[0].reason)}")

    def _cycle(self, event) -> None:
        iid = self.eff_box.tree.identify_row(event.y)
        c = self.eff_tbl.visible.get(iid)
        if c is not None:
            self._set_action(_CYCLE[c.action], [c])

    def _recommended(self) -> None:
        self.overrides.clear()
        if self.plan:
            for c in self.plan.candidates:
                c.action = c.suggested
        self.eff_tbl.refresh()
        self._update_summary()

    def _busy(self, on: bool) -> None:
        self.apply_btn.state(["disabled"] if on else ["!disabled"])
        if on:
            self.eff_pbar.pack(side="right", padx=self.px(10))
            self.eff_pbar.start(12)
        else:
            self.eff_pbar.stop()
            self.eff_pbar.pack_forget()

    def apply(self) -> None:
        plan = self.plan
        if plan is None or self._eff_busy:
            return
        opts = optimizer.Options(trim=self.opt_trim.get(), force=self.opt_force.get(),
                                 boost_target=self.opt_boost.get() and bool(plan.target_members))
        close, slow = plan.chosen(Action.CLOSE), plan.chosen(Action.THROTTLE)
        if not (close or slow or opts.boost_target):
            dialogs.info(self, i18n.t("opt.eff.confirm.title"), i18n.t("opt.eff.nothing"))
            return
        parts = []
        if slow:
            parts.append(i18n.t("opt.eff.confirm.throttle"))
            if opts.trim:
                parts.append(i18n.t("opt.eff.confirm.trim"))
        if close:
            parts.append(i18n.t("opt.eff.confirm.close_force" if opts.force else "opt.eff.confirm.close"))
        if opts.boost_target:
            parts.append(i18n.t("opt.eff.confirm.boost", name=plan.target_name))
        if not dialogs.confirm(self, i18n.t("opt.eff.confirm.title"), "\n\n".join(parts),
                               optimizer.describe_plan(plan, opts), risk=optimizer.plan_risk(plan, opts),
                               ok_text=i18n.t("opt.eff.confirm.ok")):
            return
        self._eff_busy = self._applying = True
        self._busy(True)
        self.status(i18n.t("opt.eff.applying"))
        self.app.bg.run(lambda: optimizer.apply_plan(plan, opts), on_done=self._applied,
                        on_error=lambda e: self._applied(None))

    def _applied(self, res) -> None:
        self._eff_busy = self._applying = False
        if not self.winfo_exists():
            return
        self._busy(False)
        self.overrides.clear()
        if res is not None:
            lines = [i18n.t("opt.eff.result", slow=res.throttled, closed=res.closed)]
            freed = res.available_after - res.available_before
            if freed > 0:
                lines.append(i18n.t("opt.eff.result.freed", size=fmt_size(freed)))
            if res.boosted:
                lines.append(i18n.t("opt.eff.result.boosted", n=res.boosted))
            if res.pending:
                lines.append(i18n.t("opt.eff.result.pending", items=", ".join(res.pending[:12])))
            if res.failures:
                lines.append(i18n.t("opt.eff.result.failures", items="\n".join(res.failures[:12])))
            lines.append(i18n.t("opt.eff.result.undo"))
            show = dialogs.error if res.failures else dialogs.info
            show(self, i18n.t("opt.eff.confirm.title"), "\n\n".join(lines))
        self.refresh()

    def restore(self) -> None:
        session = optimizer.SESSION
        session.prune()
        if not session.active:
            self._update_banner()
            return
        names: dict[str, int] = {}
        for t in session.throttled + session.boosted:
            names[t.name] = names.get(t.name, 0) + 1
        details = "\n".join(f"{name} ×{n}" if n > 1 else name for name, n in sorted(names.items()))
        if not dialogs.confirm(self, i18n.t("opt.eff.restore.title"), i18n.t("opt.eff.restore.body"), details,
                               risk=Risk.BAJO, ok_text=i18n.t("opt.eff.restore.ok")):
            return
        done, failures = optimizer.restore()
        if failures:
            dialogs.error(self, i18n.t("opt.eff.restore.title"), "\n".join(failures[:15]))
        self.status(i18n.t("opt.eff.restore.done", n=done))
        self.refresh()
        self._update_banner()

    def reopen(self) -> None:
        session = optimizer.SESSION
        if not session.closed:
            return
        details = "\n".join(path or name for name, path in session.closed)
        if not dialogs.confirm(self, i18n.t("opt.eff.reopen.title"), i18n.t("opt.eff.reopen.body"), details,
                               risk=Risk.BAJO, ok_text=i18n.t("opt.eff.reopen.ok")):
            return
        failures = optimizer.reopen()
        if failures:
            dialogs.error(self, i18n.t("opt.eff.reopen.title"),
                          i18n.t("opt.eff.reopen.failed", items="\n".join(failures[:15])))
        self._update_banner()
        self.after(1500, self.refresh)


def _cpu(pct: float) -> str:
    return i18n.percent(f"{pct:.1f}".replace(".", i18n.decimal_sep()))


def _signed(n: int) -> str:
    if abs(n) < 1024 * 1024:
        return ""
    return ("+" if n > 0 else "−") + fmt_size(abs(n))
