"""Tests de seguridad: los que exige la ficha «Seguridad y Safe Coding en Python» para el
código que borra, limpia o se eleva. Cada uno reproduce un fallo que la revisión encontró.

Ejecutar:  runtime\\python\\python.exe -B -m unittest discover -s tests -v
"""

import hashlib
import json
import os
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from superlimpio import cleaner, config, fileops, helper, integrity, plat, safety, scanner  # noqa: E402
from superlimpio.plat import linux_know, windows_know  # noqa: E402
from superlimpio.processes import ProcInfo, group_by_program  # noqa: E402
from superlimpio.safety import check_clean_root, check_deletable  # noqa: E402
from superlimpio.util import APP_ROOT, long_path  # noqa: E402

WINDOWS = sys.platform == "win32"
_state = {}


def setUpModule():
    # El registro de acciones de las pruebas va a una carpeta temporal, no al del usuario.
    _state["tmp"] = tempfile.TemporaryDirectory()
    _state["log_dir"] = safety.LOG_DIR
    safety.LOG_DIR = Path(_state["tmp"].name) / "logs"


def tearDownModule():
    safety.close_log()
    safety.LOG_DIR = _state["log_dir"]
    _state["tmp"].cleanup()


def _write(path, size=1):
    os.makedirs(long_path(os.path.dirname(path)), exist_ok=True)
    with open(long_path(path), "wb") as fh:
        fh.write(b"x" * size)


def _link_dir(target, link):
    """Enlace a una carpeta que cualquier usuario puede crear: junction en Windows, enlace
    simbólico en Linux. (_winapi es interno de CPython: solo para pruebas.)"""
    if WINDOWS:
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(target, link, target_is_directory=True)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = os.path.realpath(self._tmp.name)

    def tree_with_link(self):
        """«base» contiene un enlace a «fuera», que tiene un archivo que no debe borrarse."""
        outside = os.path.join(self.tmp, "fuera")
        _write(os.path.join(outside, "no_borrar.txt"))
        base = os.path.join(self.tmp, "base")
        _write(os.path.join(base, "dentro.txt"))
        _link_dir(outside, os.path.join(base, "enlace"))
        return base, os.path.join(outside, "no_borrar.txt")


# =========================================================================
# FS-01 / FS-07 / FS-11: contención y rutas protegidas
# =========================================================================

