"""Auxiliar elevado: el único código de Super Limpio que corre como administrador.

La aplicación trabaja siempre como usuario normal. Cuando una operación concreta necesita
administrador (vaciar la carpeta temporal de Windows, borrar algo que el usuario no puede),
la ventana se lo encarga a este auxiliar, que es un proceso aparte, mínimo y sin interfaz:

  1. La ventana, tras la confirmación del usuario, escribe la ORDEN en un archivo nuevo de
     su carpeta privada y lanza el auxiliar con elevación (Windows muestra su aviso UAC),
     pasándole el archivo y su huella SHA-256.
  2. El auxiliar solo acepta el archivo si su contenido tiene esa huella, y la orden solo
     si es una de las previstas, con la forma exacta prevista. No acepta comandos, código
     ni opciones libres.
  3. Lo vuelve a comprobar todo por su cuenta, con las mismas reglas que la ventana: las
     categorías de limpieza las saca de su propia lista (la orden solo trae sus nombres) y
     cada ruta a borrar pasa otra vez por `safety.check_deletable`.
  4. Deja el resultado en un archivo que crea en exclusiva, y termina.

Órdenes:
  {"v": 1, "order": "clean",  "categories": ["temp_win", ...]}   solo categorías «admin»
  {"v": 1, "order": "delete", "paths": ["C:\\\\ruta", ...]}       borrado definitivo
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import tempfile
from typing import Any

from . import i18n, plat
from .safety import log_action
from .util import APP_ROOT

VERSION = 1
MAX_REQUEST = 4 * 1024 * 1024     # bytes de una orden; más que esto no se lee
MAX_PATHS = 20000
MAX_PATH_CHARS = 32767
RESULT_SUFFIX = ".resultado"
_CATEGORY_ID = re.compile(r"^[a-z0-9_]{1,32}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")

EXIT_OK, EXIT_PARTIAL, EXIT_REJECTED = 0, 1, 2


class OrderError(ValueError):
    """La orden no es una de las previstas o no tiene la forma exacta prevista."""


# =========================================================================
# La orden: construirla, validarla
# =========================================================================

def clean_order(category_ids: list[str]) -> dict[str, Any]:
    return {"v": VERSION, "order": "clean", "categories": sorted(set(category_ids))}


def delete_order(paths: list[str]) -> dict[str, Any]:
    return {"v": VERSION, "order": "delete", "paths": list(paths)}


def parse_order(data: bytes) -> dict[str, Any]:
    """Valida una orden recibida. Lo que no sea exactamente lo esperado se rechaza."""
    try:
        order = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise OrderError("no es JSON") from exc
    if not isinstance(order, dict) or order.get("v") != VERSION:
        raise OrderError("versión desconocida")
    kind = order.get("order")
    if kind == "clean":
        if set(order) != {"v", "order", "categories"}:
            raise OrderError("campos de más o de menos")
        ids = order["categories"]
        if not isinstance(ids, list) or not ids or len(ids) > 64 \
                or not all(isinstance(i, str) and _CATEGORY_ID.match(i) for i in ids):
            raise OrderError("categorías no válidas")
        return {"v": VERSION, "order": "clean", "categories": ids}
    if kind == "delete":
        if set(order) != {"v", "order", "paths"}:
            raise OrderError("campos de más o de menos")
        paths = order["paths"]
        if not isinstance(paths, list) or not paths or len(paths) > MAX_PATHS:
            raise OrderError("lista de rutas no válida")
        for p in paths:
            if not isinstance(p, str) or not p or len(p) > MAX_PATH_CHARS or "\0" in p or not os.path.isabs(p):
                raise OrderError("ruta no válida")
        return {"v": VERSION, "order": "delete", "paths": paths}
    raise OrderError("orden desconocida")


# =========================================================================
# Lado del auxiliar (proceso elevado)
# =========================================================================

def execute(order: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta una orden ya validada y devuelve el resultado. Aquí se revalida todo."""
    if order["order"] == "clean":
        from . import cleaner
        allowed = {c.id: c for c in cleaner.default_categories() if c.admin and not c.special}
        unknown = [i for i in order["categories"] if i not in allowed]
        if unknown:
            raise OrderError("categoría no permitida: " + ", ".join(unknown))
        freed = deleted = failed = 0
        notes = []
        for cat_id in order["categories"]:
            res = cleaner.clean(allowed[cat_id])
            freed, deleted, failed = freed + res.freed, deleted + res.deleted, failed + res.failed
            if res.note:
                notes.append(f"{allowed[cat_id].name}: {res.note}")
        return {"ok": failed == 0, "msg": "\n".join(notes), "freed": freed, "deleted": deleted, "failed": failed}
    from . import fileops
    ok, msg = fileops.delete_permanently(order["paths"])   # vuelve a pasar por check_deletable
    return {"ok": ok, "msg": msg}


