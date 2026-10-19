"""Firma de integridad de las distribuciones de Super Limpio (anti-manipulación).

Uso:

  runtime\\python\\python.exe tools\\firmar.py --generar-claves
      Genera un par de claves Ed25519. La PRIVADA se guarda fuera del repositorio
      (por defecto en %USERPROFILE%\\.superlimpio\\clave_firma.hex) y nunca debe salir
      de tu equipo. La PÚBLICA se incrusta en app\\superlimpio\\integrity.py.

  runtime\\python\\python.exe tools\\firmar.py --firmar <carpeta_distribucion>
      Calcula el SHA-256 de los archivos de la distribución y escribe un manifiesto
      firmado en <carpeta>\\app\\superlimpio\\_integrity\\. La app lo verifica al
      arrancar: si algo se modifica, se niega a continuar.

  runtime\\python\\python.exe tools\\firmar.py --verificar <carpeta_distribucion>
      Comprueba la firma y los hashes (lo mismo que hace la app al arrancar).

Sin dependencias externas: Ed25519 en Python puro (app\\superlimpio\\integrity.py).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from superlimpio import __version__, integrity  # noqa: E402

INTEGRITY_PY = ROOT / "app" / "superlimpio" / "integrity.py"
DEFAULT_KEY = Path(os.path.expanduser("~")) / ".superlimpio" / "clave_firma.hex"

# Qué se firma (relativo a la raíz de la distribución). El runtime de Python no se
# incluye: sus binarios ya están firmados por la Python Software Foundation / Microsoft,
# y hashearlos todos ralentizaría el arranque. Se protege lo que es propio de la app.
SIGNED_SUBDIRS = ("app",)
SIGNED_ROOT_FILES = ("SuperLimpio.exe", "SuperLimpio.bat", "superlimpio.sh", "README.md", "LEEME.txt", "LICENSE")
EXCLUDE_NAMES = {"manifest.json", "manifest.sig", "superlimpio.config.json"}
EXCLUDE_SUFFIXES = {".log"}


def _signed_files(dist_root: Path) -> list[str]:
    """Rutas relativas (con «/») de los archivos a firmar, en orden estable."""
    rel: list[str] = []
    for sub in SIGNED_SUBDIRS:
        base = dist_root / sub
        if not base.is_dir():
            continue
        for folder, dirs, names in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d != "_integrity")
            for name in sorted(names):
                if name in EXCLUDE_NAMES or Path(name).suffix.lower() in EXCLUDE_SUFFIXES:
                    continue
                rel.append(Path(folder, name).relative_to(dist_root).as_posix())
    for name in SIGNED_ROOT_FILES:
        if (dist_root / name).is_file():
            rel.append(name)
    return sorted(set(rel))


def generar_claves(private_path: Path) -> None:
    secret = os.urandom(32)
    public = integrity.ed25519_publickey(secret)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_text(secret.hex(), encoding="ascii")
    try:
        os.chmod(private_path, 0o600)
    except OSError:
        pass

    text = INTEGRITY_PY.read_text(encoding="utf-8")
    new = re.sub(r'PUBLIC_KEY_HEX = "[0-9a-fA-F]*"',
                 f'PUBLIC_KEY_HEX = "{public.hex()}"', text, count=1)
    if new == text:
        raise SystemExit("No se encontró la línea PUBLIC_KEY_HEX en integrity.py")
    INTEGRITY_PY.write_text(new, encoding="utf-8")
    print("Clave privada:", private_path, "(guárdala a buen recaudo; no la subas a git)")
    print("Clave pública incrustada en:", INTEGRITY_PY)
    print("Pública:", public.hex())


def firmar(dist_root: Path, private_path: Path) -> None:
    if not private_path.is_file():
        raise SystemExit(f"No existe la clave privada: {private_path}\n"
                         "Genera una con  tools\\firmar.py --generar-claves")
    secret = bytes.fromhex(private_path.read_text(encoding="ascii").strip())
    rel = _signed_files(dist_root)
    if not rel:
        raise SystemExit(f"No se encontraron archivos a firmar en {dist_root}")
    files = integrity.hash_tree(str(dist_root), rel)
    manifest = integrity.build_manifest(files, __version__)
    signature = integrity.ed25519_sign(secret, manifest)

    out_dir = dist_root / "app" / "superlimpio" / "_integrity"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_bytes(manifest)
    (out_dir / "manifest.sig").write_text(signature.hex(), encoding="ascii")
    print(f"Firmados {len(files)} archivos -> {out_dir}")


def verificar(dist_root: Path) -> int:
    """Verifica como lo haría la app (con la clave pública incrustada)."""
    public_hex = integrity.PUBLIC_KEY_HEX
    if not public_hex:
        raise SystemExit("integrity.PUBLIC_KEY_HEX está vacío: genera las claves primero.")
    manifest_path = dist_root / "app" / "superlimpio" / "_integrity" / "manifest.json"
    sig_path = dist_root / "app" / "superlimpio" / "_integrity" / "manifest.sig"
    if not (manifest_path.is_file() and sig_path.is_file()):
        raise SystemExit("La distribución no está firmada (falta el manifiesto).")
    manifest_bytes = manifest_path.read_bytes()
    signature = bytes.fromhex(sig_path.read_text(encoding="ascii").strip())
    if not integrity.ed25519_verify(bytes.fromhex(public_hex), manifest_bytes, signature):
        print("FIRMA NO VÁLIDA")
        return 1
    import json
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    bad = []
    for relp, expected in manifest["files"].items():
        full = dist_root / relp
        if not full.is_file() or integrity._sha256(str(full)) != expected:
            bad.append(relp)
    if bad:
        print(f"{len(bad)} archivos modificados o ausentes:")
        for b in bad[:20]:
            print("  ", b)
        return 1
    print(f"OK: firma válida y {len(manifest['files'])} archivos íntegros.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Firma de integridad de Super Limpio")
    ap.add_argument("--generar-claves", action="store_true", help="crea el par de claves Ed25519")
    ap.add_argument("--firmar", metavar="CARPETA", help="firma una carpeta de distribución")
    ap.add_argument("--verificar", metavar="CARPETA", help="verifica una carpeta de distribución")
    ap.add_argument("--clave", metavar="ARCHIVO", default=str(DEFAULT_KEY),
                    help="ruta de la clave privada (por defecto %%USERPROFILE%%\\.superlimpio\\clave_firma.hex)")
    args = ap.parse_args()

    if args.generar_claves:
        generar_claves(Path(args.clave))
    elif args.firmar:
        firmar(Path(args.firmar), Path(args.clave))
    elif args.verificar:
        sys.exit(verificar(Path(args.verificar)))
    else:
        ap.print_help()