class ContainmentTests(_Tmp):
    def test_dotdot_that_leaves_the_base_is_rejected(self):
        sneaky = os.path.join(self.tmp, "a", "..", "..", "..", "..", "..", "..", "..", "..", "..")
        self.assertFalse(check_deletable(sneaky).allowed)                       # acaba en la raíz del disco
        inside_app = os.path.join(str(APP_ROOT), "tests", "..", "app", "main.py")
        self.assertFalse(check_deletable(inside_app).allowed)

    def test_prefix_is_not_containment(self):
        # «…/SuperLimpio2» empieza por «…/SuperLimpio» pero no está dentro: no se bloquea por eso
        sibling = str(APP_ROOT) + "2"
        self.assertTrue(safety._inside(safety.norm_key(str(APP_ROOT / "app")), safety.norm_key(str(APP_ROOT))))
        self.assertFalse(safety._inside(safety.norm_key(sibling), safety.norm_key(str(APP_ROOT))))

    def test_path_through_a_link_is_resolved(self):
        link = os.path.join(self.tmp, "atajo")
        _link_dir(str(APP_ROOT / "app"), link)
        # A través del enlace se llega a la carpeta protegida: se bloquea…
        self.assertFalse(check_deletable(os.path.join(link, "main.py")).allowed)
        self.assertFalse(check_deletable(os.path.join(link, "superlimpio")).allowed)
        # …pero el enlace en sí es del usuario y se puede quitar (sin tocar su destino).
        self.assertTrue(check_deletable(link).allowed)
        ok, msg = fileops.delete_permanently([link])
        self.assertTrue(ok, msg)
        self.assertFalse(os.path.lexists(link))
        self.assertTrue((APP_ROOT / "app" / "main.py").exists())

    @unittest.skipUnless(WINDOWS, "formas de escribir una ruta propias de Windows")
    def test_protected_paths_however_they_are_written(self):
        import ctypes
        windir = os.environ["WINDIR"]
        pf = os.environ["ProgramFiles"]
        buf = ctypes.create_unicode_buffer(260)
        ctypes.WinDLL("kernel32", winmode=0x800).GetShortPathNameW(pf, buf, 260)
        spellings = [
            windir.upper(), windir.lower(), windir.replace("\\", "/"),          # capitalización y barras
            os.path.join(windir, "System32", "..", "System32", "drivers"),      # con «..»
            "\\\\?\\" + windir, "\\\\?\\" + os.path.join(pf, "Common Files"),    # prefijo de ruta larga
            f"\\\\localhost\\{windir[0]}$" + windir[2:],                        # recurso administrativo local
            f"\\\\127.0.0.1\\{windir[0]}$" + windir[2:] + "\\System32",
            f"\\\\otro-equipo\\{windir[0]}$\\Windows",                           # y el de otro equipo
            "\\\\.\\" + windir,                                                 # espacio de dispositivos
            os.path.join(os.path.dirname(os.environ["USERPROFILE"]), "All Users", "Microsoft"),   # enlace a ProgramData
        ]
        if buf.value and buf.value.lower() != pf.lower():
            spellings += [buf.value, os.path.join(buf.value, "Common Files")]   # nombre corto 8.3 (PROGRA~1)
        for path in spellings:
            self.assertFalse(check_deletable(path).allowed, path)

    def test_reserved_names_and_alternate_streams(self):
        problem = windows_know.name_problem
        for name in ("CON", "con.txt", "NUL", "aux.tar.gz", "COM1", "lpt9.log", "PRN."):
            self.assertEqual(problem("C:\\datos\\" + name), "reserved", name)
        self.assertEqual(problem(r"C:\datos\nota.txt:oculto"), "ads")
        self.assertEqual(problem(r"C:\datos\x::$DATA"), "ads")
        for name in ("consola.txt", "com10", "nulo", "a.con", "informe final.docx"):
            self.assertEqual(problem("C:\\datos\\" + name), "", name)
        if WINDOWS:
            self.assertFalse(check_deletable(os.path.join(self.tmp, "nota.txt:oculto")).allowed)
            self.assertFalse(check_deletable(os.path.join(self.tmp, "aux.txt")).allowed)

    def test_canonical_form_of_windows_paths(self):
        canon = windows_know.canonical
        self.assertEqual(canon("\\\\?\\C:\\Windows"), "C:\\Windows")
        self.assertEqual(canon("C:/Windows/System32/../Temp"), "C:\\Windows\\Temp")
        self.assertEqual(canon("\\\\localhost\\c$\\Windows"), "C:\\Windows")
        self.assertEqual(canon("\\\\?\\UNC\\servidor\\datos\\x"), "\\\\servidor\\datos\\x")
        for device in ("\\\\.\\C:\\Windows", "\\\\?\\Volume{0000}\\Windows", "\\\\?\\GLOBALROOT\\Device\\x",
                       "\\\\servidor\\C$\\Windows"):
            self.assertIsNone(canon(device), device)

    def test_other_users_profiles_are_protected(self):
        env = {"users": r"C:\Users", "profile": r"C:\Users\Ana"}
        foreign = lambda p: windows_know.foreign_profile(windows_know.norm(p), env)   # noqa: E731
        self.assertTrue(foreign(r"C:\Users\Luis"))
        self.assertTrue(foreign(r"C:\Users\luis\Documents\carta.docx"))
        self.assertTrue(foreign(r"C:\Users\Default\NTUSER.DAT"))
        self.assertFalse(foreign(r"C:\Users\ana\proyectos\viejo"))
        self.assertFalse(foreign(r"C:\Users\Public\Videos\a.mp4"))
        self.assertFalse(foreign(r"D:\Users\Luis"))
        lenv = {"home": "/home/ana", "users": "/home"}
        lforeign = lambda p: linux_know.foreign_profile(linux_know.norm(p), lenv)   # noqa: E731
        self.assertTrue(lforeign("/home/luis"))
        self.assertTrue(lforeign("/home/luis/fotos/a.jpg"))
        self.assertFalse(lforeign("/home/ana/proyectos"))
        self.assertFalse(lforeign("/srv/datos"))
        root_env = {"home": "/root", "users": "/"}
        self.assertTrue(linux_know.foreign_profile("/home/ana/x", root_env))
        self.assertFalse(linux_know.foreign_profile("/srv/x", root_env))

    @unittest.skipUnless(sys.platform.startswith("linux"), "puntos de montaje de Linux")
    def test_a_mounted_disk_root_is_a_drive_root(self):
        with mock.patch.object(safety.os.path, "ismount", lambda p: os.path.basename(p) == "USB"):
            usb = os.path.join(self.tmp, "USB")
            os.makedirs(os.path.join(usb, "fotos"))
            self.assertFalse(check_deletable(usb).allowed)                     # el disco entero, no
            self.assertTrue(check_deletable(os.path.join(usb, "fotos")).allowed)   # lo que hay dentro, sí


# =========================================================================
# FS-02 / FS-03 / FS-05 / ERR-03 / CON-03: borrado
# =========================================================================

