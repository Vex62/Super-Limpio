"""Genera el paquete de Super Limpio para Linux en dist/.

    runtime\\python\\python.exe tools\\crear_linux.py            -> dist/SuperLimpio-<versión>-linux.tar.gz
    runtime\\python\\python.exe tools\\crear_linux.py --sin-firma -> lo mismo, sin manifiesto de integridad

El paquete lleva el código fuente de la aplicación (texto legible, con finales de línea
de Unix) y el lanzador `superlimpio.sh`. No lleva Python: en Linux se usa el del sistema
(3.11 o posterior, con tkinter), que traen casi todas las distribuciones.

Se puede crear desde Windows o desde Linux: los permisos de ejecución se escriben en el
propio .tar, no dependen del sistema de archivos. Si existe la clave de firma, el paquete
va firmado igual que el zip protegido de Windows y la app se niega a arrancar si alguien
modifica sus archivos.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

import firmar  # noqa: E402
from superlimpio import __version__, integrity  # noqa: E402

TOP = "SuperLimpio"
TEXT_SUFFIXES = {".py", ".sh", ".txt", ".md", ".json"}
EXECUTABLES = {"superlimpio.sh"}

LEEME = """Super Limpio {version} para Linux

Abrir:      ./superlimpio.sh
Al menú:    ./superlimpio.sh --instalar     (solo tu usuario; se quita con --quitar)

Necesita Python 3.11 o posterior con tkinter. Si falta, el propio lanzador te dice
qué paquete instalar (en Debian/Ubuntu: sudo apt install python3-tk).
Opcional: «wmctrl», para que el Modo eficiente sepa qué programas tienen una ventana
abierta y pueda pedirles que se cierren como si pulsaras su X.

Funciona en local, sin conexión a internet. Todas las acciones piden confirmación.
Las preferencias se guardan en superlimpio.config.json, junto a la aplicación, y lo
que hace queda anotado en ~/.local/state/superlimpio/logs/acciones.log.

--

Run:        ./superlimpio.sh
Menu entry: ./superlimpio.sh --instalar     (your user only; remove it with --quitar)

Needs Python 3.11 or newer with tkinter. If it is missing, the launcher tells you which
package to install (on Debian/Ubuntu: sudo apt install python3-tk).
Optional: "wmctrl", so Efficient mode knows which programs have an open window.

Runs locally, offline. Every action asks for confirmation.
"""


def _stage(dest: Path) -> None:
    """Copia a «dest» lo que se publica, con finales de línea de Unix en los textos."""
    def ignore(_folder: str, names: list[str]) -> set[str]:
        return {n for n in names if n in ("__pycache__", "_integrity") or n.endswith((".pyc", ".pyo", ".ico"))}

    shutil.copytree(ROOT / "app", dest / "app", ignore=ignore)
    shutil.copyfile(ROOT / "superlimpio.sh", dest / "superlimpio.sh")
    (dest / "LEEME.txt").write_text(LEEME.format(version=__version__), encoding="utf-8", newline="\n")
    for path in dest.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            data = path.read_bytes()
            fixed = data.replace(b"\r\n", b"\n")
            if fixed != data:
                path.write_bytes(fixed)


def build(sign: bool, key_path: Path) -> Path:
    stage = Path(tempfile.mkdtemp(prefix="superlimpio_linux_"))
    try:
        _stage(stage)
        signed = False
        if sign and integrity.PUBLIC_KEY_HEX and key_path.is_file():
            firmar.firmar(stage, key_path)
            signed = True
        elif sign:
            print("Sin clave de firma: el paquete se crea sin manifiesto de integridad.")

        out = ROOT / "dist" / f"SuperLimpio-{__version__}-linux.tar.gz"
        out.parent.mkdir(exist_ok=True)
        count = 0
        with tarfile.open(out, "w:gz", compresslevel=9, format=tarfile.PAX_FORMAT) as tar:
            for folder, dirs, names in os.walk(stage):
                dirs.sort()
                rel_dir = Path(folder).relative_to(stage)
                info = tarfile.TarInfo((Path(TOP) / rel_dir).as_posix())
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                info.mtime = int(Path(folder).stat().st_mtime)
                tar.addfile(info)
                for name in sorted(names):
                    data = Path(folder, name).read_bytes()
                    info = tarfile.TarInfo((Path(TOP) / rel_dir / name).as_posix())
                    info.size = len(data)
                    info.mode = 0o755 if name in EXECUTABLES else 0o644
                    info.mtime = int(Path(folder, name).stat().st_mtime)
                    tar.addfile(info, io.BytesIO(data))
                    count += 1
        print(f"{out}\n{count} archivos · {out.stat().st_size / 1024:.0f} KB" + ("  (firmado)" if signed else ""))
        return out
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crea el paquete de Super Limpio para Linux en dist/")
    parser.add_argument("--sin-firma", action="store_true", help="no añade el manifiesto de integridad")
    parser.add_argument("--clave", metavar="ARCHIVO", default=str(firmar.DEFAULT_KEY),
                        help="clave privada de firma")
    args = parser.parse_args()
    build(not args.sin_firma, Path(args.clave))
