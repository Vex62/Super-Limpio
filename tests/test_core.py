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

from superlimpio import cleaner, devdeps, i18n, scanner  # noqa: E402
from superlimpio.programs import Program, build_uninstall_plan, split_command  # noqa: E402
from superlimpio.safety import check_deletable  # noqa: E402
from superlimpio.util import fmt_size, text_bar  # noqa: E402


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
        plan = build_uninstall_plan(p)
        self.assertIn("/X{11111111", plan.params)
        p2 = Program(name="Y", msi_code="{11111111-2222-3333-4444-555555555555}")
        self.assertEqual(build_uninstall_plan(p2).params, "/x {11111111-2222-3333-4444-555555555555}")


class ElevationTests(unittest.TestCase):
    def test_launcher_needs_no_script(self):
        from unittest import mock
        from superlimpio import winapi
        with mock.patch.object(sys, "executable", r"E:\SuperLimpio\SuperLimpio.exe"):
            self.assertEqual(winapi.admin_command(r"E:\SuperLimpio\app\main.py"),
                             (r"E:\SuperLimpio\SuperLimpio.exe", ""))

    def test_python_gets_the_script(self):
        from unittest import mock
        from superlimpio import winapi
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


if __name__ == "__main__":
    unittest.main()