class DeleteTests(_Tmp):
    def test_link_inside_the_tree_is_not_followed(self):
        base, keep = self.tree_with_link()
        ok, msg = fileops.delete_permanently([base])
        self.assertTrue(ok, msg)
        self.assertFalse(os.path.lexists(base))
        self.assertTrue(os.path.exists(keep))            # el destino del enlace sigue entero

    def test_awkward_names(self):
        names = [" espacios al principio", "acentos áéíñ ç", "emoji 🧹✨", "-empieza-por-guion",
                 "amp & punto;coma $dolar", "100% (copia) [2]", "punto.final.txt"]
        if not WINDOWS:
            names += ["salto\nde línea", "dos:puntos", "espacio al final "]
        paths = []
        for name in names:
            paths.append(os.path.join(self.tmp, name))
            _write(os.path.join(paths[-1], "x.bin"), 3)
        ok, msg = fileops.delete_permanently(paths)
        self.assertTrue(ok, msg)
        self.assertEqual(os.listdir(self.tmp), [])

    def test_empty_folder_and_empty_file(self):
        empty_dir = os.path.join(self.tmp, "vacía")
        os.makedirs(empty_dir)
        empty_file = os.path.join(self.tmp, "cero.bin")
        _write(empty_file, 0)
        ok, msg = fileops.delete_permanently([empty_dir, empty_file])
        self.assertTrue(ok, msg)
        self.assertEqual(os.listdir(self.tmp), [])

    def test_deep_and_wide_trees(self):
        deep = os.path.join(self.tmp, "hondo")
        cur = deep
        for i in range(60):                              # 60 niveles: sin recursión, no se desborda nada
            cur = os.path.join(cur, f"n{i}")
        _write(os.path.join(cur, "fondo.txt"))
        wide = os.path.join(self.tmp, "ancho")
        os.makedirs(wide)
        for i in range(3000):
            with open(os.path.join(wide, f"f{i}"), "wb"):
                pass
        self.assertEqual(scanner.scan(wide).root.files, 3000)
        self.assertEqual(scanner.scan(deep).root.files, 1)
        ok, msg = fileops.delete_permanently([deep, wide])
        self.assertTrue(ok, msg)
        self.assertEqual(os.listdir(self.tmp), [])

    def test_path_that_vanished_is_not_a_failure(self):
        here = os.path.join(self.tmp, "sigue.txt")
        _write(here)
        ok, msg = fileops.delete_permanently([os.path.join(self.tmp, "ya_no_esta.txt"), here])
        self.assertTrue(ok, msg)                         # el lote sigue y no se inventa un error
        self.assertFalse(os.path.exists(here))
        self.assertIn("1", msg)                          # …pero el resumen dice que uno ya no existía

    def test_read_only_items_are_deleted(self):
        folder = os.path.join(self.tmp, "solo_lectura")
        target = os.path.join(folder, "fijo.txt")
        _write(target)
        os.chmod(target, stat.S_IREAD)
        ok, msg = fileops.delete_permanently([folder])
        self.assertTrue(ok, msg)
        self.assertFalse(os.path.exists(folder))

    def test_locked_item_fails_and_the_batch_goes_on(self):
        stuck = os.path.join(self.tmp, "ocupado")
        _write(os.path.join(stuck, "abierto.txt"))
        free = os.path.join(self.tmp, "libre.txt")
        _write(free)
        if WINDOWS:
            holder = open(os.path.join(stuck, "abierto.txt"), "rb")   # Windows no deja borrar un archivo abierto
            self.addCleanup(holder.close)
        else:
            if os.geteuid() == 0:
                self.skipTest("root puede borrar en carpetas sin permiso")
            os.chmod(stuck, 0o500)                       # carpeta sin permiso de escritura
            self.addCleanup(os.chmod, stuck, 0o700)
        ok, msg = fileops.delete_permanently([stuck, free])
        self.assertFalse(ok)                             # no dice «todo eliminado» si algo falló
        self.assertIn("abierto.txt", msg)
        self.assertTrue(os.path.exists(os.path.join(stuck, "abierto.txt")))
        self.assertFalse(os.path.exists(free))           # lo demás del lote sí se borró

    def test_blocked_path_stops_the_whole_batch(self):
        mine = os.path.join(self.tmp, "mio.txt")
        _write(mine)
        ok, _msg = fileops.delete_permanently([mine, str(APP_ROOT / "app")])
        self.assertFalse(ok)
        self.assertTrue(os.path.exists(mine))            # con algo protegido en la lista no se toca nada
        ok, _msg = fileops.recycle([mine, str(APP_ROOT / "app")])
        self.assertFalse(ok)
        self.assertTrue(os.path.exists(mine))

    def test_cancel_in_the_middle_leaves_a_coherent_state(self):
        paths = [os.path.join(self.tmp, f"f{i}.txt") for i in range(4)]
        for p in paths:
            _write(p)

        class StopAfter:
            """Se «pulsa Detener» cuando ya se han mirado dos elementos."""
            calls = 0

            def is_set(self):
                self.calls += 1
                return self.calls > 2

        ok, msg = fileops.delete_permanently(paths, StopAfter())
        self.assertFalse(ok)
        self.assertEqual([os.path.exists(p) for p in paths], [False, False, True, True])
        self.assertIn("2", msg)                          # el resumen dice cuántos se borraron de verdad
        stop = threading.Event()
        stop.set()
        self.assertFalse(fileops.recycle(paths[2:], stop)[0])
        self.assertTrue(all(os.path.exists(p) for p in paths[2:]))

    def test_long_paths(self):
        top = os.path.join(self.tmp, "largo")
        cur = top
        while len(cur) < 300:                            # más de 260 caracteres de ruta
            cur = os.path.join(cur, "carpeta-con-un-nombre-bastante-largo")
        try:
            os.makedirs(long_path(cur))
            with open(long_path(os.path.join(cur, "al_fondo.txt")), "wb") as fh:
                fh.write(b"x" * 7)
        except OSError:
            self.skipTest("este sistema de archivos no admite rutas tan largas")
        found = scanner.scan(top)
        self.assertEqual((found.root.files, found.root.size, found.errors), (1, 7, 0))
        ok, msg = fileops.delete_permanently([top])
        self.assertTrue(ok, msg)
        self.assertFalse(os.path.lexists(top))

    def test_component_longer_than_the_limit_is_an_error_not_a_crash(self):
        too_long = os.path.join(self.tmp, "ñ" * 300)      # 600 bytes en UTF-8: ningún sistema lo admite
        ok, msg = fileops.delete_permanently([too_long])   # según el sistema: «ya no estaba» o un error claro
        self.assertTrue(ok or "ñ" in msg, msg)
        self.assertEqual(scanner.scan(self.tmp).root.files, 0)


