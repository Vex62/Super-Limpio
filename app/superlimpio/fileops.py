"""Operaciones de borrado con comprobaciones de seguridad y registro."""

from __future__ import annotations

import os
import shutil
import stat

from . import i18n, winapi
from .safety import check_deletable, log_action


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


def recycle(paths: list[str]) -> tuple[bool, str]:
    allowed, blocked = validate(paths)
    if blocked:
        msg = "; ".join(f"{p}: {r}" for p, r in blocked)
        log_action("papelera", ", ".join(paths), "bloqueado: " + msg, ok=False)
        return False, i18n.t("fileops.blocked", msg=msg)
    ok, msg = winapi.send_to_recycle_bin(allowed)
    log_action("papelera", " | ".join(allowed), msg, ok=ok)
    return ok, msg


def _on_rm_error(func, path, exc):
    # Quita el atributo de solo lectura y reintenta una vez
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def delete_permanently(paths: list[str]) -> tuple[bool, str]:
    allowed, blocked = validate(paths)
    if blocked:
        msg = "; ".join(f"{p}: {r}" for p, r in blocked)
        log_action("borrado_definitivo", ", ".join(paths), "bloqueado: " + msg, ok=False)
        return False, i18n.t("fileops.blocked", msg=msg)
    errors = []
    for p in allowed:
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                try:
                    shutil.rmtree(p, onexc=_on_rm_error)  # Python 3.12+
                except TypeError:
                    shutil.rmtree(p, onerror=lambda f, pa, ei: _on_rm_error(f, pa, ei[1]))
            else:
                try:
                    os.remove(p)
                except PermissionError:
                    os.chmod(p, stat.S_IWRITE)
                    os.remove(p)
        except OSError as exc:
            errors.append(f"{p}: {exc.strerror or exc}")
        if os.path.exists(p) and not any(e.startswith(p) for e in errors):
            errors.append(i18n.t("fileops.in_use", path=p))
    ok = not errors
    msg = i18n.t("fileops.deleted_perm") if ok else i18n.t("fileops.some_failed",
                                                           items="\n".join(errors[:20]))
    log_action("borrado_definitivo", " | ".join(allowed), msg, ok=ok)
    return ok, msg
