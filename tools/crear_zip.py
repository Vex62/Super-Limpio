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
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from superlimpio import __version__  # noqa: E402

# Lo que forma la aplicación (rutas relativas a la raíz del proyecto)
INCLUDE = ["SuperLimpio.bat", "preparar_entorno.bat", "README.md", "SuperLimpio.code-workspace",
           ".vscode", "app", "tests", "tools/crear_zip.py", "tools/LEEME.txt", "runtime/LEEME.txt"]
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crea el zip de Super Limpio en dist\\")
    parser.add_argument("--con-python", action="store_true",
                        help="incluye runtime\\python para que funcione sin descargar nada")
    parser.add_argument("--portable", action="store_true",
                        help="SuperLimpio.exe + app + runtime\\python: descomprimir y abrir con doble clic")
    args = parser.parse_args()
    build(args.con_python, args.portable)
