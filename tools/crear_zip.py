"""Genera el zip de Super Limpio en dist\\.

    runtime\\python\\python.exe tools\\crear_zip.py               -> solo código (unos 100 KB)
    runtime\\python\\python.exe tools\\crear_zip.py --con-python  -> además el Python portable

El zip solo contiene texto legible (.py, .bat, .md, .json). Con --con-python se
añaden los binarios oficiales de Python tal cual se descargaron, con su firma
digital intacta. Nunca se incluyen registros, descargas temporales, VS Code ni
nada compilado por nosotros: es lo que evita los falsos positivos del antivirus.
"""

from __future__ import annotations

import argparse
import os
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


def _files(base: Path):
    if base.is_file():
        yield base
        return
    # Dentro del Python portable solo se descarta el código compilado
    skip = {"__pycache__"} if base.name == "python" else SKIP_DIRS
    for folder, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        for name in sorted(names):
            path = Path(folder, name)
            if path.suffix.lower() not in SKIP_SUFFIXES:
                yield path


def build(with_python: bool) -> Path:
    include = list(INCLUDE)
    if with_python:
        if not (ROOT / "runtime" / "python" / "pythonw.exe").exists():
            raise SystemExit("Falta runtime\\python. Ejecuta antes preparar_entorno.bat.")
        include.append("runtime/python")
    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)
    suffix = "-con-python" if with_python else ""
    out = out_dir / f"SuperLimpio-{__version__}{suffix}.zip"
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for item in include:
            base = ROOT / item
            if not base.exists():
                raise SystemExit(f"Falta {item}")
            for path in _files(base):
                # Todo cuelga de una carpeta «SuperLimpio» para que al descomprimir quede ordenado
                zf.write(path, Path("SuperLimpio", path.relative_to(ROOT)).as_posix())
                count += 1
    print(f"{out}\n{count} archivos · {out.stat().st_size / 1024 / 1024:.2f} MB")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crea el zip de Super Limpio en dist\\")
    parser.add_argument("--con-python", action="store_true",
                        help="incluye runtime\\python para que funcione sin descargar nada")
    build(parser.parse_args().con_python)
