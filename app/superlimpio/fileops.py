"""Operaciones de borrado con comprobaciones de seguridad y registro.

Reglas que se cumplen aquí, además de las de `safety.check_deletable`:
  * Nunca se sigue un enlace simbólico ni un junction: se quita el enlace, no su destino.
  * El tipo de cada elemento se vuelve a mirar justo antes de tocarlo: entre que se
    analizó y se borra, una carpeta pudo cambiarse por un enlace.
  * Un fallo no detiene el lote: se sigue con lo demás y el resumen dice qué pasó de verdad.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import threading
from typing import Any

from . import i18n, plat
from .safety import check_deletable, log_action
from .util import is_link, long_path


def validate(paths: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Separa las rutas en (permitidas, [(bloqueada, motivo)])."""
    ok, blocked = [], []
    for p in paths:
        chk = check_deletable(p)
        if chk.allowed:
            ok.append(p)
        else:
            blocked.append((p, chk.reason))
    return ok, blocked


def _present(paths: list[str]) -> tuple[list[str], int]:
    """(los que siguen existiendo, cuántos han desaparecido desde que se analizaron)."""
    here = [p for p in paths if os.path.lexists(long_path(p))]
    return here, len(paths) - len(here)


def _gone_note(gone: int) -> str:
    return "\n" + i18n.t("fileops.gone", n=gone) if gone else ""


def recycle(paths: list[str], cancel: threading.Event | None = None) -> tuple[bool, str]:
    allowed, blocked = validate(paths)
    if blocked:
        msg = "; ".join(f"{p}: {r}" for p, r in blocked)
        log_action("papelera", ", ".join(paths), "bloqueado: " + msg, ok=False)
        return False, i18n.t("fileops.blocked", msg=msg)
    if cancel is not None and cancel.is_set():
        return False, i18n.t("fileops.cancelled", done=0, total=len(allowed))
    allowed, gone = _present(allowed)
    ok, msg = plat.send_to_recycle_bin(allowed)
    msg += _gone_note(gone)
    log_action("papelera", " | ".join(allowed), msg, ok=ok)
    return ok, msg


# =========================================================================
# Borrado definitivo
# =========================================================================

def _writable_retry(func: Any, path: str) -> None:
    """Quita el atributo de solo lectura y reintenta una vez. Solo sobre el propio
    elemento (ya validado y que no es un enlace): chmod sí seguiría un enlace."""
    try:
        func(long_path(path))
    except PermissionError:
        st = os.lstat(long_path(path))
        if is_link(st) or st.st_mode & stat.S_IWRITE:
            raise
        os.chmod(long_path(path), stat.S_IWRITE | stat.S_IREAD)
        func(long_path(path))


def _remove_link(path: str) -> None:
    """Quita un enlace o junction sin tocar aquello a lo que apunta."""
    try:
        os.unlink(long_path(path))
    except OSError:
        os.rmdir(long_path(path))   # los junctions de carpeta, según la versión de Python


def _remove_tree(top: str, cancel: threading.Event | None, errors: list[str]) -> None:
    """Borra una carpeta recorriéndola a mano. Es lo que hace shutil.rmtree donde es
    resistente a los ataques con enlaces (Linux); en Windows no lo es, así que aquí cada
    entrada se mira con lstat y en un enlace o junction nunca se entra."""
    stack, folders = [top], []
    while stack:
        if cancel is not None and cancel.is_set():
            return
        folder = stack.pop()
        try:
            if is_link(os.lstat(long_path(folder))):   # se cambió por un enlace mientras tanto
                _remove_link(folder)
                continue
            folders.append(folder)
            with os.scandir(long_path(folder)) as it:
                entries = [(e.name, e.stat(follow_symlinks=False)) for e in it]
        except OSError as exc:
            errors.append(f"{folder}: {exc.strerror or exc}")
            continue
        for name, st in entries:
            full = os.path.join(folder, name)
            try:
                if is_link(st):
                    _remove_link(full)
                elif stat.S_ISDIR(st.st_mode):
                    stack.append(full)
                else:
                    _writable_retry(os.unlink, full)
            except OSError as exc:
                errors.append(f"{full}: {exc.strerror or exc}")
    for folder in reversed(folders):   # de la más profunda a la primera
        try:
            _writable_retry(os.rmdir, folder)
        except OSError as exc:
            # Si no se vació porque falló algo de dentro, ese fallo ya está anotado.
            if not any(e.startswith(folder + os.sep) for e in errors):
                errors.append(f"{folder}: {exc.strerror or exc}")


def _remove_any(path: str, cancel: threading.Event | None, errors: list[str]) -> None:
    st = os.lstat(long_path(path))   # el tipo, justo antes de actuar
    if is_link(st):
        _remove_link(path)
    elif not stat.S_ISDIR(st.st_mode):
        _writable_retry(os.unlink, path)
    elif shutil.rmtree.avoids_symlink_attacks:
        # Linux: rmtree trabaja con descriptores de carpeta y no se deja engañar por enlaces.
        def on_error(_func: Any, target: Any, exc: Any) -> None:
            if isinstance(exc, tuple):   # Python < 3.12 entrega (tipo, valor, traza)
                exc = exc[1]
            errors.append(f"{target}: {getattr(exc, 'strerror', None) or exc}")
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=on_error)
        else:
            shutil.rmtree(path, onerror=on_error)
    else:
        _remove_tree(path, cancel, errors)


def delete_permanently(paths: list[str], cancel: threading.Event | None = None) -> tuple[bool, str]:
    allowed, blocked = validate(paths)
    if blocked:
        msg = "; ".join(f"{p}: {r}" for p, r in blocked)
        log_action("borrado_definitivo", ", ".join(paths), "bloqueado: " + msg, ok=False)
        return False, i18n.t("fileops.blocked", msg=msg)
    errors: list[str] = []
    done = gone = 0
    stopped = False
    for p in allowed:
        if cancel is not None and cancel.is_set():
            stopped = True
            break
        before = len(errors)
        try:
            _remove_any(p, cancel, errors)
        except FileNotFoundError:
            gone += 1   # desapareció entre el análisis y el borrado: no es un fallo
            continue
        except OSError as exc:
            errors.append(f"{p}: {exc.strerror or exc}")
        if os.path.lexists(long_path(p)):
            if len(errors) == before and not (cancel is not None and cancel.is_set()):
                errors.append(i18n.t("fileops.in_use", path=p))
        else:
            done += 1
    ok = not errors and not stopped
    if stopped or (cancel is not None and cancel.is_set()):
        ok = False
        msg = i18n.t("fileops.cancelled", done=done, total=len(allowed))
        if errors:
            msg += "\n" + "\n".join(errors[:20])
    elif errors:
        msg = i18n.t("fileops.some_failed", items="\n".join(errors[:20]))
        if len(errors) > 20:
            msg += "\n" + i18n.t("dialog.more_items", n=len(errors) - 20)
    else:
        msg = i18n.t("fileops.deleted_perm")
    msg += _gone_note(gone)
    log_action("borrado_definitivo", " | ".join(allowed), msg, ok=ok, borrados=done, fallos=len(errors))
    return ok, msg
