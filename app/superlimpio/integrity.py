"""Autocomprobación de integridad de la distribución (anti-manipulación).

Al crear una distribución (tools\\firmar.py) se calcula el SHA-256 de cada archivo
de la aplicación y se guarda un manifiesto firmado con una clave privada Ed25519 que
solo tiene quien publica. La app verifica al arrancar que:

  1) la firma del manifiesto es válida para la clave pública incrustada aquí, y
  2) cada archivo listado conserva su hash.

Si alguien modifica o sustituye un archivo de una copia publicada, o AÑADE uno dentro de
la carpeta «app» (un .py junto a un .pyc firmado se cargaría en su lugar), la app se niega
a continuar. Todo con biblioteca estándar (Ed25519 en Python puro), sin dependencias.

Qué NO cubre: la carpeta «runtime» (el Python portable, cuyos binarios ya van firmados por
la Python Software Foundation) y cualquier comprobación que alguien desactive editando
este mismo archivo. Es una barrera contra copias manipuladas, no un sustituto de la firma
Authenticode del ejecutable.

Sobre la criptografía propia: la biblioteca estándar no trae Ed25519 y la aplicación no
admite dependencias, así que aquí va la implementación de referencia del RFC 8032. Solo
se usa para VERIFICAR con una clave pública (no hay secretos que filtrar por tiempo); la
firma se hace en el equipo de quien publica.

Límite honesto: cualquier protección que se ejecute en el propio equipo del usuario puede,
en teoría, desactivarse si se edita el código verificador y se vuelve a firmar con otra
clave. Por eso este módulo se distribuye compilado y ofuscado (PyArmor) y la clave pública
viaja también incrustada en SuperLimpio.exe: subir el listón, no prometer lo imposible.
"""

from __future__ import annotations

import hashlib
import json
import os

# Este módulo no importa NADA del resto de la aplicación: main.py lo carga por su ruta y lo
# ejecuta antes que cualquier otro, cuando todavía no se sabe si los demás son los originales.
# Carpeta raíz de la app portable (la que contiene SuperLimpio.exe): tres niveles por encima.
APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Clave pública Ed25519 (64 hex = 32 bytes) de quien firma las distribuciones.
# La escribe tools\\firmar.py --generar-claves. Vacía = sin firmar (modo desarrollo).
PUBLIC_KEY_HEX = "07f10f84d68944e0b67495ab9b925125e0902a1b0d95578dfc4da6bce79536ec"

_INTEGRITY_DIR = os.path.join(APP_ROOT, "app", "superlimpio", "_integrity")
MANIFEST_PATH = os.path.join(_INTEGRITY_DIR, "manifest.json")
SIGNATURE_PATH = os.path.join(_INTEGRITY_DIR, "manifest.sig")


