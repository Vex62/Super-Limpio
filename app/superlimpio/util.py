"""Utilidades comunes: formato de tamaños, fechas y rutas de la app."""

from __future__ import annotations

import datetime as _dt
import os
import stat as _stat
from pathlib import Path

from . import i18n, plat

IS_WINDOWS = plat.IS_WINDOWS

# Carpeta raíz de la app portable (la que contiene SuperLimpio.exe)
APP_ROOT = Path(__file__).resolve().parents[2]
# El registro de acciones es un dato del usuario: vive en su carpeta de estado
# (%LOCALAPPDATA%\SuperLimpio en Windows, ~/.local/state/superlimpio en Linux), no junto
# a la aplicación, que puede estar en una carpeta de solo lectura o compartida.
LOG_DIR = Path(plat.state_dir() or APP_ROOT) / "logs"

# Una sola convención de tamaños en toda la aplicación: base 1024, con sus nombres (KiB, MiB…).
_UNITS = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")

_REPARSE_POINT = 0x400   # FILE_ATTRIBUTE_REPARSE_POINT (solo existe en Windows)
_LONG_PATH_AT = 248      # a partir de aquí Windows necesita el prefijo \\?\ (el límite de carpeta)


def is_link(st: os.stat_result) -> bool:
    """True si esa entrada es un enlace simbólico, un junction o cualquier otro punto de
    reanálisis: algo que no se debe seguir ni borrar por dentro."""
    return _stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & _REPARSE_POINT)


def long_path(path: str) -> str:
    """En Windows, la misma ruta con el prefijo que admite más de 260 caracteres. Solo para
    rutas absolutas ya validadas: con el prefijo, Windows no normaliza nada."""
    if not IS_WINDOWS or len(path) < _LONG_PATH_AT or path.startswith("\\\\?\\"):
        return path
    path = os.path.abspath(path)
    if path.startswith("\\\\"):
        return "\\\\?\\UNC\\" + path[2:]
    return "\\\\?\\" + path


def _localize_number(s: str) -> str:
    """Convierte un número con formato estándar (coma de millares, punto decimal)
    al separador del idioma activo: en español se intercambian coma y punto."""
    if i18n.current() == "es":
        return s.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return s


def fmt_size(num: float | int | None) -> str:
    """Formatea bytes con base 1024, como hace el Explorador de Windows."""
    if num is None:
        return "—"
    num = float(num)
    if num < 1024:
        return f"{int(num)} B"
    for unit in _UNITS[1:]:
        num /= 1024.0
        if num < 1024 or unit == _UNITS[-1]:
            if num >= 100:
                return f"{_localize_number(f'{num:,.0f}')} {unit}"
            return f"{_localize_number(f'{num:.1f}')} {unit}"
    return f"{_localize_number(f'{num:.1f}')} {_UNITS[-1]}"


def fmt_count(n: int | None) -> str:
    if n is None:
        return "—"
    return _localize_number(f"{n:,}")


def fmt_date(ts: float | None) -> str:
    if not ts:
        return ""
    fmt = "%d/%m/%Y %H:%M" if i18n.current() == "es" else "%Y-%m-%d %H:%M"
    try:
        return _dt.datetime.fromtimestamp(ts).strftime(fmt)
    except (OverflowError, OSError, ValueError):
        return ""


def fmt_pct(part: float, total: float) -> str:
    if not total:
        return i18n.percent("0")
    return i18n.percent(_localize_number(f"{(part / total) * 100:.1f}"))


def text_bar(part: float, total: float, width: int = 12) -> str:
    """Barra de texto para ver de un vistazo el peso relativo."""
    if not total or part <= 0:
        return "░" * width
    frac = max(0.0, min(1.0, part / total))
    full = int(round(frac * width))
    if full == 0 and frac > 0:
        full = 1
    return "█" * full + "░" * (width - full)


def expand(path: str) -> str:
    """Expande %VARIABLES% y ~ de forma segura."""
    return os.path.normpath(os.path.expanduser(os.path.expandvars(path)))


def norm_key(path: str) -> str:
    """Clave normalizada para comparar rutas (insensible a mayúsculas en Windows)."""
    p = os.path.normpath(os.path.abspath(path))
    return os.path.normcase(p).rstrip("\\/") or p
