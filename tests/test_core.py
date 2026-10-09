"""Tests de la lógica (no requieren Windows ni interfaz).

Ejecutar:  runtime\\python\\python.exe -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from superlimpio import cleaner, devdeps, i18n, plat, scanner  # noqa: E402
from superlimpio.programs import Program, build_uninstall_plan, split_command  # noqa: E402
from superlimpio.safety import check_deletable  # noqa: E402
from superlimpio.util import fmt_size, text_bar  # noqa: E402
from superlimpio.plat import windows as _windows  # noqa: E402

# Estas pruebas describen escenarios de Windows (nombres de proceso, rutas...). Se fija
# su conocimiento para que den lo mismo en cualquier sistema; las de Linux lo cambian.
plat.set_knowledge("windows")


def _aes_available():
    from superlimpio import aes
    return aes.AVAILABLE


def _write(path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(b"x" * size)


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.tmp.name
        _write(os.path.join(r, "a", "f1.bin"), 1000)
        _write(os.path.join(r, "a", "b", "f2.bin"), 3000)
        _write(os.path.join(r, "c", "f3.iso"), 500)
        _write(os.path.join(r, "root.txt"), 10)
        for i in range(scanner.FILES_KEPT_PER_DIR + 15):
            _write(os.path.join(r, "many", f"s{i}.dat"), 1 + i)

    def tearDown(self):
        self.tmp.cleanup()

    def test_folder_sizes_are_recursive(self):
        res = scanner.scan(self.tmp.name)
        sizes = {c.name: c.size for c in res.root.children}
        self.assertEqual(sizes["a"], 4000)
        self.assertEqual(sizes["c"], 500)
        many = sum(1 + i for i in range(scanner.FILES_KEPT_PER_DIR + 15))
        self.assertEqual(res.root.size, 4000 + 500 + 10 + many)
        self.assertEqual(res.root.children[0].name, "a")  # ordenado por tamaño
        self.assertEqual(res.top_files[0][0], 3000)

    def test_small_files_are_aggregated(self):
        res = scanner.scan(self.tmp.name)
        many = next(c for c in res.root.children if c.name == "many")
        self.assertEqual(len(many.top_files), scanner.FILES_KEPT_PER_DIR)
        self.assertEqual(many.small_files_count, 15)
        self.assertEqual(sum(s for s, _, _ in many.top_files) + many.small_files_size, many.size)
        self.assertEqual(min(s for s, _, _ in many.top_files), 16)  # se quedan los grandes

    def test_symlinks_not_followed(self):
        if not hasattr(os, "symlink"):
            self.skipTest("sin symlinks")
        try:
            os.symlink(os.path.join(self.tmp.name, "a"), os.path.join(self.tmp.name, "link"))
        except OSError:
            self.skipTest("sin permiso para symlinks")
        res = scanner.scan(self.tmp.name)
        self.assertNotIn("link", [c.name for c in res.root.children])
        self.assertGreaterEqual(res.skipped_links, 1)

    def test_parallel_scan_matches_serial(self):
        one = scanner.scan(self.tmp.name, workers=1)
        many = scanner.scan(self.tmp.name, workers=6)
        self.assertEqual((one.root.size, one.root.files, one.root.dirs),
                         (many.root.size, many.root.files, many.root.dirs))
        self.assertEqual(one.top_files, many.top_files)
        self.assertEqual(one.by_extension, many.by_extension)
        self.assertEqual(one.by_extension[".iso"], [500, 1])
        self.assertEqual([c.name for c in one.root.children], [c.name for c in many.root.children])

    def test_cancel(self):
        ev = threading.Event()
        ev.set()
        res = scanner.scan(self.tmp.name, cancel=ev)
        self.assertTrue(res.cancelled)


class FormatTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_sizes_english(self):
        i18n.set_language("en")
        self.assertEqual(fmt_size(512), "512 B")
        self.assertEqual(fmt_size(1536), "1.5 KB")
        self.assertEqual(fmt_size(5 * 1024 ** 3), "5.0 GB")
        self.assertEqual(text_bar(1, 2, 10), "█████░░░░░")

    def test_sizes_spanish(self):
        i18n.set_language("es")
        self.assertEqual(fmt_size(1536), "1,5 KB")
        self.assertEqual(fmt_size(5 * 1024 ** 3), "5,0 GB")
        self.assertEqual(fmt_size(1500 * 1024 ** 2), "1,5 GB")


class SafetyTests(unittest.TestCase):
    def test_roots_blocked(self):
        self.assertFalse(check_deletable(os.path.abspath(os.sep)).allowed)

    def test_per_drive_system_folders_blocked(self):
        root = os.path.abspath(os.sep)
        self.assertFalse(check_deletable(os.path.join(root, "$Recycle.Bin", "S-1-5-21")).allowed)
        self.assertFalse(check_deletable(os.path.join(root, "System Volume Information")).allowed)

    def test_app_folder_blocked(self):
        from superlimpio.util import APP_ROOT
        self.assertFalse(check_deletable(str(APP_ROOT / "app")).allowed)

    def test_regular_folder_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(check_deletable(os.path.join(d, "x")).allowed)


class UninstallParsingTests(unittest.TestCase):
    def test_quoted(self):
        self.assertEqual(split_command('"C:\\Program Files\\App X\\unins000.exe" /SILENT'),
                         ("C:\\Program Files\\App X\\unins000.exe", "/SILENT"))

    def test_unquoted_with_spaces(self):
        self.assertEqual(split_command("C:\\Program Files\\Foo Bar\\uninstall.exe --remove now"),
                         ("C:\\Program Files\\Foo Bar\\uninstall.exe", "--remove now"))

    def test_msi_uses_x(self):
        p = Program(name="X", uninstall_string="MsiExec.exe /I{11111111-2222-3333-4444-555555555555}")
        plan = build_uninstall_plan(p, _windows.uninstall_command)
        self.assertIn("/X{11111111", plan.params)
        p2 = Program(name="Y", msi_code="{11111111-2222-3333-4444-555555555555}")
        self.assertEqual(build_uninstall_plan(p2, _windows.uninstall_command).params, "/x {11111111-2222-3333-4444-555555555555}")


class ElevationTests(unittest.TestCase):
    def test_launcher_needs_no_script(self):
        from unittest import mock
        from superlimpio.plat import windows as winapi
        with mock.patch.object(sys, "executable", r"E:\SuperLimpio\SuperLimpio.exe"):
            self.assertEqual(winapi.admin_command(r"E:\SuperLimpio\app\main.py"),
                             (r"E:\SuperLimpio\SuperLimpio.exe", ""))

    def test_python_gets_the_script(self):
        from unittest import mock
        from superlimpio.plat import windows as winapi
        with mock.patch.object(sys, "executable", r"E:\nada\pythonw.exe"):
            self.assertEqual(winapi.admin_command(r"E:\app\main.py"),
                             (r"E:\nada\pythonw.exe", r'"E:\app\main.py"'))


class DevDepsTests(unittest.TestCase):
    def test_finds_node_modules_and_requires_markers(self):
        with tempfile.TemporaryDirectory() as r:
            _write(os.path.join(r, "web", "package.json"), 5)
            _write(os.path.join(r, "web", "node_modules", "lib", "index.js"), 2000)
            _write(os.path.join(r, "web", "node_modules", "inner", "node_modules", "x.js"), 10)
            _write(os.path.join(r, "py", ".venv", "pyvenv.cfg"), 5)
            _write(os.path.join(r, "py", ".venv", "Lib", "x.py"), 100)
            _write(os.path.join(r, "docs", "target", "keep.txt"), 50)  # sin Cargo.toml
            _write(os.path.join(r, "rs", "Cargo.toml"), 5)
            _write(os.path.join(r, "rs", "target", "debug", "app"), 700)
            found = devdeps.find_artifacts(r)
            names = sorted(os.path.relpath(a.path, r) for a in found)
            self.assertEqual(names, sorted([os.path.join("web", "node_modules"),
                                            os.path.join("py", ".venv"),
                                            os.path.join("rs", "target")]))
            nm = next(a for a in found if a.path.endswith("node_modules"))
            self.assertEqual(nm.size, 2010)


class CleanerTests(unittest.TestCase):
    def test_analyze_and_clean_respect_age(self):
        with tempfile.TemporaryDirectory() as r:
            old = os.path.join(r, "cache", "old.tmp")
            new = os.path.join(r, "cache", "sub", "new.tmp")
            _write(old, 100)
            _write(new, 50)
            past = time.time() - 3 * 86400
            os.utime(old, (past, past))
            cat = cleaner.Category("t", "Test", "Test", "", dirs=[os.path.join(r, "cache")],
                                   min_age_hours=24)
            est = cleaner.analyze(cat)
            self.assertEqual((est.size, est.count, est.skipped_young), (100, 1, 1))
            res = cleaner.clean(cat)
            self.assertEqual(res.freed, 100)
            self.assertFalse(os.path.exists(old))
            self.assertTrue(os.path.exists(new))
            self.assertTrue(os.path.isdir(os.path.join(r, "cache")))  # la raíz se conserva

    def test_categories_are_well_formed(self):
        ids = [c.id for c in cleaner.default_categories()]
        self.assertEqual(len(ids), len(set(ids)))


class ResilienceTests(unittest.TestCase):
    """Config atómica, tolerancia a corrupción y modo de recuperación."""

    def setUp(self):
        from superlimpio import config
        self.config = config
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = os.path.join(self.tmp.name, "superlimpio.config.json")
        self._orig = config._candidate_paths
        config._candidate_paths = lambda: [self.cfg]
        config._data = None
        config._path = None

    def tearDown(self):
        self.config._candidate_paths = self._orig
        self.config._data = None
        self.config._path = None
        self.tmp.cleanup()

    def test_backup_created_on_second_write(self):
        self.config.set("language", "es")
        self.assertTrue(os.path.exists(self.cfg))
        self.assertFalse(os.path.exists(self.cfg + ".tmp"))  # el temporal no queda
        self.config.set("language", "en")
        self.assertTrue(os.path.exists(self.cfg + ".bak"))

    def test_recovers_from_corrupt_primary_via_backup(self):
        self.config.set("language", "es")
        self.config.set("language", "en")   # .bak guarda "es"; primario = "en"
        with open(self.cfg, "w", encoding="utf-8") as fh:
            fh.write("{ esto no es json valido")
        self.config._data = None
        self.config._path = None
        self.assertEqual(self.config.get("language"), "es")  # recuperado del .bak

    def test_corrupt_without_backup_resets_and_quarantines(self):
        self.config.set("language", "es")   # una sola escritura: no hay .bak
        with open(self.cfg, "w", encoding="utf-8") as fh:
            fh.write("roto")
        self.config._data = None
        self.config._path = None
        self.assertIsNone(self.config.get("language"))        # valores por defecto
        self.assertTrue(os.path.exists(self.cfg + ".corrupt"))

    def test_recovery_flag_cycle(self):
        from superlimpio import recovery
        recovery.mark_started()
        self.assertFalse(recovery.pending_recovery())
        recovery.mark_starting()
        self.assertTrue(recovery.pending_recovery())
        recovery.mark_started()
        self.assertFalse(recovery.pending_recovery())

    def test_repair_resets_config(self):
        from superlimpio import recovery
        orig_clear = recovery._clear_bytecode_caches
        recovery._clear_bytecode_caches = lambda: 0   # no tocar cachés reales en el test
        try:
            self.config.set_scale(1.5)
            self.assertEqual(self.config.get_scale(), 1.5)
            recovery.repair("test")
            self.assertEqual(self.config.get_scale(), 1.0)
        finally:
            recovery._clear_bytecode_caches = orig_clear


def _proc(pid, name, path="", ppid=1, private=100 * 1024 ** 2, ct=None, accessible=True, **kw):
    from superlimpio.plat import RawProcess
    return RawProcess(pid=pid, ppid=ppid, name=name, threads=1, path=path, working_set=private,
                      private=private, accessible=accessible, create_time=ct if ct is not None else float(pid),
                      **kw)


class _FakeApi:
    """Sustituye a winapi: anota lo que se le pide y simula qué procesos siguen vivos."""

    def __init__(self, stubborn=()):
        self.dead, self.stubborn = set(), set(stubborn)
        self.throttled, self.restored, self.terminated, self.closed_hwnds, self.trimmed = [], [], [], [], []
        self.priorities = {}

    def memory_status(self):
        return None

    def process_alive(self, pid, create_time=None):
        return pid not in self.dead

    def set_efficiency(self, pid, create_time=None):
        self.throttled.append(pid)
        return True, "ok", 0x20

    def restore_efficiency(self, pid, priority, create_time=None):
        self.restored.append((pid, priority))
        return True, "ok"

    def set_priority(self, pid, priority, create_time=None):
        prev = self.priorities.get(pid, 0x20)
        self.priorities[pid] = priority
        return True, "ok", prev

    def trim_working_set(self, pid, create_time=None):
        self.trimmed.append(pid)
        return True, "ok"

    def terminate_process(self, pid, create_time=None):
        self.terminated.append(pid)
        self.dead.add(pid)
        return True, "ok"

    def close_window(self, hwnd):
        self.closed_hwnds.append(hwnd)
        if hwnd not in self.stubborn:   # hwnd == pid en estos tests
            self.dead.add(hwnd)
        return True


def _quiet(*_a, **_k):
    pass


class OptimizerTests(unittest.TestCase):
    WIN = r"C:\Windows"

    def setUp(self):
        from superlimpio import optimizer
        from superlimpio.plat import WindowInfo
        self.o = optimizer
        chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        self.procs = [
            _proc(4, "System", accessible=False),
            _proc(500, "services.exe", self.WIN + r"\System32\services.exe", accessible=False),
            _proc(600, "explorer.exe", self.WIN + r"\explorer.exe"),
            _proc(610, "svchost.exe", self.WIN + r"\System32\svchost.exe"),
            _proc(700, "UpdSvc.exe", r"C:\Program Files\Vendor\UpdSvc.exe", ppid=500),
            _proc(800, "MsMpEng.exe", accessible=False),
            _proc(810, "vgc.exe", r"C:\Program Files\Riot Vanguard\vgc.exe"),
            _proc(900, "steam.exe", r"C:\Games\Steam\steam.exe", ppid=600),
            _proc(901, "steamwebhelper.exe", r"C:\Games\Steam\bin\steamwebhelper.exe", ppid=900),
            _proc(910, "game.exe", r"C:\Games\Steam\steamapps\common\Game\game.exe", ppid=900),
            _proc(1000, "chrome.exe", chrome, ppid=600),
            _proc(1001, "chrome.exe", chrome, ppid=1000),
            _proc(1100, "ms-teams.exe", r"C:\Program Files\WindowsApps\MSTeams\ms-teams.exe", ppid=610),
            _proc(1101, "msedgewebview2.exe", r"C:\Program Files (x86)\Microsoft\EdgeWebView\msedgewebview2.exe",
                  ppid=1100),
            _proc(1200, "GoogleUpdate.exe", r"C:\Program Files (x86)\Google\Update\GoogleUpdate.exe", ppid=600),
            _proc(1300, "notes.exe", r"C:\Apps\Notes\notes.exe", ppid=600),
            _proc(1400, "agent.exe", r"C:\Apps\Agent\agent.exe", ppid=600),
            _proc(1500, "tiny.exe", r"C:\Apps\Tiny\tiny.exe", ppid=600, private=5 * 1024 ** 2),
            _proc(2000, "pythonw.exe", r"D:\SL\runtime\python\pythonw.exe", ppid=600),
        ]
        self.windows = [WindowInfo(1000, 1000, "Tabs"), WindowInfo(910, 910, "Game"),
                        WindowInfo(1300, 1300, "Notes"), WindowInfo(600, 600, "Files")]

    def plan(self, target="", profile="game"):
        return self.o.build_plan(self.procs, self.windows, target, profile, self_pid=2000, windir=self.WIN)

    @staticmethod
    def by_name(plan):
        return {c.name: c for c in plan.candidates}

    def test_system_services_security_and_self_are_never_offered(self):
        plan = self.plan()
        names = set(self.by_name(plan))
        for forbidden in ("System", "services.exe", "explorer.exe", "svchost.exe", "UpdSvc.exe", "MsMpEng.exe",
                          "vgc.exe", "pythonw.exe"):
            self.assertNotIn(forbidden, names)
        self.assertEqual(plan.kept["service"], 1)
        self.assertEqual(plan.kept["self"], 1)
        self.assertGreaterEqual(plan.kept["security"], 1)

    def test_process_trees_are_one_program(self):
        c = self.by_name(self.plan())
        self.assertEqual(c["chrome.exe"].count, 2)
        self.assertEqual(c["steam.exe"].count, 3)                 # ayudante + juego bajo su carpeta
        self.assertEqual(c["ms-teams.exe"].count, 2)              # la vista web incrustada va con Teams
        self.assertNotIn("msedgewebview2.exe", c)
        self.assertTrue(c["steam.exe"].has_window)                # la ventana del juego cuenta

    def test_default_proposals(self):
        A = self.o.Action
        c = self.by_name(self.plan(profile="game"))
        self.assertEqual(c["GoogleUpdate.exe"].action, A.CLOSE)
        self.assertEqual(c["chrome.exe"].action, A.THROTTLE)
        self.assertEqual(c["ms-teams.exe"].action, A.KEEP)       # llamadas
        self.assertEqual(c["steam.exe"].action, A.KEEP)          # jugando: la plataforma se queda
        self.assertEqual(c["notes.exe"].action, A.KEEP)          # abierto por el usuario
        self.assertEqual(c["agent.exe"].action, A.THROTTLE)      # segundo plano desconocido
        self.assertEqual(c["tiny.exe"].action, A.KEEP)           # no merece la pena
        c = self.by_name(self.plan(profile="program"))
        self.assertEqual(c["steam.exe"].action, A.THROTTLE)

    def test_target_family_is_kept(self):
        key = self.o.program_key(self.procs[9])                   # game.exe
        plan = self.plan(target=key)
        self.assertNotIn("steam.exe", self.by_name(plan))        # lanzador y ayudantes del juego
        self.assertEqual(plan.kept["target"], 3)
        self.assertEqual([m.pid for m in plan.target_members], [910])
        self.assertIn("chrome.exe", self.by_name(plan))

    def test_reused_parent_pid_does_not_link_processes(self):
        self.procs.append(_proc(3000, "orphan.exe", r"C:\Program Files\Google\Chrome\Application\orphan.exe",
                                ppid=1000, ct=5.0))               # el «padre» 1000 nació después
        self.assertIn("orphan.exe", self.by_name(self.plan()))

    def test_window_targets_skip_shell(self):
        labels = dict(self.o.window_targets(self.procs, self.windows))
        self.assertEqual(len(labels), 3)
        self.assertFalse(any("explorer" in k for k in labels))

    def test_apply_throttle_and_restore(self):
        plan, api, session = self.plan(), _FakeApi(), self.o.Session()
        for c in plan.candidates:
            c.action = self.o.Action.THROTTLE if c.name == "chrome.exe" else self.o.Action.KEEP
        res = self.o.apply_plan(plan, self.o.Options(trim=True), session, api, log=_quiet)
        self.assertEqual(sorted(api.throttled), [1000, 1001])
        self.assertEqual(sorted(api.trimmed), [1000, 1001])
        self.assertEqual((res.throttled, res.closed, api.terminated), (1, 0, []))
        self.assertTrue(session.active)
        api.dead.add(1001)                                        # uno se cerró mientras tanto
        done, failures = self.o.restore(session, api, log=_quiet)
        self.assertEqual((done, failures, api.restored), (1, [], [(1000, 0x20)]))
        self.assertFalse(session.active)

    def _close(self, force):
        A = self.o.Action
        plan, api = self.plan(), _FakeApi(stubborn={1300})
        for c in plan.candidates:
            c.action = A.CLOSE if c.name in ("notes.exe", "agent.exe") else A.KEEP
        now = [0.0]
        res = self.o.apply_plan(plan, self.o.Options(force=force, grace=2.0), self.o.Session(), api, log=_quiet,
                                sleep=lambda s: now.__setitem__(0, now[0] + s), clock=lambda: now[0])
        return res, api

    def test_close_asks_windows_and_does_not_force_by_default(self):
        res, api = self._close(force=False)
        self.assertEqual(api.terminated, [1400])                  # solo el que no tiene ventana
        self.assertEqual(api.closed_hwnds, [1300])                # al de la ventana se le pide
        self.assertEqual(res.pending, ["notes.exe"])              # no se cerró: se deja abierto
        self.assertEqual(res.closed, 1)

    def test_close_forces_only_when_told(self):
        res, api = self._close(force=True)
        self.assertEqual(sorted(api.terminated), [1300, 1400])
        self.assertEqual((res.pending, res.closed), ([], 2))

    def test_apply_never_touches_protected_even_if_injected(self):
        plan, api = self.plan(), _FakeApi()
        rogue = self.o.Candidate("x", "lsass.exe", "", members=[_proc(77, "lsass.exe")],
                                 action=self.o.Action.CLOSE)
        slow = self.o.Candidate("y", "explorer.exe", "", members=[self.procs[2]],
                                action=self.o.Action.THROTTLE)
        plan.candidates[:] = [rogue, slow]
        self.o.apply_plan(plan, self.o.Options(force=True), self.o.Session(), api, log=_quiet)
        self.assertEqual((api.terminated, api.throttled), ([], []))

    def test_manual_selection_from_analysis_respects_protection(self):
        rep = self.o.analyze([(0.0, self.procs), (1.0, self.procs)], ncpu=4, self_pid=2000)
        wanted = ("chrome.exe", "explorer.exe", "vgc.exe", "pythonw.exe", "UpdSvc.exe", "agent.exe")
        pick = [u for u in rep.programs if u.name in wanted]
        plan, blocked = self.o.selection_plan(pick, rep.procs, self.windows, self_pid=2000, windir=self.WIN)
        c = self.by_name(plan)
        self.assertEqual(sorted(c), ["agent.exe", "chrome.exe"])     # lo protegido no entra
        self.assertEqual(len(blocked), 4)
        self.assertEqual((c["chrome.exe"].count, c["chrome.exe"].has_window), (2, True))
        self.assertTrue(all(x.action == self.o.Action.CLOSE for x in plan.candidates))
        api = _FakeApi()
        res = self.o.apply_plan(plan, self.o.Options(grace=0.0), self.o.Session(), api, log=_quiet)
        self.assertEqual(api.terminated, [1400])                     # sin ventana: se finaliza
        self.assertEqual(api.closed_hwnds, [1000])                   # con ventana: solo se le pide
        self.assertEqual(res.pending, ["chrome.exe"])                # y sin forzar, se respeta

    def test_risk_grows_with_what_is_asked(self):
        A, plan = self.o.Action, self.plan()
        for c in plan.candidates:
            c.action = A.THROTTLE
        self.assertEqual(self.o.plan_risk(plan, self.o.Options()).name, "BAJO")
        self.by_name(plan)["notes.exe"].action = A.CLOSE
        self.assertEqual(self.o.plan_risk(plan, self.o.Options()).name, "MEDIO")
        self.assertEqual(self.o.plan_risk(plan, self.o.Options(force=True)).name, "ALTO")
        self.assertIn("notes.exe", self.o.describe_plan(plan, self.o.Options()))

    def test_analysis_finds_pressure_growth_and_background_cpu(self):
        from superlimpio.plat import MemoryStatus
        gb, mb = 1024 ** 3, 1024 ** 2
        samples = []
        for i in range(5):
            samples.append((float(i), [
                _proc(10, "leaky.exe", r"C:\A\leaky.exe", private=gb + i * 60 * mb),
                _proc(11, "miner.exe", r"C:\B\miner.exe", cpu_time=i * 2.0),      # 2 s de CPU por segundo
                _proc(12, "calm.exe", r"C:\C\calm.exe", cpu_time=0.0),
                _proc(13, "big.exe", r"C:\D\big.exe", private=6 * gb),
            ]))
        mem = MemoryStatus(total=16 * gb, available=1 * gb, load_pct=94, commit_total=20 * gb,
                           commit_available=3 * gb)
        rep = self.o.analyze(samples, mem, None, window_pids={13}, ncpu=4, self_pid=-1)
        titles = " | ".join(f.title for f in rep.findings)
        self.assertEqual(rep.severity, 3)
        self.assertIn("leaky.exe", titles)
        self.assertIn("miner.exe", titles)
        self.assertIn("big.exe", titles)
        self.assertNotIn("calm.exe", titles)
        usage = {u.name: u for u in rep.programs}
        self.assertAlmostEqual(usage["miner.exe"].cpu_avg, 50.0)
        self.assertEqual(usage["leaky.exe"].growth, 240 * mb)
        self.assertEqual(rep.findings[0].severity, 3)             # lo urgente, primero

    def test_calm_system_reports_no_problems(self):
        from superlimpio.plat import MemoryStatus
        gb = 1024 ** 3
        samples = [(float(i), [_proc(12, "calm.exe", r"C:\C\calm.exe")]) for i in range(3)]
        rep = self.o.analyze(samples, MemoryStatus(16 * gb, 10 * gb, 37, 20 * gb, 12 * gb), None, ncpu=4,
                             self_pid=-1)
        self.assertEqual(rep.severity, 0)

    def test_every_optimizer_text_is_translated(self):
        for key, entry in i18n.CATALOG.items():
            if key.startswith("opt."):
                self.assertTrue(entry.get("en") and entry.get("es"), key)
        for cat in list(plat.know.CATALOG) + ["other"]:
            self.assertIn(f"opt.cat.{cat}", i18n.CATALOG)


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


class ArchiverTests(unittest.TestCase):
    """Compresor propio: los archivos se releen con lectores independientes."""

    def setUp(self):
        from superlimpio import aes, archiver
        self.a, self.aes = archiver, aes
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "datos ñ")
        self.content = {
            "uno.txt": ("texto repetido áé\n" * 4000).encode("utf-8"),
            "vacio.bin": b"",
            "sub/dos.log": b"0123456789abcdef" * 9000,
            "sub/tres.bin": bytes((i * 7919) % 251 for i in range(70000)),
        }
        for rel, data in self.content.items():
            full = os.path.join(self.src, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(data)
        os.makedirs(os.path.join(self.src, "sub", "hueca"))

    def tearDown(self):
        i18n.set_language("en")
        self.tmp.cleanup()

    def pack(self, fmt, password="", level="fast", **kw):
        col = self.a.collect([self.src])
        dest = os.path.join(self.tmp.name, f"out.{fmt}")
        return self.a.compress(col, self.a.Options(dest, fmt, level, password, **kw))

    def test_collect_counts_and_never_duplicates_nested_selection(self):
        col = self.a.collect([self.src, os.path.join(self.src, "sub"), os.path.join(self.src, "uno.txt")])
        self.assertEqual((col.files, col.dirs), (4, 3))
        self.assertEqual(col.total, sum(len(v) for v in self.content.values()))
        names = {e.arcname for e in col.entries}
        self.assertIn("datos ñ/sub/dos.log", names)
        self.assertEqual(len(names), len(col.entries))

    def test_links_are_skipped_not_followed(self):
        link = os.path.join(self.src, "enlace")
        try:
            os.symlink(self.tmp.name, link, target_is_directory=True)
        except (OSError, NotImplementedError, AttributeError):
            self.skipTest("sin permiso para crear enlaces simbólicos")
        col = self.a.collect([self.src])
        self.assertEqual([p for p, _why in col.skipped], [link])
        self.assertEqual(col.files, 4)

    def test_zip_is_readable_by_the_standard_library(self):
        import zipfile
        res = self.pack("zip", level="max")
        self.assertTrue(res.verified)
        self.assertLess(res.out_bytes, res.in_bytes)
        with zipfile.ZipFile(res.dest) as zf:
            self.assertIsNone(zf.testzip())
            for rel, data in self.content.items():
                self.assertEqual(zf.read("datos ñ/" + rel), data)
            self.assertIn("datos ñ/sub/hueca/", zf.namelist())

    def test_7z_solid_stream_decodes_to_the_original_bytes(self):
        import lzma
        import struct
        res = self.pack("7z", level="normal")
        raw = _read_bytes(res.dest)
        self.assertEqual(raw[:6], b"7z\xbc\xaf\x27\x1c")
        next_offset, next_size, next_crc = struct.unpack("<QQI", raw[12:32])
        import zlib
        self.assertEqual(zlib.crc32(raw[12:32]), struct.unpack("<I", raw[8:12])[0])
        self.assertEqual(zlib.crc32(raw[32 + next_offset:32 + next_offset + next_size]), next_crc)
        self.assertEqual(32 + next_offset + next_size, len(raw))
        plain = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[
            {"id": lzma.FILTER_LZMA2, "dict_size": 1 << 24}]).decompress(raw[32:32 + next_offset])
        # sólido y ordenado por tipo: .bin, .log, .txt
        self.assertEqual(plain, self.content["sub/tres.bin"] + self.content["sub/dos.log"] + self.content["uno.txt"])
        self.assertIn("uno.txt".encode("utf-16-le"), raw)

    def test_parallel_blocks_form_one_valid_stream(self):
        import lzma
        big = os.path.join(self.src, "grande.dat")
        data = b"".join(b"%07d registro de prueba\n" % i for i in range(400000))     # ~10 MiB
        with open(big, "wb") as fh:
            fh.write(data)
        col = self.a.collect([big])
        gb = 1024 ** 3
        how = self.a.plan("7z", "fast", col.total, 16 * gb, 8 * gb, cpus=4)
        self.assertGreater(how.threads, 1)
        dest = os.path.join(self.tmp.name, "multi.7z")
        import unittest.mock as mock
        with mock.patch.object(os, "cpu_count", return_value=4):
            res = self.a.compress(col, self.a.Options(dest, "7z", "fast", "", True, 16 * gb, 8 * gb))
        self.assertTrue(res.verified)
        raw = _read_bytes(dest)
        import struct
        next_offset = struct.unpack("<Q", raw[12:20])[0]
        plain = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[
            {"id": lzma.FILTER_LZMA2, "dict_size": 1 << 20}]).decompress(raw[32:32 + next_offset])
        self.assertEqual(plain, data)

    def test_plan_respects_the_memory_of_the_machine(self):
        gb = 1024 ** 3
        small = self.a.plan("7z", "ultra", 50 * gb, 2 * gb, gb // 4, cpus=8)
        large = self.a.plan("7z", "ultra", 50 * gb, 64 * gb, 48 * gb, cpus=8)
        self.assertEqual(large.dict_size, 64 * 1024 ** 2)
        self.assertLess(small.dict_size, large.dict_size)
        self.assertLessEqual(small.memory, 2 * gb // 4)
        self.assertEqual(small.threads, 1)
        self.assertGreater(large.threads, 1)
        self.assertEqual(self.a.plan("7z", "ultra", 100_000).dict_size, 1024 ** 2)    # no más que los datos

    def test_password_rules(self):
        self.assertTrue(self.a.password_ok("7z", "Señor ñandú ✓"))
        self.assertFalse(self.a.password_ok("zip", "Señor"))
        self.assertTrue(self.a.password_ok("zip", "Clave-123 !"))
        if self.aes.AVAILABLE:
            with self.assertRaises(self.a.ArchiveError):
                self.pack("zip", "contraseña")
            self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "out.zip.part")))

    @unittest.skipUnless(_aes_available(), "este equipo no tiene AES del sistema (CNG u OpenSSL)")
    def test_aes_matches_the_official_vector(self):
        key = bytes(range(32))
        out = self.aes.Aes(key).encrypt(bytes.fromhex("00112233445566778899aabbccddeeff"))
        self.assertEqual(out.hex(), "8ea2b7ca516745bfeafc49904b496089")      # FIPS-197, C.3
        a, b = self.aes.Ctr(key), self.aes.Ctr(key)
        msg = bytes(range(256)) * 41
        self.assertEqual(b.process(a.process(msg[:5]) + a.process(msg[5:])), msg)

    @unittest.skipUnless(_aes_available(), "este equipo no tiene AES del sistema (CNG u OpenSSL)")
    def test_encrypted_archives_hide_content_and_verify(self):
        for fmt, pw in (("7z", "Señor ñandú ✓"), ("zip", "Clave-123 !")):
            res = self.pack(fmt, pw)
            self.assertTrue(res.verified, fmt)
            raw = _read_bytes(res.dest)
            self.assertNotIn(b"0123456789abcdef0123456789abcdef", raw)
            if fmt == "7z":   # cabecera cifrada: ni los nombres
                self.assertNotIn("uno.txt".encode("utf-16-le"), raw)
            else:             # una contraseña distinta no supera la comprobación
                with self.assertRaises(self.a.ArchiveError):
                    self.a._verify_zip(res.dest, "otra", self.a._Reporter(None, None, 0))
            os.remove(res.dest)

    @unittest.skipUnless(os.path.exists(r"C:\Program Files\7-Zip\7z.exe"), "7-Zip no está instalado")
    def test_real_7zip_accepts_our_archives(self):
        import subprocess
        for fmt, pw in (("7z", ""), ("7z", "Señor ñandú ✓"), ("zip", ""), ("zip", "Clave-123 !")):
            res = self.pack(fmt, pw, level="normal")
            run = subprocess.run([r"C:\Program Files\7-Zip\7z.exe", "t", res.dest, f"-p{pw or 'x'}"],
                                 capture_output=True)
            self.assertEqual(run.returncode, 0, (fmt, pw, run.stdout[-300:]))
            if pw:
                bad = subprocess.run([r"C:\Program Files\7-Zip\7z.exe", "t", res.dest, "-pmala"],
                                     capture_output=True)
                self.assertNotEqual(bad.returncode, 0)
            os.remove(res.dest)

    def test_cancel_and_errors_leave_nothing_behind(self):
        col = self.a.collect([self.src])
        dest = os.path.join(self.tmp.name, "x.7z")
        calls = [0]

        def stop():
            calls[0] += 1
            return calls[0] > 2

        with self.assertRaises(self.a.Cancelled):
            self.a.compress(col, self.a.Options(dest, "7z", "fast"), should_stop=stop)
        self.assertEqual([f for f in os.listdir(self.tmp.name) if f.startswith("x.")], [])
        # el destino no puede ser uno de los originales
        victim = os.path.join(self.src, "uno.txt")
        with self.assertRaises(self.a.ArchiveError):
            self.a.compress(col, self.a.Options(victim, "zip", "fast"))
        self.assertEqual(_read_bytes(victim), self.content["uno.txt"])

    def test_unreadable_file_is_reported_and_the_rest_is_kept(self):
        col = self.a.collect([self.src])
        os.remove(os.path.join(self.src, "uno.txt"))          # desaparece entre el recuento y la compresión
        res = self.a.compress(col, self.a.Options(os.path.join(self.tmp.name, "r.zip"), "zip", "fast"))
        self.assertEqual(len(res.skipped), 1)
        self.assertEqual(res.files, 3)
        self.assertTrue(res.verified)

    def test_default_name_never_overwrites(self):
        first = self.a.default_dest([self.src], "7z")
        self.assertEqual(os.path.basename(first), "datos ñ.7z")
        open(first, "wb").close()
        self.assertEqual(os.path.basename(self.a.default_dest([self.src], "7z")), "datos ñ (2).7z")
        single = os.path.join(self.src, "uno.txt")
        self.assertEqual(os.path.basename(self.a.default_dest([single], "zip")), "uno.zip")


class I18nTests(unittest.TestCase):
    def test_placeholders_may_be_called_like_the_parameters(self):
        # «programs.detail» lleva un marcador {key}: no puede chocar con el parámetro de t()
        text = i18n.t("programs.detail", cmd="unins.exe /S", key=r"HKLM\Software\X")
        self.assertIn("unins.exe /S", text)
        self.assertIn(r"HKLM\Software\X", text)
        self.assertEqual(i18n.t("no.such.key {key} {n}", key="a", n=2), "no.such.key a 2")
        self.assertIn("3", i18n.plural(3, "items"))

    def test_catalog_is_complete_in_both_languages(self):
        import re
        for key, entry in i18n.CATALOG.items():
            self.assertEqual(set(entry), {"en", "es"}, key)
            marks = [sorted(re.findall(r"\{(\w+)\}", entry[lang])) for lang in ("en", "es")]
            self.assertEqual(marks[0], marks[1], key)


class WindowGeometryTests(unittest.TestCase):
    AREA = (0, 0, 1920, 1040)

    def setUp(self):
        from superlimpio.ui import winframe
        self.w = winframe

    def test_fit_keeps_the_rectangle_inside(self):
        self.assertEqual(self.w.fit_rect(100, 100, 800, 600, self.AREA), (100, 100, 800, 600))
        self.assertEqual(self.w.fit_rect(1500, 900, 800, 600, self.AREA), (1120, 440, 800, 600))
        self.assertEqual(self.w.fit_rect(-50, -20, 800, 600, self.AREA), (0, 0, 800, 600))
        # más grande que la pantalla: se encoge
        self.assertEqual(self.w.fit_rect(10, 10, 3000, 2000, self.AREA), (0, 0, 1920, 1040))
        # monitor a la izquierda del principal (coordenadas negativas)
        self.assertEqual(self.w.fit_rect(0, 0, 800, 600, (-1280, 0, 0, 1024)), (-800, 0, 800, 600))

    def test_window_dragged_away_comes_back_within_reach(self):
        keep = self.w.keep_reachable
        self.assertEqual(keep(300, 200, 800, 600, self.AREA), (300, 200))       # dentro: no se toca
        self.assertEqual(keep(-400, 200, 800, 600, self.AREA), (-400, 200))     # a medias fuera: tampoco
        self.assertEqual(keep(-790, 200, 800, 600, self.AREA), (-680, 200))     # casi nada a la vista
        self.assertEqual(keep(1910, 200, 800, 600, self.AREA), (1800, 200))
        self.assertEqual(keep(300, -300, 800, 600, self.AREA), (300, 0))        # la barra de título, arriba
        self.assertEqual(keep(300, 1035, 800, 600, self.AREA), (300, 1000))     # ...o escondida abajo

    def test_resolution_change_keeps_proportions(self):
        old, new = (0, 0, 1920, 1080), (0, 0, 1280, 720)
        self.assertEqual(self.w.rescale_rect(480, 270, 960, 540, old, new), (320, 180, 640, 360))
        # con un mínimo, el tamaño no baja de ahí y la ventana sigue entera en pantalla
        x, y, w, h = self.w.rescale_rect(1200, 600, 700, 450, old, new, min_size=(760, 520))
        self.assertEqual((w, h), (760, 520))
        self.assertTrue(0 <= x and x + w <= 1280 and 0 <= y and y + h <= 720)
        # y al volver a la resolución grande recupera su proporción
        self.assertEqual(self.w.rescale_rect(320, 180, 640, 360, new, old), (480, 270, 960, 540))


class CriticalityTests(unittest.TestCase):
    WIN = r"C:\Windows"
    ENV = {"sysdrive": "C:", "windir": r"C:\Windows", "programdata": r"C:\ProgramData",
           "program_files": [r"C:\Program Files", r"C:\Program Files (x86)"], "users": r"C:\Users",
           "profile": r"C:\Users\ana", "app_root": r"D:\Apps\SuperLimpio"}

    def setUp(self):
        from superlimpio import criticality
        self.c = criticality

    def proc(self, name, path="", **kw):
        kw.setdefault("self_pid", 999999)
        return self.c.assess_process(name, path, windir=self.WIN, **kw)

    def test_processes_are_ranked_by_what_breaks(self):
        L = self.c.Level
        self.assertEqual(self.proc("csrss.exe", r"C:\Windows\System32\csrss.exe").level, L.VITAL)
        self.assertEqual(self.proc("System", pid=4).level, L.VITAL)
        self.assertEqual(self.proc("svchost.exe", r"C:\Windows\System32\svchost.exe", service=True).level, L.VITAL)
        self.assertEqual(self.proc("MsMpEng.exe", accessible=False).level, L.IMPORTANT)
        self.assertEqual(self.proc("vgc.exe", r"C:\Program Files\Riot Vanguard\vgc.exe").level, L.IMPORTANT)
        self.assertEqual(self.proc("explorer.exe", r"C:\Windows\explorer.exe").level, L.CAUTION)
        self.assertEqual(self.proc("mystery.exe", r"C:\Windows\System32\mystery.exe").level, L.IMPORTANT)
        self.assertEqual(self.proc("notepad.exe", r"C:\Windows\System32\notepad.exe").level, L.NORMAL)
        self.assertEqual(self.proc("UpdSvc.exe", r"C:\Program Files\Acme\UpdSvc.exe", service=True).level, L.CAUTION)
        self.assertEqual(self.proc("chrome.exe", r"C:\Program Files\Google\chrome.exe").level, L.NORMAL)
        for name in self.c.PROTECTED_PROCESSES:      # nada de lo que safety bloquea sale como inocuo
            self.assertGreaterEqual(self.proc(name).level, L.IMPORTANT, name)
        for name in self.c.SENSITIVE_PROCESSES:
            self.assertGreaterEqual(self.proc(name).level, L.CAUTION, name)

    def test_own_process_is_recognised(self):
        a = self.c.assess_process("SuperLimpio.exe", r"D:\Apps\SuperLimpio\SuperLimpio.exe", pid=77, self_pid=77)
        self.assertEqual((a.kind, a.level), ("self", self.c.Level.NORMAL))
        self.assertTrue(a.what and a.risk)

    def test_paths_are_ranked_by_what_breaks(self):
        L = self.c.Level
        cases = {
            "C:\\": L.VITAL, "D:\\": L.IMPORTANT, r"C:\pagefile.sys": L.IMPORTANT, r"C:\bootmgr": L.VITAL,
            r"C:\Windows": L.VITAL, r"C:\Windows\System32\drivers\ntfs.sys": L.VITAL,
            r"C:\Windows\WinSxS\x": L.VITAL, r"C:\Windows\Fonts\arial.ttf": L.IMPORTANT,
            r"C:\Windows\Temp\a.tmp": L.CAUTION, r"C:\Windows\SoftwareDistribution\Download\x": L.CAUTION,
            r"C:\Windows\SoftwareDistribution\DataStore": L.IMPORTANT,
            r"D:\System Volume Information": L.IMPORTANT, r"E:\$RECYCLE.BIN\S-1": L.IMPORTANT,
            r"C:\Program Files\Acme\acme.exe": L.IMPORTANT, r"C:\ProgramData\Acme\cfg": L.CAUTION,
            r"C:\ProgramData\Microsoft\Windows": L.IMPORTANT,
            r"C:\Users\ana": L.VITAL, r"C:\Users\ana\NTUSER.DAT": L.VITAL, r"C:\Users\ana\AppData\Local": L.IMPORTANT,
            r"C:\Users\ana\AppData\Roaming\Acme": L.CAUTION, r"C:\Users\ana\AppData\Local\Temp\x.tmp": L.NORMAL,
            r"C:\Users\ana\Documents": L.IMPORTANT, r"C:\Users\ana\Documents\carta.docx": L.NORMAL,
            r"C:\Users\ana\proyectos\x\node_modules": L.NORMAL, r"C:\Users\luis\Desktop\a.txt": L.CAUTION,
            r"C:\Users\Public": L.IMPORTANT, r"D:\Apps\SuperLimpio\app\main.py": L.IMPORTANT,
            r"D:\Juegos\partida.sav": L.NORMAL, "C:/Windows/System32/": L.VITAL,
            r"C:\pagefile.sys\x": L.NORMAL, r"D:\Windows\System32": L.NORMAL,
        }
        for path, level in cases.items():
            a = self.c.assess_path(path, env=self.ENV)
            self.assertEqual(a.level, level, path)
            self.assertTrue(a.what and a.risk, path)

    def test_only_system_files_are_flagged_as_damaging(self):
        flagged = lambda p: self.c.assess_path(p, env=self.ENV).system  # noqa: E731
        for path in ("C:\\", r"C:\Windows\System32\ntoskrnl.exe", r"C:\Windows\System32\config\SYSTEM",
                     r"C:\Windows\WinSxS\x", r"C:\Windows\Installer\a.msi", r"C:\pagefile.sys", r"C:\bootmgr",
                     r"C:\EFI\Microsoft\Boot\bootmgfw.efi", r"D:\System Volume Information",
                     r"C:\Users\ana\NTUSER.DAT", r"C:\Users\ana", r"C:\ProgramData\Microsoft\Crypto"):
            self.assertTrue(flagged(path), path)
        # importantes o delicados, pero no del sistema: no se destacan
        for path in (r"C:\Program Files\Acme\acme.exe", r"C:\ProgramData\Acme\cfg", r"C:\Users\ana\Documents",
                     r"C:\Users\ana\AppData\Roaming\Acme", r"D:\Apps\SuperLimpio\app\main.py",
                     r"C:\Users\luis\Desktop\a.txt", r"D:\Juegos\partida.sav",
                     # Windows los regenera: borrarlos no daña nada
                     r"C:\Windows\Temp\a.tmp", r"C:\Windows\SoftwareDistribution\Download\x",
                     r"C:\Windows\Prefetch\A.pf", r"E:\$RECYCLE.BIN\S-1"):
            self.assertFalse(flagged(path), path)

    def test_analysis_explains_system_processes(self):
        from superlimpio import optimizer
        from superlimpio.plat import MemoryStatus
        gb = 1024 ** 3
        procs = [
            _proc(4, "System", ppid=0, private=1 * gb),
            _proc(600, "services.exe", r"C:\Windows\System32\services.exe", ppid=4),
            _proc(700, "svchost.exe", r"C:\Windows\System32\svchost.exe", ppid=600, private=5 * gb),
            _proc(800, "game.exe", r"D:\Games\game.exe", private=6 * gb),
            _proc(900, "SuperLimpio.exe", r"D:\Apps\SuperLimpio\SuperLimpio.exe"),
        ]
        mem = MemoryStatus(total=16 * gb, available=4 * gb, load_pct=75, commit_total=20 * gb,
                           commit_available=8 * gb)
        rep = optimizer.analyze([(0.0, procs), (1.0, procs)], mem, ncpu=4, self_pid=900, windir=self.WIN)
        by = {u.name: u for u in rep.programs}
        L = self.c.Level
        self.assertEqual((by["svchost.exe"].level, by["game.exe"].level), (L.VITAL, L.NORMAL))
        self.assertTrue(by["SuperLimpio.exe"].own and not by["game.exe"].own)
        self.assertTrue(all(u.what and u.risk for u in rep.programs))
        hogs = {f.title.split()[0]: f for f in rep.findings if f.goto == "memory"}
        # al proceso vital que acapara memoria no se le aconseja lo mismo que a un programa corriente
        self.assertIn(i18n.t("opt.find.hog_system_advice"), hogs["svchost.exe"].advice)
        self.assertEqual(hogs["game.exe"].advice, i18n.t("opt.find.hog_advice"))
        self.assertTrue(any(f.title == i18n.t("opt.find.system_share", size=fmt_size(6 * gb + 100 * 1024 ** 2),
                                              pct=i18n.percent("38")) for f in rep.findings))


class SourceTests(unittest.TestCase):
    def test_every_module_compiles(self):
        # La interfaz no se importa en estas pruebas: al menos, que todo su código sea válido.
        import glob
        base = os.path.join(os.path.dirname(__file__), "..")
        files = (glob.glob(os.path.join(base, "app", "**", "*.py"), recursive=True)
                 + glob.glob(os.path.join(base, "tools", "*.py")))
        self.assertGreater(len(files), 40)
        for path in files:
            with open(path, encoding="utf-8") as fh:
                compile(fh.read(), path, "exec")


class LinuxKnowledgeTests(unittest.TestCase):
    """Las reglas de Linux son lógica pura: se prueban desde cualquier sistema."""

    ENV = {"home": "/home/ana", "users": "/home", "app_root": "/opt/apps/SuperLimpio", "mounts": ["/mnt/datos"]}
    SYS = ("/usr/lib/systemd", "/usr/libexec", "/usr/sbin")

    def setUp(self):
        from superlimpio import criticality, optimizer
        self.c, self.o = criticality, optimizer
        plat.set_knowledge("linux")
        self.addCleanup(plat.set_knowledge, "windows")

    def proc(self, name, path="", **kw):
        kw.setdefault("self_pid", 999999)
        return self.c.assess_process(name, path, windir=self.SYS, **kw)

    def test_processes_are_ranked_by_what_breaks(self):
        L = self.c.Level
        self.assertEqual(self.proc("systemd", "/usr/lib/systemd/systemd", pid=1).level, L.VITAL)
        self.assertEqual(self.proc("gnome-shell", "/usr/bin/gnome-shell").level, L.VITAL)
        self.assertEqual(self.proc("Xorg", "/usr/lib/xorg/Xorg", accessible=False).level, L.VITAL)
        self.assertEqual(self.proc("NetworkManager", "", accessible=False, service=True).level, L.IMPORTANT)
        self.assertEqual(self.proc("pipewire", "/usr/bin/pipewire").level, L.CAUTION)
        self.assertEqual(self.proc("cupsd", "", accessible=False, service=True).level, L.IMPORTANT)
        self.assertEqual(self.proc("mysqld", "", accessible=False, service=True).level, L.IMPORTANT)
        self.assertEqual(self.proc("syncthing", "/usr/bin/syncthing", service=True).level, L.CAUTION)
        self.assertEqual(self.proc("gvfsd", "/usr/libexec/gvfsd").level, L.CAUTION)
        self.assertEqual(self.proc("firefox", "/usr/lib/firefox/firefox").level, L.NORMAL)
        self.assertEqual(self.proc("code", "/usr/share/code/code").level, L.NORMAL)
        for name in plat.know.PROTECTED_PROCESSES:   # nada de lo que no se puede finalizar sale como inocuo
            self.assertGreaterEqual(self.proc(name).level, L.IMPORTANT, name)
        for name in plat.know.SENSITIVE_PROCESSES:
            self.assertGreaterEqual(self.proc(name).level, L.CAUTION, name)
        for key in {v[i] for v in plat.know.PROCESSES.values() for i in (1, 2)}:
            self.assertIn(key, i18n.CATALOG)

    def test_essential_processes_cannot_be_ended(self):
        from superlimpio.safety import Risk, check_process_kill
        self.assertFalse(check_process_kill("systemd", 1)[0])
        self.assertFalse(check_process_kill("gnome-shell", 2345)[0])
        self.assertFalse(check_process_kill("dbus-daemon", 900)[0])
        self.assertEqual(check_process_kill("plasmashell", 2345)[:2], (True, Risk.ALTO))
        self.assertTrue(check_process_kill("firefox", 3456)[0])

    def test_paths_are_ranked_by_what_breaks(self):
        L = self.c.Level
        cases = {
            "/": L.VITAL, "/mnt/datos": L.IMPORTANT, "/boot/vmlinuz": L.VITAL, "/etc/fstab": L.VITAL,
            "/usr/bin/bash": L.VITAL, "/lib/x86_64-linux-gnu/libc.so.6": L.VITAL, "/usr/lib/": L.VITAL,
            "/proc/1": L.VITAL, "/var/lib/dpkg/status": L.VITAL, "/var/lib/mysql": L.IMPORTANT,
            "/var": L.IMPORTANT, "/var/log/syslog": L.CAUTION, "/var/cache/apt/archives/x.deb": L.CAUTION,
            "/swapfile": L.IMPORTANT, "/opt/google/chrome": L.IMPORTANT, "/usr/local/bin/tool": L.IMPORTANT,
            "/snap/firefox": L.IMPORTANT, "/home": L.IMPORTANT, "/home/ana": L.VITAL,
            "/home/ana/.config": L.IMPORTANT, "/home/ana/.config/Code": L.CAUTION,
            "/home/ana/.ssh/id_ed25519": L.IMPORTANT, "/home/ana/.cache": L.CAUTION,
            "/home/ana/.cache/pip/x": L.NORMAL, "/home/ana/.bashrc": L.CAUTION,
            "/home/ana/Documents": L.IMPORTANT, "/home/ana/Documents/carta.odt": L.NORMAL,
            "/home/ana/proyectos/web/node_modules": L.NORMAL, "/home/luis/notas.txt": L.CAUTION,
            "/mnt/datos/juegos/partida.sav": L.NORMAL, "/media/ana/USB/foto.jpg": L.NORMAL,
            "/opt/apps/SuperLimpio/app/main.py": L.IMPORTANT, "/tmp/x.tmp": L.NORMAL, "/srv/web/index.html": L.NORMAL,
        }
        for path, level in cases.items():
            a = self.c.assess_path(path, env=self.ENV)
            self.assertEqual(a.level, level, path)
            self.assertTrue(a.what and a.risk, path)

    def test_only_system_files_are_flagged_as_damaging(self):
        flagged = lambda p: self.c.assess_path(p, env=self.ENV).system  # noqa: E731
        for path in ("/", "/boot/grub/grub.cfg", "/etc/passwd", "/usr/lib/libssl.so", "/bin/sh",
                     "/var/lib/dpkg/status", "/swapfile", "/home/ana", "/home/ana/.ssh/id_rsa", "/home"):
            self.assertTrue(flagged(path), path)
        for path in ("/opt/google/chrome/chrome", "/home/ana/.config/Code/settings.json", "/home/ana/Documents",
                     "/var/log/syslog", "/var/cache/apt/archives/x.deb", "/home/ana/.cache/pip/x",
                     "/home/luis/a.txt", "/mnt/datos/pelis/a.mkv", "/opt/apps/SuperLimpio/app/main.py"):
            self.assertFalse(flagged(path), path)

    def test_efficient_mode_leaves_the_system_alone(self):
        P = _proc
        procs = [
            P(1, "systemd", "/usr/lib/systemd/systemd", ppid=0),
            P(700, "NetworkManager", "", ppid=1, accessible=False),
            P(710, "syncthing", "/usr/bin/syncthing", ppid=1),
            P(900, "systemd", "/usr/lib/systemd/systemd", ppid=1),             # el de la sesión del usuario
            P(950, "gnome-shell", "/usr/bin/gnome-shell", ppid=900),
            P(960, "gvfsd", "/usr/libexec/gvfsd", ppid=900),
            P(1000, "firefox", "/usr/lib/firefox/firefox", ppid=900, private=900 * 1024 ** 2),
            P(1001, "Web Content", "/usr/lib/firefox/firefox-bin", ppid=1000),
            P(1100, "gnome-software", "/usr/bin/gnome-software", ppid=900),
            P(1200, "gedit", "/usr/bin/gedit", ppid=900),
            P(1300, "bash", "/usr/bin/bash", ppid=900),
            P(1301, "python3", "/usr/bin/python3.12", ppid=1300),               # la propia aplicación
        ]
        from superlimpio.plat import WindowInfo
        windows = [WindowInfo(5, 1000, "Mozilla Firefox"), WindowInfo(6, 1200, "sin título")]
        plan = self.o.build_plan(procs, windows, profile="program", self_pid=1301, windir=self.SYS)
        c = {x.name: x for x in plan.candidates}
        self.assertEqual(sorted(c), ["firefox", "gedit", "gnome-software"])
        self.assertEqual(c["firefox"].count, 2)                    # el navegador y su proceso hijo, juntos
        self.assertEqual(c["firefox"].category, "browser")
        self.assertEqual(c["gnome-software"].suggested, self.o.Action.CLOSE)
        self.assertEqual(c["gedit"].suggested, self.o.Action.KEEP)  # tiene ventana: no se propone nada
        # /usr/bin es de todos: que bash lance python no los convierte en el mismo programa
        self.assertEqual(plan.kept, {"system": 5, "service": 1, "self": 2})
        for cat in list(plat.know.CATALOG) + ["other"]:
            self.assertIn(f"opt.cat.{cat}", i18n.CATALOG)

    def test_platform_lists_have_their_texts(self):
        from unittest import mock
        from superlimpio.plat import linux
        ids = [c["id"] for c in linux.cleaner_categories()]
        self.assertEqual(len(ids), len(set(ids)))
        for c in linux.cleaner_categories():
            self.assertIn(f"clean.{c['id']}.name", i18n.CATALOG)
            self.assertIn(f"clean.{c['id']}.desc", i18n.CATALOG)
            self.assertIn(f"cleaner.group.{c['group']}", i18n.CATALOG)
            for path in c.get("dirs", []) + c.get("files", []):   # nunca una carpeta entera del sistema o del perfil
                self.assertGreaterEqual(path.replace("\\", "/").strip("/").count("/"), 1, path)
        with mock.patch("shutil.which", lambda name: "/usr/bin/" + name):   # como si todo estuviera instalado
            tools = linux.system_tools()
        self.assertGreater(len(tools), 5)
        for t in tools:
            for part in ("title", "desc", "effect"):
                self.assertIn(f"systool.{t['id']}.{part}", i18n.CATALOG)
        for key in i18n.CATALOG:
            if "@" in key:   # un texto propio de un sistema siempre sustituye a uno que existe
                self.assertIn(key.split("@")[0], i18n.CATALOG, key)

    def test_uninstall_goes_through_the_package_manager(self):
        from unittest import mock
        from superlimpio.plat import linux
        with mock.patch("shutil.which", lambda name: "/usr/bin/" + name):
            plan = build_uninstall_plan(Program(name="GIMP", scope="deb", reg_key="gimp"), linux.uninstall_command)
            self.assertEqual(plan.display, "sudo apt-get remove gimp")
            self.assertTrue(plan.exe and "sudo apt-get remove gimp" in plan.params)
            plan = build_uninstall_plan(Program(name="X", scope="flatpak", reg_key="org.x.App; rm -rf ~"),
                                        linux.uninstall_command)
            self.assertEqual(plan.display, "flatpak uninstall 'org.x.App; rm -rf ~'")   # entrecomillado: no se ejecuta
        plan = build_uninstall_plan(Program(name="Suelto", scope="user_app", reg_key="/home/ana/x.desktop"),
                                    linux.uninstall_command)
        self.assertEqual(plan.exe, "")                              # sin paquete no hay nada que lanzar
        self.assertTrue(plan.warnings)


@unittest.skipUnless(sys.platform.startswith("linux"), "llamadas reales al sistema: solo en Linux")
class LinuxPlatformTests(unittest.TestCase):
    def setUp(self):
        from superlimpio.plat import linux
        self.lx = linux

    def test_processes_and_memory_are_read_from_proc(self):
        procs = {p.pid: p for p in self.lx.list_processes()}
        me = procs[os.getpid()]
        self.assertTrue(me.accessible and me.path and me.private > 0 and me.threads >= 1)
        self.assertIn("python", me.name.lower())
        self.assertNotIn(2, procs)                                   # los hilos del núcleo no se listan
        self.assertTrue(self.lx.process_alive(me.pid, me.create_time))
        self.assertFalse(self.lx.process_alive(me.pid, me.create_time + 50))   # mismo PID, otro proceso
        mem = self.lx.memory_status()
        self.assertTrue(mem.total > mem.available > 0)
        perf = self.lx.performance_info()
        self.assertGreater(perf.processes, 1)
        self.assertEqual(self.lx.list_drives()[0], "/")

    def test_ending_a_process_checks_it_is_still_the_same(self):
        import subprocess
        child = subprocess.Popen(["sleep", "60"])
        try:
            info = next(p for p in self.lx.list_processes() if p.pid == child.pid)
            self.assertEqual(info.name, "sleep")
            ok, _msg = self.lx.terminate_process(child.pid, info.create_time + 50)
            self.assertFalse(ok)                                     # no es el que se analizó: no se toca
            self.assertIsNone(child.poll())
            ok, _msg, prev = self.lx.set_efficiency(child.pid, info.create_time)
            self.assertTrue(ok)
            self.assertEqual(os.getpriority(os.PRIO_PROCESS, child.pid), 10)
            self.assertEqual(prev, plat.PRIORITY_NORMAL)
            ok, _msg = self.lx.terminate_process(child.pid, info.create_time)
            self.assertTrue(ok)
            child.wait(timeout=5)
        finally:
            if child.poll() is None:
                child.kill()

    def test_trash_follows_the_freedesktop_layout(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "datos")
            victim = os.path.join(tmp, "trabajo", "informe ñ.txt")
            folder = os.path.join(tmp, "trabajo", "carpeta")
            _write(victim, 1234)
            _write(os.path.join(folder, "a.bin"), 100)
            with mock.patch.dict(os.environ, {"XDG_DATA_HOME": data}):
                ok, msg = self.lx.send_to_recycle_bin([victim, folder])
                self.assertTrue(ok, msg)
                self.assertFalse(os.path.exists(victim) or os.path.exists(folder))
                trash = os.path.join(data, "Trash")
                self.assertEqual(sorted(os.listdir(os.path.join(trash, "files"))), ["carpeta", "informe ñ.txt"])
                info = open(os.path.join(trash, "info", "informe ñ.txt.trashinfo"), encoding="utf-8").read()
                self.assertTrue(info.startswith("[Trash Info]\nPath="))
                self.assertIn("informe%20%C3%B1.txt", info)
                self.assertIn("DeletionDate=", info)
                size, count = self.lx.recycle_bin_info()
                self.assertEqual((size, count), (1334, 2))
                _write(victim, 5)                                    # otro con el mismo nombre no pisa al primero
                self.assertTrue(self.lx.send_to_recycle_bin([victim])[0])
                self.assertEqual(len(os.listdir(os.path.join(trash, "files"))), 3)
                ok, _msg = self.lx.send_to_recycle_bin([os.path.join(tmp, "no existe")])
                self.assertFalse(ok)
                self.assertTrue(self.lx.empty_recycle_bin()[0])
                self.assertEqual(self.lx.recycle_bin_info(), (0, 0))

    def test_system_paths_cannot_be_deleted(self):
        home = os.path.expanduser("~")
        for path in ("/", "/usr", "/usr/bin/python3", "/etc/passwd", "/boot", "/var/lib/dpkg", "/home", home,
                     os.path.join(home, ".config"), os.path.join(home, ".ssh"), "/opt", "/var/log/syslog"):
            self.assertFalse(check_deletable(path).allowed, path)
        for path in (os.path.join(home, "proyectos", "viejo"), os.path.join(home, ".cache", "pip", "x"),
                     os.path.join(home, ".config", "Code", "Cache"), "/mnt/datos/pelis/a.mkv"):
            self.assertTrue(check_deletable(path).allowed, path)

    def test_lists_of_the_system_do_not_fail(self):
        from superlimpio import programs, startup, systools
        self.assertIsInstance(programs.list_installed(), list)
        self.assertIsInstance(startup.list_startup(), list)
        self.assertIsInstance(systools.tools(), list)
        self.assertTrue(cleaner.default_categories())
        caps = plat.capabilities()
        self.assertFalse(caps["elevate"] or caps["trim"])

    def test_desktop_entries_are_read_without_running_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = os.path.join(tmp, "x.desktop")
            with open(entry, "w", encoding="utf-8") as fh:
                fh.write("[Desktop Entry]\nType=Application\nName=Editor\nName[es]=Editor de textos\n"
                         "Exec=env LANG=C /bin/sh -c 'echo hola' %U\nHidden=false\n\n[Otra sección]\nExec=/bin/false\n")
            d = self.lx._desktop_entry(entry)
            self.assertEqual((d["Name"], d["Name[es]"], d["Type"]), ("Editor", "Editor de textos", "Application"))
            self.assertEqual(self.lx._exec_program(d["Exec"]), "/bin/sh")
            self.assertEqual(self.lx._exec_program("no-existe-este-programa --x"), "")


if __name__ == "__main__":
    unittest.main()