# =========================================================================
# Limpieza: las ubicaciones se comprueban y los enlaces no se siguen
# =========================================================================

class CleanerSafetyTests(_Tmp):
    def _cat(self, **kw):
        return cleaner.Category("t", "Test", "Test", "", **kw)

    def test_root_that_is_a_link_is_refused(self):
        outside = os.path.join(self.tmp, "fuera")
        _write(os.path.join(outside, "no_borrar.txt"))
        cache = os.path.join(self.tmp, "cache")
        _link_dir(outside, cache)
        cat = self._cat(dirs=[cache])
        est = cleaner.analyze(cat)
        self.assertEqual((est.count, len(est.refused)), (0, 1))
        res = cleaner.clean(cat)
        self.assertEqual((res.deleted, len(res.refused)), (0, 1))
        self.assertTrue(os.path.exists(os.path.join(outside, "no_borrar.txt")))

    def test_link_inside_is_not_followed(self):
        base, keep = self.tree_with_link()
        res = cleaner.clean(self._cat(dirs=[base]))
        self.assertEqual(res.deleted, 1)                 # solo «dentro.txt»
        self.assertTrue(os.path.exists(keep))
        self.assertTrue(os.path.lexists(os.path.join(base, "enlace")))   # el enlace tampoco se quita

    def test_wide_locations_are_refused(self):
        home = os.path.expanduser("~")
        for path in (home, os.path.dirname(home), os.path.abspath(os.sep), str(APP_ROOT), str(APP_ROOT.parent),
                     str(APP_ROOT / "app")):
            chk, _real = check_clean_root(path)
            self.assertFalse(chk.allowed, path)
        chk, real = check_clean_root(self.tmp)
        self.assertTrue(chk.allowed, chk.reason)
        self.assertEqual(os.path.normcase(real), os.path.normcase(self.tmp))

    def test_environment_cannot_point_the_cleaner_at_the_profile(self):
        from superlimpio.plat import windows as winapi
        local = r"C:\Users\Ana\AppData\Local"
        for bad in (r"C:\Users\Ana", "C:\\", r"C:\Users\Ana\Documents", "Temp", r"..\Temp", ""):
            with mock.patch.dict(os.environ, {"TEMP": bad, "TMP": bad}):
                self.assertEqual(winapi._temp_dir(local), local + r"\Temp", bad)
        with mock.patch.dict(os.environ, {"TEMP": r"D:\Temp"}):
            self.assertEqual(winapi._temp_dir(local), r"D:\Temp")
        # Una variable sin definir no se convierte en una ruta relativa a la carpeta actual
        self.assertEqual(cleaner._matches("%SUPERLIMPIO_NO_EXISTE%" + os.sep + "cache"), [])
        self.assertEqual(cleaner._matches(os.path.join("cache", "*")), [])

    def test_xdg_variables_must_be_absolute(self):
        from superlimpio.plat import linux
        with mock.patch.object(linux, "_home", lambda: "/home/ana"):
            for bad in ("", "cache", "../x", "~/cache"):
                with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": bad}):
                    self.assertEqual(linux._xdg("XDG_CACHE_HOME", ".cache").replace("\\", "/"), "/home/ana/.cache")
        absolute = os.path.abspath(os.sep + "datos")
        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": absolute}):
            self.assertEqual(linux._xdg("XDG_CACHE_HOME", ".cache"), os.path.normpath(absolute))

    def test_cancel_also_stops_loose_files(self):
        loose = os.path.join(self.tmp, "suelto.dmp")
        _write(loose)
        stop = threading.Event()
        stop.set()
        res = cleaner.clean(self._cat(files=[os.path.join(self.tmp, "*.dmp")]), stop)
        self.assertTrue(res.cancelled)
        self.assertTrue(os.path.exists(loose))           # detenido: no se borra nada más
        res = cleaner.clean(self._cat(files=[os.path.join(self.tmp, "*.dmp")]))
        self.assertEqual((res.deleted, os.path.exists(loose)), (1, False))

    def test_loose_file_that_is_a_link_is_left_alone(self):
        target = os.path.join(self.tmp, "fuera", "valioso.dmp")
        _write(target)
        folder = os.path.join(self.tmp, "volcados")
        os.makedirs(folder)
        try:
            os.symlink(target, os.path.join(folder, "enlace.dmp"))
        except (OSError, NotImplementedError):
            self.skipTest("sin permiso para crear enlaces simbólicos")
        res = cleaner.clean(self._cat(files=[os.path.join(folder, "*.dmp")]))
        self.assertEqual(res.deleted, 0)
        self.assertTrue(os.path.exists(target))

    def test_empty_subfolders_go_but_the_root_stays(self):
        root = os.path.join(self.tmp, "cache")
        _write(os.path.join(root, "a", "b", "c.tmp"), 5)
        _write(os.path.join(root, "d.tmp"), 5)
        res = cleaner.clean(self._cat(dirs=[root]))
        self.assertEqual((res.deleted, res.freed, res.failed), (2, 10, 0))
        self.assertEqual(os.listdir(root), [])

    @unittest.skipIf(WINDOWS, "en Windows scandir no informa de enlaces duros ni distingue mayúsculas")
    def test_hard_links_count_once_and_case_matters(self):
        base = os.path.join(self.tmp, "datos")
        _write(os.path.join(base, "uno.bin"), 1000)
        os.link(os.path.join(base, "uno.bin"), os.path.join(base, "otro_nombre.bin"))
        _write(os.path.join(base, "Informe.txt"), 10)
        _write(os.path.join(base, "informe.txt"), 20)     # distinto archivo: Linux distingue mayúsculas
        found = scanner.scan(base)
        self.assertEqual((found.root.files, found.root.size), (3, 1030))
        self.assertEqual(scanner.quick_folder_size(base), (1030, 3))

    @unittest.skipUnless(sys.platform.startswith("linux"), "sistemas de archivos virtuales de Linux")
    def test_virtual_filesystems_are_not_scanned(self):
        for path in ("/proc", "/sys/kernel", "/dev"):
            with self.assertRaises(OSError):
                scanner.scan(path)
        root_scan = scanner.scan("/proc/..", workers=2, cancel=_cancelled())
        self.assertTrue(root_scan.cancelled)


