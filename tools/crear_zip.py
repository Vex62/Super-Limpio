"""Genera el zip de Super Limpio en dist\\.

    runtime\\python\\python.exe tools\\crear_zip.py               -> solo código (unos 100 KB)
    runtime\\python\\python.exe tools\\crear_zip.py --con-python  -> además el Python portable
    runtime\\python\\python.exe tools\\crear_zip.py --portable    -> SuperLimpio.exe + app + Python

El zip solo contiene texto legible (.py, .bat, .md, .json). Con --con-python se
añaden los binarios oficiales de Python tal cual se descargaron, con su firma
digital intacta. Con --portable va además SuperLimpio.exe (tools\\crear_exe.py),
un lanzador de unos 55 KB que no lleva nada empaquetado dentro: descomprimir y
abrir con doble clic. Ese zip lleva también el código ya compilado (.pyc) para que
la ventana abra rápido desde la primera vez, esté donde esté la carpeta.
Nunca se incluyen registros, descargas temporales ni VS Code.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

import firmar  # noqa: E402
from superlimpio import __version__, integrity  # noqa: E402

# Lo que forma la aplicación (rutas relativas a la raíz del proyecto)
# La documentación y las herramientas de protección (PROTECCION.md, tools\firmar.py)
# se quedan SOLO en el repositorio: nunca se distribuyen.
INCLUDE = ["SuperLimpio.bat", "preparar_entorno.bat", "README.md", "SuperLimpio.code-workspace",
           ".vscode", "app", "tests", "tools/crear_zip.py", "tools/LEEME.txt", "runtime/LEEME.txt"]

# README mínimo para la distribución de producción: solo cómo abrirla, sin internos.
PROD_README = """Super Limpio {version}

Doble clic en SuperLimpio.exe para abrir la aplicación.
Funciona en local, sin conexión a internet. Todas las acciones piden confirmación.
Las preferencias se guardan en superlimpio.config.json, junto a la aplicación.

--