# =========================================================================
# Ed25519 en Python puro (RFC 8032). Solo verificación/firma de una firma al
# arrancar: el rendimiento no importa.
# =========================================================================
_p = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_d = (-121665 * pow(121666, _p - 2, _p)) % _p
_I = pow(2, (_p - 1) // 4, _p)


def _inv(x: int) -> int:
    return pow(x, _p - 2, _p)


def _x_recover(y: int) -> int:
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = pow(xx, (_p + 3) // 8, _p)
    if (x * x - xx) % _p != 0:
        x = (x * _I) % _p
    if x % 2 != 0:
        x = _p - x
    return x


_By = (4 * _inv(5)) % _p
_Bx = _x_recover(_By)
_B = (_Bx % _p, _By % _p)


def _edwards(pt1: tuple[int, int], pt2: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = pt1
    x2, y2 = pt2
    denom = _d * x1 * x2 * y1 * y2
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + denom)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - denom)
    return (x3 % _p, y3 % _p)


def _scalarmult(pt: tuple[int, int], e: int) -> tuple[int, int]:
    if e == 0:
        return (0, 1)
    q = _scalarmult(pt, e // 2)
    q = _edwards(q, q)
    if e & 1:
        q = _edwards(q, pt)
    return q


def _encode_point(pt: tuple[int, int]) -> bytes:
    x, y = pt
    bits = [(y >> i) & 1 for i in range(255)] + [x & 1]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(32))


def _bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1


def _hint(m: bytes) -> int:
    h = hashlib.sha512(m).digest()
    return sum(2 ** i * _bit(h, i) for i in range(512))


def _is_on_curve(pt: tuple[int, int]) -> bool:
    x, y = pt
    return (-x * x + y * y - 1 - _d * x * x * y * y) % _p == 0


def _decode_point(s: bytes) -> tuple[int, int]:
    y = sum(2 ** i * _bit(s, i) for i in range(255))
    x = _x_recover(y)
    if x & 1 != _bit(s, 255):
        x = _p - x
    pt = (x, y)
    if not _is_on_curve(pt):
        raise ValueError("punto fuera de la curva")
    return pt


def ed25519_publickey(secret: bytes) -> bytes:
    h = hashlib.sha512(secret).digest()
    a = 2 ** 254 + sum(2 ** i * _bit(h, i) for i in range(3, 254))
    return _encode_point(_scalarmult(_B, a))


def ed25519_sign(secret: bytes, msg: bytes) -> bytes:
    h = hashlib.sha512(secret).digest()
    a = 2 ** 254 + sum(2 ** i * _bit(h, i) for i in range(3, 254))
    public = _encode_point(_scalarmult(_B, a))
    r = _hint(h[32:64] + msg)
    big_r = _scalarmult(_B, r)
    s = (r + _hint(_encode_point(big_r) + public + msg) * a) % _L
    return _encode_point(big_r) + int(s).to_bytes(32, "little")


def ed25519_verify(public: bytes, msg: bytes, signature: bytes) -> bool:
    if len(signature) != 64 or len(public) != 32:
        return False
    try:
        big_r = _decode_point(signature[:32])
        a = _decode_point(public)
    except ValueError:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:   # RFC 8032: una firma con S fuera de rango no es válida (evita firmas «gemelas»)
        return False
    h = _hint(signature[:32] + public + msg)
    left = _scalarmult(_B, s)
    right = _edwards(big_r, _scalarmult(a, h))
    return left == right


# =========================================================================
# Manifiesto
# =========================================================================
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build_manifest(files: dict[str, str], version: str) -> bytes:
    """Serializa el manifiesto de forma estable (lo mismo que se firma y se verifica)."""
    payload = {"version": version, "algo": "ed25519-sha256", "files": dict(sorted(files.items()))}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash_tree(root: str, rel_paths: list[str]) -> dict[str, str]:
    return {rel: _sha256(os.path.join(root, rel)) for rel in rel_paths
            if os.path.isfile(os.path.join(root, rel))}


_MAX_MANIFEST = 8 * 1024 * 1024
# Lo que puede aparecer dentro de «app» sin estar en el manifiesto: el propio manifiesto.
_UNSIGNED_DIRS = {"_integrity"}
# En la carpeta de la aplicación, junto al ejecutable, estos tipos de archivo se cargarían
# como código al arrancar: si no están firmados, no deben estar.
_CODE_SUFFIXES = (".dll", ".pyd", ".pth", ".py", ".pyc", ".exe")


def unexpected_files(root: str, listed: set[str]) -> list[str]:
    """Archivos que no figuran en el manifiesto y que el intérprete podría cargar: todo lo
    que haya dentro de «app», y el código suelto junto al ejecutable."""
    extra: list[str] = []
    app = os.path.join(root, "app")
    for folder, dirs, names in os.walk(app):
        dirs[:] = [d for d in dirs if d not in _UNSIGNED_DIRS]
        for name in names:
            rel = os.path.relpath(os.path.join(folder, name), root).replace(os.sep, "/")
            if rel not in listed:
                extra.append(rel)
    try:
        for name in os.listdir(root):
            if name not in listed and name.lower().endswith(_CODE_SUFFIXES) \
                    and os.path.isfile(os.path.join(root, name)):
                extra.append(name)
    except OSError:
        extra.append(".")   # no se puede comprobar: se trata como manipulada
    return sorted(extra)


class IntegrityResult:
    def __init__(self, ok: bool, enforced: bool, detail: str = "") -> None:
        self.ok = ok
        self.enforced = enforced   # False = no hay manifiesto firmado (modo desarrollo)
        self.detail = detail


def verify_distribution() -> IntegrityResult:
    """Comprueba la distribución. Sin manifiesto o sin clave pública => modo desarrollo (no bloquea).

    El detalle va en español e inglés porque esto se ejecuta antes de saber el idioma: no
    puede usar ningún otro módulo de la aplicación (aún no se sabe si son los originales)."""
    if not PUBLIC_KEY_HEX or not (os.path.isfile(MANIFEST_PATH) and os.path.isfile(SIGNATURE_PATH)):
        return IntegrityResult(True, enforced=False)
    bad_signature = "la firma de integridad no es válida / the integrity signature is not valid"
    try:
        with open(MANIFEST_PATH, "rb") as fh:
            manifest_bytes = fh.read(_MAX_MANIFEST + 1)
        with open(SIGNATURE_PATH, encoding="ascii") as fh:
            signature = bytes.fromhex(fh.read(1024).strip())
        public = bytes.fromhex(PUBLIC_KEY_HEX.strip())
        if len(manifest_bytes) > _MAX_MANIFEST:
            raise ValueError("manifiesto demasiado grande")
    except (OSError, ValueError):
        return IntegrityResult(False, enforced=True, detail=bad_signature)

    if not ed25519_verify(public, manifest_bytes, signature):
        return IntegrityResult(False, enforced=True, detail=bad_signature)

    manifest = json.loads(manifest_bytes.decode("utf-8"))
    listed = manifest.get("files", {})
    changed = 0
    for rel, expected in listed.items():
        full = os.path.join(APP_ROOT, rel)
        try:
            if not os.path.isfile(full) or _sha256(full) != expected:
                changed += 1
        except OSError:
            changed += 1
    if changed:
        return IntegrityResult(False, enforced=True,
                               detail=f"{changed} archivos modificados o que faltan / modified or missing files")
    extra = unexpected_files(APP_ROOT, set(listed))
    if extra:
        return IntegrityResult(False, enforced=True,
                               detail=f"{len(extra)} archivos que no son de la aplicación / files that are not "
                                      f"part of the application ({extra[0]})")
    return IntegrityResult(True, enforced=True)
