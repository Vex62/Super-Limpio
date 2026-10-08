"""Buscador de librerías y artefactos de desarrollo regenerables.

Encuentra carpetas como node_modules, entornos virtuales de Python o salidas de
compilación dentro de tus proyectos. Solo se marcan como candidatas cuando hay
indicios claros (p. ej. «target» solo si junto a ella existe Cargo.toml).
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Callable

from .scanner import _is_link_or_junction, quick_folder_size

# nombre -> (tipo, archivo marcador requerido dentro/junto (None = sin requisito), dónde buscarlo)
RULES: dict[str, tuple[str, str | None, str]] = {
    "node_modules": ("Dependencias Node (npm/yarn/pnpm)", None, ""),
    ".venv": ("Entorno virtual Python", "pyvenv.cfg", "inside"),
    "venv": ("Entorno virtual Python", "pyvenv.cfg", "inside"),
    "env": ("Entorno virtual Python", "pyvenv.cfg", "inside"),
    "__pycache__": ("Bytecode Python", None, ""),
    ".pytest_cache": ("Caché de pytest", None, ""),
    ".mypy_cache": ("Caché de mypy", None, ""),
    ".ruff_cache": ("Caché de ruff", None, ""),
    ".tox": ("Entornos tox", None, ""),
    "target": ("Compilación Rust/Maven", "Cargo.toml|pom.xml", "sibling"),
    ".gradle": ("Caché Gradle del proyecto", "build.gradle|build.gradle.kts|settings.gradle", "sibling"),
    "build": ("Compilación Gradle/CMake", "build.gradle|build.gradle.kts|CMakeLists.txt", "sibling"),
    ".next": ("Compilación Next.js", "package.json", "sibling"),
    ".nuxt": ("Compilación Nuxt", "package.json", "sibling"),
    ".angular": ("Caché Angular", "angular.json", "sibling"),
    ".parcel-cache": ("Caché Parcel", None, ""),
    ".turbo": ("Caché Turborepo", None, ""),
    "obj": (".NET intermedios", "*.csproj|*.fsproj|*.vbproj", "sibling"),
    "bin": (".NET compilados", "*.csproj|*.fsproj|*.vbproj", "sibling"),
    "dist-newstyle": ("Compilación Haskell", None, ""),
    ".dart_tool": ("Herramientas Dart/Flutter", "pubspec.yaml", "sibling"),
    "Pods": ("Dependencias CocoaPods", "Podfile", "sibling"),
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
    stack = [root]
    visited = 0
    while stack:
        if cancel is not None and cancel.is_set():
            break
        cur = stack.pop()
        visited += 1
        if progress and visited % 200 == 0:
            progress(cur, len(found))
        try:
            with os.scandir(cur) as it:
                entries = [e for e in it]
        except OSError:
            continue
        for e in entries:
            try:
                if not e.is_dir(follow_symlinks=False) or _is_link_or_junction(e):
                    continue
            except OSError:
                continue
            rule = RULES.get(e.name) or RULES.get(e.name.lower())
            if rule and _marker_ok(cur, e.name, rule[1], rule[2]):
                art = DevArtifact(e.path, rule[0], cur)
                try:
                    art.mtime = e.stat(follow_symlinks=False).st_mtime
                except OSError:
                    pass
                if measure:
                    art.size, art.files = quick_folder_size(e.path, cancel)
                found.append(art)
                continue  # no se entra dentro de un artefacto
            if e.name.lower() in SKIP_DIRS:
                continue
            stack.append(e.path)
    found.sort(key=lambda a: a.size, reverse=True)
    return found