Double-click SuperLimpio.exe to start.
Runs locally, offline. Every action asks for confirmation.
Settings are stored in superlimpio.config.json, next to the application.
"""
SKIP_DIRS = {"__pycache__", "_pycache", "_descargas", "logs", "dist", ".git", "VSCode"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".log"}
# Lo justo para usar la aplicación con doble clic, sin nada de desarrollo
PORTABLE = ["SuperLimpio.exe", "README.md", "app", "runtime/LEEME.txt", "runtime/python"]
# Partes de la biblioteca de Python que la app no usa: no merece la pena compilarlas
NO_COMPILE = r"[\\/](test|tests|idlelib|lib2to3|turtledemo|ensurepip|site-packages)[\\/]"


def _files(base: Path, compiled: bool = False):
    if base.is_file():
        yield base
        return
    # Dentro del Python portable solo se descarta el código compilado
    skip = {"__pycache__"} if base.name == "python" else SKIP_DIRS
    suffixes = SKIP_SUFFIXES
    if compiled:
        skip, suffixes = skip - {"__pycache__"}, suffixes - {".pyc"}
    for folder, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        for name in sorted(names):
            path = Path(folder, name)
            if path.suffix.lower() not in suffixes:
                yield path


def _compile() -> None:
    """Deja hechos los .pyc de la app y de la biblioteca, con el Python que va en el zip.

    Se validan por el contenido del .py (checked-hash) y no por su fecha, así que valen
    en cualquier carpeta y equipo, y si alguien edita un .py se vuelve a compilar solo.
    """
    python = ROOT / "runtime" / "python" / "python.exe"
    print("Compilando .pyc ...")
    subprocess.run([str(python), "-I", "-m", "compileall", "-q", "-f", "--invalidation-mode", "checked-hash",
                    "-x", NO_COMPILE, str(ROOT / "app"), str(ROOT / "runtime" / "python" / "Lib")], check=True)


def build(with_python: bool, portable: bool = False) -> Path:
    include = list(PORTABLE if portable else INCLUDE)
    if portable and not (ROOT / "SuperLimpio.exe").exists():
        raise SystemExit("Falta SuperLimpio.exe. Ejecuta antes tools\\crear_exe.py.")
    if with_python or portable:
        if not (ROOT / "runtime" / "python" / "pythonw.exe").exists():
            raise SystemExit("Falta runtime\\python. Ejecuta antes preparar_entorno.bat.")
    if with_python and not portable:
        include.append("runtime/python")
    if portable:
        _compile()
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    suffix = "-portable" if portable else "-con-python" if with_python else ""
    out = out_dir / f"SuperLimpio-{__version__}{suffix}.zip"
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for item in include:
            base = ROOT / item
            if not base.exists():
                raise SystemExit(f"Falta {item}")
            for path in _files(base, compiled=portable):
                # Todo cuelga de una carpeta «SuperLimpio» para que al descomprimir quede ordenado
                zf.write(path, Path("SuperLimpio", path.relative_to(ROOT)).as_posix())
                count += 1
    print(f"{out}\n{count} archivos · {out.stat().st_size / 1024 / 1024:.2f} MB")
    return out


def _pyarmor_obfuscate(pkg_dir: Path) -> bool:
    """Ofusca el paquete superlimpio con PyArmor si está instalado. Devuelve True si se aplicó."""
    try:
        subprocess.run([sys.executable, "-I", "-m", "pyarmor", "--version"],
                       capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        print("PyArmor no está instalado (pip install pyarmor); se omite la ofuscación.")
        return False
    out = pkg_dir.parent / "_pyarmor_out"
    print("Ofuscando con PyArmor…")
    subprocess.run([sys.executable, "-I", "-m", "pyarmor", "gen", "-O", str(out),
                    "-r", str(pkg_dir)], check=True)
    obf_pkg = out / pkg_dir.name
    if not obf_pkg.is_dir():
        raise SystemExit("PyArmor no generó el paquete ofuscado esperado.")
    shutil.rmtree(pkg_dir)
    shutil.move(str(obf_pkg), str(pkg_dir))
    # PyArmor deja un runtime propio junto al paquete: hay que llevarlo a app\
    for extra in out.iterdir():
        dest = pkg_dir.parent / extra.name
        if not dest.exists():
            shutil.move(str(extra), str(dest))
    shutil.rmtree(out, ignore_errors=True)
    return True


def _make_sourceless(pkg_dir: Path) -> None:
    """Compila a .pyc junto a cada módulo y borra los .py (distribución sin fuente)."""
    python = ROOT / "runtime" / "python" / "python.exe"
    subprocess.run([str(python), "-I", "-m", "compileall", "-b", "-q", str(pkg_dir)], check=True)
    for py in pkg_dir.rglob("*.py"):
        if py.with_suffix(".pyc").is_file():
            py.unlink()
    for cache in pkg_dir.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def build_protected(key_path: Path, use_pyarmor: bool) -> Path:
    """Distribución blindada: bytecode sin fuente del paquete + manifiesto firmado (+ PyArmor opcional)."""
    if not (ROOT / "SuperLimpio.exe").exists():
        raise SystemExit("Falta SuperLimpio.exe. Ejecuta antes tools\\crear_exe.py.")
    if not (ROOT / "runtime" / "python" / "pythonw.exe").exists():
        raise SystemExit("Falta runtime\\python. Ejecuta antes preparar_entorno.bat.")
    if not integrity.PUBLIC_KEY_HEX:
        raise SystemExit("No hay clave de firma. Ejecuta antes:\n"
                         "  runtime\\python\\python.exe tools\\firmar.py --generar-claves")
    if not key_path.is_file():
        raise SystemExit(f"No existe la clave privada: {key_path}")

    stage = Path(tempfile.mkdtemp(prefix="superlimpio_stage_"))
    try:
        app_stage = stage / "app"
        shutil.copytree(ROOT / "app", app_stage,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        if use_pyarmor:
            _pyarmor_obfuscate(app_stage / "superlimpio")
        _make_sourceless(app_stage / "superlimpio")   # main.py se conserva: lo lanza SuperLimpio.exe
        shutil.copyfile(ROOT / "SuperLimpio.exe", stage / "SuperLimpio.exe")
        # README mínimo (no el del repo): la versión de producción no explica su interior
        (stage / "README.md").write_text(PROD_README.format(version=__version__), encoding="utf-8")

        firmar.firmar(stage, key_path)                # manifiesto firmado sobre lo que se publica

        out = ROOT / "dist" / f"SuperLimpio-{__version__}-protegido.zip"
        out.parent.mkdir(exist_ok=True)
        count = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for folder, dirs, names in os.walk(stage):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                for name in sorted(names):
                    path = Path(folder, name)
                    zf.write(path, Path("SuperLimpio", path.relative_to(stage)).as_posix())
                    count += 1
            for item in ("runtime/python", "runtime/LEEME.txt"):
                base = ROOT / item
                for path in _files(base, compiled=True):
                    zf.write(path, Path("SuperLimpio", path.relative_to(ROOT)).as_posix())
                    count += 1
        print(f"{out}\n{count} archivos · {out.stat().st_size / 1024 / 1024:.2f} MB  (firmado)")
        return out
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crea el zip de Super Limpio en dist\\")
    parser.add_argument("--con-python", action="store_true",
                        help="incluye runtime\\python para que funcione sin descargar nada")
    parser.add_argument("--portable", action="store_true",
                        help="SuperLimpio.exe + app + runtime\\python: descomprimir y abrir con doble clic")
    parser.add_argument("--protegido", action="store_true",
                        help="como --portable pero con bytecode sin fuente y manifiesto de integridad firmado")
    parser.add_argument("--pyarmor", action="store_true",
                        help="además, ofusca el paquete con PyArmor (requiere: pip install pyarmor)")
    parser.add_argument("--clave", metavar="ARCHIVO", default=str(firmar.DEFAULT_KEY),
                        help="clave privada de firma (para --protegido)")
    args = parser.parse_args()
    if args.protegido:
        build_protected(Path(args.clave), args.pyarmor)
    else:
        build(args.con_python, args.portable)