def _cancelled():
    ev = threading.Event()
    ev.set()
    return ev


# =========================================================================
# PRV-01/02/03: el auxiliar elevado solo hace órdenes previstas y lo revalida todo
# =========================================================================

class HelperTests(_Tmp):
    def _run(self, order, digest=None):
        data = json.dumps(order).encode("utf-8")
        request = os.path.join(self.tmp, "orden.json")
        with open(request, "wb") as fh:
            fh.write(data)
        code = helper.main(["--auxiliar", request, "--sha256", digest or hashlib.sha256(data).hexdigest()])
        with open(request + helper.RESULT_SUFFIX, encoding="utf-8") as fh:
            return code, json.load(fh)

    def test_only_known_orders_with_the_exact_shape(self):
        good = helper.delete_order([os.path.join(self.tmp, "x")])
        self.assertEqual(helper.parse_order(json.dumps(good).encode()), good)
        bad = [
            b"no es json", b"[]", b'{"v": 2, "order": "clean", "categories": ["temp_win"]}',
            json.dumps({"v": 1, "order": "run", "command": "cmd.exe /c del"}).encode(),
            json.dumps({"v": 1, "order": "clean", "categories": ["temp_win"], "dirs": ["C:\\"]}).encode(),
            json.dumps({"v": 1, "order": "clean", "categories": ["../x"]}).encode(),
            json.dumps({"v": 1, "order": "clean", "categories": []}).encode(),
            json.dumps({"v": 1, "order": "delete", "paths": ["relativa\\x"]}).encode(),
            json.dumps({"v": 1, "order": "delete", "paths": [5]}).encode(),
            json.dumps({"v": 1, "order": "delete", "paths": "C:\\x"}).encode(),
            json.dumps({"v": 1, "order": "delete", "paths": [os.path.join(self.tmp, "a\0b")]}).encode(),
        ]
        for data in bad:
            with self.assertRaises(helper.OrderError, msg=data):
                helper.parse_order(data)

    def test_cleaning_is_limited_to_admin_categories(self):
        user_cats = [c.id for c in cleaner.default_categories() if not c.admin or c.special]
        self.assertTrue(user_cats)
        with self.assertRaises(helper.OrderError):       # ni las del usuario ni la Papelera ni inventadas
            helper.execute(helper.clean_order([user_cats[0]]))
        with self.assertRaises(helper.OrderError):
            helper.execute(helper.clean_order(["no_existe"]))

    def test_order_must_match_its_fingerprint(self):
        victim = os.path.join(self.tmp, "victima.txt")
        _write(victim)
        code, result = self._run(helper.delete_order([victim]), digest="0" * 64)
        self.assertEqual(code, helper.EXIT_REJECTED)
        self.assertTrue(result["rejected"])
        self.assertTrue(os.path.exists(victim))          # una orden cambiada por el camino no se ejecuta

    def test_paths_are_validated_again_by_the_helper(self):
        mine = os.path.join(self.tmp, "mio.txt")
        _write(mine)
        code, result = self._run(helper.delete_order([mine, str(APP_ROOT / "app")]))
        self.assertEqual(code, helper.EXIT_PARTIAL)
        self.assertFalse(result["ok"])
        self.assertTrue(os.path.exists(mine) and (APP_ROOT / "app" / "main.py").exists())
        os.remove(os.path.join(self.tmp, "orden.json" + helper.RESULT_SUFFIX))
        code, result = self._run(helper.delete_order([mine]))
        self.assertEqual((code, result["ok"], os.path.exists(mine)), (helper.EXIT_OK, True, False))

    def test_result_file_is_never_overwritten(self):
        mine = os.path.join(self.tmp, "mio.txt")
        _write(mine)
        planted = os.path.join(self.tmp, "orden.json" + helper.RESULT_SUFFIX)
        with open(planted, "w", encoding="utf-8") as fh:
            fh.write("contenido ajeno")
        data = json.dumps(helper.delete_order([mine])).encode("utf-8")
        with open(os.path.join(self.tmp, "orden.json"), "wb") as fh:
            fh.write(data)
        helper.main(["--auxiliar", os.path.join(self.tmp, "orden.json"), "--sha256", hashlib.sha256(data).hexdigest()])
        with open(planted, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "contenido ajeno")

    def test_missing_arguments_do_nothing(self):
        self.assertEqual(helper.main(["--auxiliar"]), helper.EXIT_REJECTED)
        self.assertEqual(helper.main(["--auxiliar", os.path.join(self.tmp, "no_existe.json")]), helper.EXIT_REJECTED)