def _read_order(path: str, digest: str) -> dict[str, Any]:
    if not _DIGEST.match(digest):
        raise OrderError("huella no válida")
    with open(path, "rb") as fh:
        data = fh.read(MAX_REQUEST + 1)
    if len(data) > MAX_REQUEST:
        raise OrderError("orden demasiado grande")
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), digest):
        raise OrderError("la orden no es la que se confirmó")
    return parse_order(data)


def _write_result(request: str, result: dict[str, Any]) -> None:
    # «x»: el archivo se crea o falla. Si alguien dejó ahí otro (o un enlace), no se escribe en él.
    with open(request + RESULT_SUFFIX, "x", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=True)


def main(argv: list[str]) -> int:
    """Punto de entrada del auxiliar: --auxiliar <archivo de la orden> --sha256 <huella>."""
    request = digest = ""
    try:
        request = argv[argv.index("--auxiliar") + 1]
        digest = argv[argv.index("--sha256") + 1].lower()
    except (ValueError, IndexError):
        return EXIT_REJECTED
    try:
        order = _read_order(request, digest)
        result = execute(order)
        code = EXIT_OK if result.get("ok") else EXIT_PARTIAL
    except (OrderError, OSError) as exc:
        log_action("auxiliar", request, f"orden rechazada: {exc}", ok=False)
        result, code = {"ok": False, "msg": i18n.t("helper.rejected", why=str(exc)), "rejected": True}, EXIT_REJECTED
    else:
        log_action("auxiliar", order["order"], str(result.get("msg", ""))[:500], ok=bool(result.get("ok")),
                   admin=plat.is_admin())
    try:
        _write_result(request, result)
    except OSError:
        return EXIT_REJECTED if code == EXIT_OK else code
    return code


# =========================================================================
# Lado de la ventana (usuario normal)
# =========================================================================

def _orders_dir() -> str:
    folder = os.path.join(plat.state_dir() or tempfile.gettempdir(), "ordenes")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return folder


def available() -> bool:
    return bool(plat.capabilities().get("elevate"))


def describe(order: dict[str, Any]) -> str:
    """El comando exacto que se lanzará con elevación, para enseñarlo en la confirmación."""
    exe, params = plat.helper_command(str(APP_ROOT / "app" / "main.py"), "<orden.json>", "<sha256>")
    return f'"{exe}" {params}'


def run(order: dict[str, Any]) -> dict[str, Any]:
    """Encarga una orden al auxiliar elevado y espera su resultado. Se llama desde un hilo
    de trabajo, DESPUÉS de que el usuario haya confirmado en pantalla qué se va a hacer."""
    order = parse_order(json.dumps(order).encode("utf-8"))   # lo mismo que comprobará el auxiliar
    data = json.dumps(order, ensure_ascii=True, sort_keys=True).encode("utf-8")
    fd, request = tempfile.mkstemp(prefix="orden-", suffix=".json", dir=_orders_dir())
    result_path = request + RESULT_SUFFIX
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        exe, params = plat.helper_command(str(APP_ROOT / "app" / "main.py"), request,
                                          hashlib.sha256(data).hexdigest())
        if not exe:
            return {"ok": False, "msg": i18n.t("linux.not_available"), "launched": False}
        launched, msg, code = plat.run_elevated(exe, params)
        log_action("auxiliar_lanzado", order["order"], f"{msg} (código {code})", ok=launched and code == EXIT_OK)
        if not launched:
            return {"ok": False, "msg": msg, "launched": False}
        try:
            with open(result_path, "rb") as fh:
                raw = fh.read(MAX_REQUEST + 1)
            result = json.loads(raw.decode("utf-8")) if len(raw) <= MAX_REQUEST else None
        except (OSError, ValueError):
            result = None
        if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
            return {"ok": False, "msg": i18n.t("helper.no_result", code=code), "launched": True}
        result["msg"] = str(result.get("msg", ""))
        result["launched"] = True
        return result
    finally:
        for leftover in (request, result_path):
            try:
                os.remove(leftover)
            except OSError:
                pass   # no llegó a crearse, o ya no está
