"""Buscador de librerías y artefactos de desarrollo regenerables.

Encuentra carpetas como node_modules, entornos virtuales de Python o salidas de
compilación dentro de tus proyectos. Solo se marcan como candidatas cuando hay
indicios claros (p. ej. «target» solo si junto a ella existe Cargo.toml).
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from collections.abc import Callable

from . import i18n
from .scanner import _is_link_or_junction, quick_folder_size, refuse_virtual
from .util import IS_WINDOWS, long_path

# nombre -> (clave i18n del tipo, archivo marcador requerido (None = sin requisito), dónde buscarlo)
RULES: dict[str, tuple[str, str | None, str]] = {
    "node_modules": ("devkind.node", None, ""),
    ".venv": ("devkind.venv", "pyvenv.cfg", "inside"),
    "venv": ("devkind.venv", "pyvenv.cfg", "inside"),
    "env": ("devkind.venv", "pyvenv.cfg", "inside"),
    "__pycache__": ("devkind.pycache", None, ""),
    ".pytest_cache": ("devkind.pytest", None, ""),
    ".mypy_cache": ("devkind.mypy", None, ""),
    ".ruff_cache": ("devkind.ruff", None, ""),
    ".tox": ("devkind.tox", None, ""),
    "target": ("devkind.rustmaven", "Cargo.toml|pom.xml", "sibling"),
    ".gradle": ("devkind.gradlecache", "build.gradle|build.gradle.kts|settings.gradle", "sibling"),
    "build": ("devkind.gradlecmake", "build.gradle|build.gradle.kts|CMakeLists.txt", "sibling"),
    ".next": ("devkind.next", "package.json", "sibling"),
    ".nuxt": ("devkind.nuxt", "package.json", "sibling"),
    ".angular": ("devkind.angular", "angular.json", "sibling"),
    ".parcel-cache": ("devkind.parcel", None, ""),
    ".turbo": ("devkind.turbo", None, ""),
    "obj": ("devkind.dotnet_obj", "*.csproj|*.fsproj|*.vbproj", "sibling"),
    "bin": ("devkind.dotnet_bin", "*.csproj|*.fsproj|*.vbproj", "sibling"),
    "dist-newstyle": ("devkind.haskell", None, ""),
    ".dart_tool": ("devkind.dart", "pubspec.yaml", "sibling"),
    "Pods": ("devkind.cocoapods", "Podfile", "sibling"),
}

SKIP_DIRS = {"$recycle.bin", "system volume information", "windows", "program files",
             "program files (x86)", "programdata", "appdata", ".git", ".hg", ".svn"}


@dataclass
class DevArtifact:
    path: str
    kind: str
    project: str
    size: int = 0
    files: int = 0
    mtime: float = 0.0


def _marker_ok(parent: str, folder: str, marker: str | None, where: str) -> bool:
    if marker is None:
        return True
    base = os.path.join(parent, folder) if where == "inside" else parent
    try:
        names = os.listdir(base)
    except OSError:
        return False
    lower = [n.lower() for n in names]
    for m in marker.split("|"):
        m = m.lower()
        if m.startswith("*"):
            if any(n.endswith(m[1:]) for n in lower):
                return True
        elif m in lower:
            return True
    return False


def find_artifacts(root: str,
                   progress: Callable[[str, int], None] | None = None,
                   cancel: threading.Event | None = None,
                   measure: bool = True) -> list[DevArtifact]:
    found: list[DevArtifact] = []
    refuse_virtual(root)
    stack = [root]
    visited = 0
    root_dev: int | None = None
    if not IS_WINDOWS:   # no se sale a otros discos montados dentro de la carpeta
        try:
            root_dev = os.stat(root).st_dev
        except OSError:
            return found
    while stack:
        if cancel is not None and cancel.is_set():
            break
        cur = stack.pop()
        visited += 1
        if progress and visited % 200 == 0:
            progress(cur, len(found))
        try:
            with os.scandir(long_path(cur)) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            try:
                if not e.is_dir(follow_symlinks=False) or _is_link_or_junction(e):
                    continue
                st = e.stat(follow_symlinks=False)
            except OSError:
                continue
            if root_dev is not None and st.st_dev != root_dev:
                continue
            full = os.path.join(cur, e.name)
            rule = RULES.get(e.name) or RULES.get(e.name.lower())
            if rule and _marker_ok(cur, e.name, rule[1], rule[2]):
                art = DevArtifact(full, i18n.t(rule[0]), cur, mtime=st.st_mtime)
                if measure:
                    art.size, art.files = quick_folder_size(full, cancel)
                found.append(art)
                continue  # no se entra dentro de un artefacto
            if e.name.lower() in SKIP_DIRS:
                continue
            stack.append(full)
    found.sort(key=lambda a: a.size, reverse=True)
    return found