class HelperWindowSideTests(_Tmp):
    """El lado de la ventana: escribe la orden, lanza el auxiliar y lee su resultado. Aquí el
    «aviso UAC» se sustituye por ejecutar el auxiliar en este mismo proceso."""

    def _fake_elevation(self, answer=None):
        def run_elevated(exe, params, timeout=3600.0):
            if answer is not None:
                return answer
            args = __import__("shlex").split(params.replace("\\", "/"))
            request = args[args.index("--auxiliar") + 1]
            digest = args[args.index("--sha256") + 1]
            return True, "ok", helper.main(["--auxiliar", request, "--sha256", digest])
        return mock.patch.multiple(
            plat, run_elevated=run_elevated, state_dir=lambda: self.tmp,
            helper_command=lambda script, request, digest: ("exe", f'--auxiliar "{request}" --sha256 {digest}'))

    def test_round_trip(self):
        victim = os.path.join(self.tmp, "victima.txt")
        _write(victim)
        with self._fake_elevation():
            result = helper.run(helper.delete_order([victim]))
        self.assertEqual((result["ok"], result["launched"], os.path.exists(victim)), (True, True, False))
        self.assertEqual(os.listdir(os.path.join(self.tmp, "ordenes")), [])     # ni la orden ni el resultado quedan

    def test_declined_prompt_does_nothing(self):
        victim = os.path.join(self.tmp, "victima.txt")
        _write(victim)
        with self._fake_elevation(answer=(False, "rechazado", -1)):
            result = helper.run(helper.delete_order([victim]))
        self.assertEqual((result["ok"], result["launched"], result["msg"]), (False, False, "rechazado"))
        self.assertTrue(os.path.exists(victim))
        with self._fake_elevation(answer=(True, "ok", 0)):                       # «terminó» sin dejar resultado
            result = helper.run(helper.delete_order([victim]))
        self.assertFalse(result["ok"])
        self.assertTrue(os.path.exists(victim))

    def test_window_never_sends_a_malformed_order(self):
        with self._fake_elevation(), self.assertRaises(helper.OrderError):
            helper.run({"v": 1, "order": "delete", "paths": ["relativa"]})
        self.assertIn("--auxiliar", helper.describe(helper.clean_order(["temp_win"])))


