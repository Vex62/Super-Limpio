"""Preferencias del usuario (idioma, tamaño de la interfaz y divisores de paneles).

Se guardan en un archivo JSON. Primero se intenta junto a la app (modo portable);
si esa carpeta es de solo lectura, se usa %LOCALAPPDATA%\\SuperLimpio. El archivo de
configuración NO forma parte de la distribución firmada (es un dato del usuario), así
que escribirlo nunca invalida la comprobación de integridad.

Resiliencia frente a cierres forzados:
  * La escritura es atómica (archivo temporal + os.replace), así un corte a mitad de
    guardado nunca deja el archivo a medias.
  * Antes de reemplazarlo se conserva una copia .bak del último estado válido.
  * Al leer, si el JSON está corrupto se recurre a .bak y, si tampoco, se aparta el
    archivo dañado (.corrupt) y se parte de los valores por defecto. La app nunca
    deja de arrancar por una configuración rota.
"""

from __future__ import annotations

import json
import os
import shutil

from .util import APP_ROOT, IS_WINDOWS

_FILENAME = "superlimpio.config.json"

DEFAULTS: dict = {
    "language": None,       # None = aún sin elegir (se detecta del sistema la primera vez)
    "ui_scale": 1.0,        # multiplicador de zoom de la interfaz (0.8 .. 1.6)
    "sashes": {},           # posición de los divisores arrastrables, por vista
}

MIN_SCALE, MAX_SCALE, SCALE_STEP = 0.8, 1.6, 0.1

_data: dict | None = None
_path: str | None = None


def _candidate_paths() -> list[str]:
    paths = [os.path.join(str(APP_ROOT), _FILENAME)]
    if IS_WINDOWS:
        base = os.environ.get("LOCALAPPDATA")
        if base:
            paths.append(os.path.join(base, "SuperLimpio", _FILENAME))
    else:
        paths.append(os.path.join(os.path.expanduser("~/.config/superlimpio"), _FILENAME))
    return paths


def _read_json(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            stored = json.load(fh)
        return stored if isinstance(stored, dict) else None
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return None


def _load() -> None:
    global _data, _path
    if _data is not None:
        return
    for candidate in _candidate_paths():
        if not os.path.exists(candidate) and not os.path.exists(candidate + ".bak"):
            continue
        stored = _read_json(candidate)
        if stored is None:
            stored = _read_json(candidate + ".bak")   # el primario estaba corrupto o faltaba
            if stored is None and os.path.exists(candidate):
                try:  # apartar el archivo dañado para no volver a leerlo
                    os.replace(candidate, candidate + ".corrupt")
                except OSError:
                    pass
        if stored is not None:
            _data = {**DEFAULTS, **stored}
            _path = candidate
            return
    _data = dict(DEFAULTS)
    _path = None


def reset_to_defaults(quarantine: bool = True) -> None:
    """Descarta la configuración actual y vuelve a los valores por defecto.

    Si quarantine=True, los archivos existentes se conservan con sufijo .corrupt
    por si hay que inspeccionarlos; no se borran."""
    global _data, _path
    for candidate in _candidate_paths():
        for suffix in ("", ".bak"):
            p = candidate + suffix
            if os.path.exists(p):
                try:
                    os.replace(p, p + ".corrupt") if quarantine else os.remove(p)
                except OSError:
                    pass
    _data = dict(DEFAULTS)
    _path = None


def get(key: str, default=None):
    _load()
    assert _data is not None
    return _data.get(key, DEFAULTS.get(key, default))


def set(key: str, value) -> None:
    _load()
    assert _data is not None
    _data[key] = value
    _save()


def _atomic_write(path: str, text: str) -> bool:
    d = os.path.dirname(path)
    try:
        os.makedirs(d, exist_ok=True)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        if os.path.exists(path):   # conservar el último estado válido como respaldo
            try:
                shutil.copy2(path, path + ".bak")
            except OSError:
                pass
        os.replace(tmp, path)      # reemplazo atómico: nunca queda un archivo a medias
        return True
    except OSError:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False


def _save() -> None:
    global _path
    assert _data is not None
    text = json.dumps(_data, ensure_ascii=False, indent=2)
    targets = [_path] if _path else []
    targets += [p for p in _candidate_paths() if p != _path]
    for candidate in targets:
        if candidate and _atomic_write(candidate, text):
            _path = candidate
            return


def state_dir() -> str:
    """Carpeta escribible para archivos de estado (p. ej. la marca de arranque)."""
    _load()
    if _path:
        return os.path.dirname(_path)
    for c in _candidate_paths():
        d = os.path.dirname(c)
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except OSError:
            continue
    return os.path.dirname(_candidate_paths()[0])


def clamp_scale(value: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 1.0
    return max(MIN_SCALE, min(MAX_SCALE, round(value, 2)))


def get_scale() -> float:
    return clamp_scale(get("ui_scale", 1.0))


def set_scale(value: float) -> float:
    value = clamp_scale(value)
    set("ui_scale", value)
    return value


def get_sash(view: str, name: str, default: int | None = None) -> int | None:
    sashes = get("sashes", {}) or {}
    try:
        return int(sashes.get(view, {}).get(name, default))
    except (TypeError, ValueError, AttributeError):
        return default


def set_sash(view: str, name: str, value: int) -> None:
    sashes = dict(get("sashes", {}) or {})
    view_map = dict(sashes.get(view, {}) or {})
    view_map[name] = int(value)
    sashes[view] = view_map
    set("sashes", sashes)
