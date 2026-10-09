"""Importancia de un proceso o de un archivo para el sistema: qué es y qué pasa si se toca.

`safety` decide si algo se PUEDE borrar o finalizar; este módulo lo explica. A cada
proceso y a cada ruta le pone un nivel (normal, precaución, importante o vital), una
frase que dice qué es y otra con el riesgo de cerrarlo o borrarlo. Se usa para avisar
en «Memoria y procesos», en el análisis de «Optimizar» y en el «Analizador de disco».

Qué es vital depende del sistema operativo: las tablas viven en `plat/windows_know.py`
y `plat/linux_know.py`. Aquí solo está lo común. Es lógica pura (sin interfaz ni
llamadas al sistema), para poder probarla con tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import IntEnum

from . import i18n, plat
from .plat import know
from .safety import check_deletable
from .util import APP_ROOT


class Level(IntEnum):
    NORMAL = 0       # programa o archivo corriente: no afecta al sistema
    CAUTION = 1      # se puede cerrar o borrar, pero algo deja de funcionar o se pierde
    IMPORTANT = 2    # componente del sistema, de seguridad o de un programa instalado
    VITAL = 3        # sin él el sistema se detiene o no arranca

    @property
    def label(self) -> str:
        return i18n.t(f"crit.level.{int(self)}")


@dataclass(frozen=True)
class Assessment:
    level: Level
    what: str        # qué es
    risk: str        # qué pasa si se cierra o se borra
    kind: str = ""   # «self» = la propia aplicación
    system: bool = False   # es del propio sistema y borrarlo lo daña (solo rutas)

    @property
    def label(self) -> str:
        return self.level.label

    @property
    def text(self) -> str:
        return f"{self.what} {self.risk}".strip()


def _a(level: int, what: str, risk: str, kind: str = "", system: bool = False) -> Assessment:
    return Assessment(Level(level), i18n.t(what), i18n.t(risk), kind, system)


# Se mantienen como nombres del módulo porque forman parte de su interfaz
# (`criticality.SECURITY_PROCESSES`...), pero siempre reflejan el sistema activo.
_KNOWLEDGE_NAMES = ("SECURITY_PROCESSES", "SECURITY_PATHS", "PROTECTED_PROCESSES", "SENSITIVE_PROCESSES")


def __getattr__(name: str):
    if name in _KNOWLEDGE_NAMES:
        return getattr(know, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# =========================================================================
# Procesos
# =========================================================================

def assess_process(name: str, path: str = "", pid: int = -1, accessible: bool = True,
                   service: bool = False, windir: str | tuple[str, ...] | None = None,
                   self_pid: int | None = None) -> Assessment:
    """Qué es un proceso y qué pasa si se finaliza. «windir» son las carpetas del sistema
    (por defecto, las de este equipo)."""
    if pid >= 0 and pid == (os.getpid() if self_pid is None else self_pid):
        return _a(Level.NORMAL, "crit.proc.self", "crit.risk.self", kind="self")
    sysdirs = know.system_dirs() if windir is None else ((windir,) if isinstance(windir, str) else tuple(windir))
    return _a(*know.process_info(name, path, pid, accessible, service, sysdirs))


# =========================================================================
# Archivos y carpetas
# =========================================================================

_ENV: dict[str, dict] = {}


def real_env() -> dict[str, object]:
    """Las carpetas del sistema de este equipo, según el sistema activo."""
    if know.name not in _ENV:
        _ENV[know.name] = know.path_env(str(APP_ROOT))
    return _ENV[know.name]


def assess_path(path: str, env: dict | None = None, strict: bool = True) -> Assessment:
    """Qué es un archivo o carpeta y qué pasa si se borra.

    Con strict=True, lo que `safety.check_deletable` bloquea nunca sale como «normal».
    «env» permite fijar las carpetas del sistema (para los tests)."""
    found = know.classify_path(know.norm(path), env if env is not None else real_env())
    if found is not None:
        level, what, risk = found
        return _a(level, what, risk, system=what in know.SYSTEM_DAMAGE)
    if strict and env is None and know.name == plat.NAME:
        chk = check_deletable(path)
        if not chk.allowed:
            return Assessment(Level.IMPORTANT, chk.reason, i18n.t("crit.prisk.important"))
    return _a(Level.NORMAL, "crit.path.normal", "crit.prisk.normal")


def worst(items: list[Assessment]) -> Assessment | None:
    """La valoración más grave de una lista (None si está vacía)."""
    return max(items, key=lambda a: a.level, default=None)