class RecycleAndAnalyzeTests(_Tmp):
    def test_recycle_skips_what_is_gone_and_reports_it(self):
        here = os.path.join(self.tmp, "a.txt")
        _write(here)
        sent = []
        with mock.patch.object(plat, "send_to_recycle_bin", lambda paths: (sent.extend(paths), (True, "enviado"))[1]):
            ok, msg = fileops.recycle([here, os.path.join(self.tmp, "ya_no.txt")])
        self.assertTrue(ok)
        self.assertEqual(sent, [here])                   # lo que ya no existe no se manda (y no tumba el lote)
        self.assertIn("1", msg)

    def test_analysis_touches_nothing_and_reports_refusals(self):
        root = os.path.join(self.tmp, "cache")
        _write(os.path.join(root, "a.tmp"), 10)
        _write(os.path.join(self.tmp, "volcado.dmp"), 5)
        link = os.path.join(self.tmp, "enlace")
        _link_dir(os.path.join(self.tmp, "cache"), link)
        cat = cleaner.Category("t", "T", "T", "", dirs=[root, link], files=[os.path.join(self.tmp, "*.dmp")])
        est = cleaner.analyze(cat)
        self.assertEqual((est.size, est.count, len(est.refused)), (15, 2, 1))
        self.assertTrue(est.note)
        self.assertTrue(os.path.exists(os.path.join(root, "a.tmp")))
        res = cleaner.clean(cat)
        self.assertEqual((res.deleted, res.freed, len(res.refused)), (2, 15, 1))
        self.assertTrue(os.path.lexists(link))

    def test_recycle_bin_category(self):
        cat = cleaner.Category("recycle", "T", "Papelera", "", special="recycle_bin")
        with mock.patch.object(plat, "recycle_bin_info", lambda: (1234, 3)),                 mock.patch.object(plat, "empty_recycle_bin", lambda: (True, "vacía")):
            self.assertEqual((cleaner.analyze(cat).size, cleaner.analyze(cat).count), (1234, 3))
            res = cleaner.clean(cat)
        self.assertEqual((res.freed, res.deleted, res.failed), (1234, 3, 0))
        with mock.patch.object(plat, "recycle_bin_info", lambda: (1, 1)),                 mock.patch.object(plat, "empty_recycle_bin", lambda: (False, "no se pudo")):
            self.assertEqual(cleaner.clean(cat).failed, 1)

    def test_real_categories_only_name_absolute_safe_places(self):
        for cat in cleaner.default_categories():
            for pattern in cat.dirs + cat.files:
                self.assertTrue(os.path.isabs(pattern), f"{cat.id}: {pattern}")
                self.assertNotIn("%", pattern, f"{cat.id}: {pattern}")
            roots, _refused = cleaner._resolve_dirs(cat.dirs)
            for root in roots:                           # nada de lo que se vaciaría es una zona amplia
                self.assertTrue(check_clean_root(root)[0].allowed, root)
                self.assertNotEqual(os.path.normcase(root), os.path.normcase(os.path.expanduser("~")))


# =========================================================================
# PRV-09, integridad, configuración y registro
# =========================================================================

class ProcessIdentityTests(unittest.TestCase):
    def test_creation_time_travels_with_each_pid(self):
        a = ProcInfo(10, "app.exe", r"C:\a\app.exe", 1, 1, 0.0, 1, True, 1, [10], created={10: 111.5})
        b = ProcInfo(11, "app.exe", r"C:\a\app.exe", 1, 1, 0.0, 1, True, 1, [11], created={11: 222.5})
        (group,) = group_by_program([a, b])
        self.assertEqual(group.created, {10: 111.5, 11: 222.5})
        self.assertEqual(a.created, {10: 111.5})          # agrupar no mezcla los datos de cada proceso

    def test_memory_view_passes_the_creation_time(self):
        source = (APP_ROOT / "app" / "superlimpio" / "ui" / "views" / "memory_view.py").read_text(encoding="utf-8")
        self.assertIn("plat.terminate_process(pid, born)", source)
        self.assertNotIn("plat.terminate_process(pid)", source)

    @unittest.skipUnless(WINDOWS, "llamada real a Windows")
    def test_wrong_creation_time_is_not_touched(self):
        from superlimpio import i18n
        me = next(p for p in plat.list_processes() if p.pid == os.getpid())
        self.assertTrue(plat.process_alive(me.pid, me.create_time))
        self.assertFalse(plat.process_alive(me.pid, me.create_time + 60))
        ok, msg, _prev = plat.set_priority(me.pid, plat.PRIORITY_NORMAL, me.create_time + 60)
        self.assertEqual((ok, msg), (False, i18n.t("winapi.proc_changed")))


class IntegrityTests(_Tmp):
    def test_added_files_are_detected(self):
        _write(os.path.join(self.tmp, "app", "main.py"))
        _write(os.path.join(self.tmp, "app", "superlimpio", "safety.pyc"))
        _write(os.path.join(self.tmp, "app", "superlimpio", "_integrity", "manifest.json"))
        _write(os.path.join(self.tmp, "runtime", "python", "python312.dll"))
        _write(os.path.join(self.tmp, "superlimpio.config.json"))
        listed = {"app/main.py", "app/superlimpio/safety.pyc"}
        self.assertEqual(integrity.unexpected_files(self.tmp, listed), [])
        _write(os.path.join(self.tmp, "app", "superlimpio", "safety.py"))    # ganaría al .pyc firmado
        _write(os.path.join(self.tmp, "dwmapi.dll"))                          # se cargaría junto al .exe
        _write(os.path.join(self.tmp, "app", "sitecustomize.py"))
        self.assertEqual(integrity.unexpected_files(self.tmp, listed),
                         ["app/sitecustomize.py", "app/superlimpio/safety.py", "dwmapi.dll"])

    def test_signature_with_s_out_of_range_is_rejected(self):
        secret = bytes(range(32))
        public = integrity.ed25519_publickey(secret)
        signature = integrity.ed25519_sign(secret, b"manifiesto")
        self.assertTrue(integrity.ed25519_verify(public, b"manifiesto", signature))
        self.assertFalse(integrity.ed25519_verify(public, b"manifiest0", signature))
        twin = signature[:32] + (int.from_bytes(signature[32:], "little") + integrity._L).to_bytes(32, "little")
        self.assertFalse(integrity.ed25519_verify(public, b"manifiesto", twin))


class ConfigAndLogTests(_Tmp):
    def test_atomic_write_fails_cleanly(self):
        blocker = os.path.join(self.tmp, "archivo")
        _write(blocker)
        self.assertFalse(config._atomic_write(os.path.join(blocker, "sub", "c.json"), "{}"))   # antes: UnboundLocalError
        target = os.path.join(self.tmp, "ok", "c.json")
        self.assertTrue(config._atomic_write(target, "{}"))
        self.assertEqual(os.listdir(os.path.dirname(target)), ["c.json"])                       # sin temporales

    def test_oversized_config_is_ignored(self):
        big = os.path.join(self.tmp, "c.json")
        with open(big, "w", encoding="utf-8") as fh:
            fh.write('{"language": "es", "relleno": "' + "x" * (config._MAX_BYTES + 10) + '"}')
        self.assertIsNone(config._read_json(big))

    def test_log_rotates_and_cannot_be_forged(self):
        logs = Path(self.tmp) / "registro"
        with mock.patch.object(safety, "LOG_DIR", logs), mock.patch.object(safety, "LOG_MAX_BYTES", 4000):
            safety.log_action("prueba", "ruta\ncon salto", '{"accion": "falsa"}\n{"accion": "otra"}')
            first = safety.read_log()
            self.assertEqual(len(first), 1)                                   # un salto de línea no crea otra entrada
            self.assertEqual(first[0]["objetivo"], "ruta\ncon salto")
            self.assertRegex(first[0]["fecha"], r"[+-]\d\d:\d\d$")             # con su desfase horario
            for i in range(200):
                safety.log_action("relleno", str(i), "x" * 50)
            self.assertTrue((logs / (safety.LOG_NAME + ".1")).exists())
            self.assertLessEqual((logs / safety.LOG_NAME).stat().st_size, 4000)
            self.assertLessEqual(len(os.listdir(logs)), safety.LOG_BACKUPS + 1)
            self.assertEqual(safety.read_log(1)[0]["objetivo"], "199")
            safety.close_log()

    def test_a_log_that_cannot_be_written_is_counted(self):
        blocker = os.path.join(self.tmp, "archivo")
        _write(blocker)
        before = safety.log_failures
        with mock.patch.object(safety, "LOG_DIR", Path(blocker) / "logs"):
            safety.log_action("prueba", "x", "y")                            # no lanza nada…
        self.assertEqual(safety.log_failures, before + 1)                     # …pero queda constancia
        safety.close_log()


class SourceRulesTests(unittest.TestCase):
    """Reglas de la ficha que se comprueban leyendo el código."""

    def _sources(self):
        for path in sorted((APP_ROOT / "app").rglob("*.py")) + sorted((APP_ROOT / "tools").glob("*.py")):
            yield path, path.read_text(encoding="utf-8")

    def test_no_dangerous_calls(self):
        import re
        banned = re.compile(r"\beval\(|\bexec\(|\bpickle\b|\bmarshal\b|yaml\.load\(|shell\s*=\s*True|os\.system\(|"
                            r"os\.popen\(|tempfile\.mktemp\(|verify\s*=\s*False")
        for path, source in self._sources():
            for n, line in enumerate(source.splitlines(), 1):
                code = line.split("#", 1)[0]
                self.assertIsNone(banned.search(code), f"{path}:{n}: {line.strip()}")

    def test_windows_dlls_are_loaded_from_system32_only(self):
        import re
        for path, source in self._sources():
            self.assertNotIn("ctypes.windll", source, path)
            for call in re.findall(r"ctypes\.WinDLL\([^)]*\)", source):
                self.assertIn("winmode=", call, f"{path}: {call}")

    def test_every_platform_branch_fails_explicitly(self):
        source = (APP_ROOT / "app" / "superlimpio" / "plat" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn('raise ImportError(f"Super Limpio no admite esta plataforma', source)

    def test_launchers_run_python_isolated(self):
        bat = (APP_ROOT / "SuperLimpio.bat").read_text(encoding="utf-8")
        for line in bat.splitlines():
            if "main.py" in line and not line.lstrip().lower().startswith("rem"):
                self.assertIn(" -I ", line, line)
        self.assertIn('-I "$HERE/app/main.py"', (APP_ROOT / "superlimpio.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
