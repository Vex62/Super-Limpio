"""Escáner de disco: calcula cuánto pesa cada carpeta (recursivamente).

Diseño:
  * Recorrido iterativo con os.scandir (rápido: en Windows reutiliza los datos
    de FindFirstFile, sin llamadas extra a stat).
  * No sigue enlaces simbólicos ni puntos de unión (junctions), para no contar
    dos veces ni entrar en bucles.
  * Archivos de OneDrive «solo en la nube» no ocupan disco: se cuentan aparte.
  * Para no agotar memoria en discos con millones de archivos, cada carpeta
    guarda solo sus archivos más grandes; el resto se agrega en una fila.
"""

from __future__ import annotations

import heapq
import os
import queue
import stat as _stat
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from . import i18n
from .util import IS_WINDOWS
from .plat import CLOUD_ONLY_MASK, FILE_ATTRIBUTE_REPARSE_POINT

# Marcador interno para los archivos sin extensión (se traduce al mostrarlo)
NO_EXT = "\0no-ext"

FILES_KEPT_PER_DIR = 60     # archivos individuales que se muestran por carpeta
ALWAYS_KEEP = 64 * 1024 * 1024  # además, se guarda siempre cualquier archivo >= 64 MB
TOP_FILES = 500             # ranking global de archivos más grandes
MAX_WORKERS = 8             # carpetas leídas a la vez (más hilos no aporta nada)


class DirNode:
    __slots__ = ("name", "path", "parent", "size", "own_size", "files", "dirs", "mtime",
                 "children", "top_files", "small_files_count", "small_files_size",
                 "cloud_size", "errors", "done")

    def __init__(self, name: str, path: str, parent: "DirNode | None"):
        self.name = name
        self.path = path
        self.parent = parent
        self.size = 0            # tamaño total (recursivo)
        self.own_size = 0        # solo archivos directos
        self.files = 0           # nº archivos (recursivo)
        self.dirs = 0            # nº subcarpetas (recursivo)
        self.mtime = 0.0
        self.children: list[DirNode] = []
        self.top_files: list[tuple[int, str, float]] = []  # (tamaño, nombre, mtime)
        self.small_files_count = 0
        self.small_files_size = 0
        self.cloud_size = 0
        self.errors = 0
        self.done = False        # ya se ha leído su contenido

    def __repr__(self) -> str:  # pragma: no cover
        return f"DirNode({self.path!r}, {self.size})"


@dataclass
class ScanProgress:
    files: int = 0
    dirs: int = 0
    bytes: int = 0
    current: str = ""
    elapsed: float = 0.0


@dataclass
class ScanResult:
    root: DirNode
    top_files: list[tuple[int, str, float]]         # (tamaño, ruta, mtime) desc
    by_extension: dict[str, list[int]]              # ext -> [bytes, nº]
    errors: int
    cloud_size: int
    elapsed: float
    cancelled: bool = False
    skipped_links: int = 0
    error_samples: list[str] = field(default_factory=list)


def _is_link_or_junction(entry: os.DirEntry) -> bool:
    try:
        if entry.is_symlink():
            return True
        if IS_WINDOWS:
            st = entry.stat(follow_symlinks=False)
            return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return True
    return False


class _Worker:
    """Estado propio de cada hilo: se fusiona al final, sin bloqueos por archivo."""

    __slots__ = ("top_heap", "by_ext", "errors", "skipped_links", "error_samples")

    def __init__(self) -> None:
        self.top_heap: list[tuple[int, str, float]] = []
        self.by_ext: dict[str, list[int]] = {}
        self.errors = 0
        self.skipped_links = 0
        self.error_samples: list[str] = []


def _scan_dir(node: DirNode, w: _Worker) -> tuple[list[DirNode], int]:
    """Lee UNA carpeta. Devuelve (subcarpetas a visitar, bytes contados)."""
    children: list[DirNode] = []
    local_heap: list[tuple[int, str, float]] = []
    top_heap, by_ext = w.top_heap, w.by_ext
    own = cloud = nfiles = small_n = small_sz = 0
    try:
        with os.scandir(node.path) as it:
            for entry in it:
                try:
                    # Una sola consulta por entrada: en Windows no cuesta ninguna llamada
                    # al sistema (son los datos que ya trae la enumeración de la carpeta).
                    st = entry.stat(follow_symlinks=False)
                    mode = st.st_mode
                    attrs = st.st_file_attributes if IS_WINDOWS else 0
                    if attrs & FILE_ATTRIBUTE_REPARSE_POINT or _stat.S_ISLNK(mode):
                        w.skipped_links += 1
                        continue
                    name = entry.name
                    if _stat.S_ISDIR(mode):
                        child = DirNode(name, entry.path, node)
                        child.mtime = st.st_mtime
                        children.append(child)
                        continue
                    if not _stat.S_ISREG(mode):
                        continue
                    size = st.st_size
                    if attrs & CLOUD_ONLY_MASK:
                        cloud += size
                        size = 0
                    own += size
                    nfiles += 1
                    mtime = st.st_mtime
                    if size >= ALWAYS_KEEP:
                        node.top_files.append((size, name, mtime))
                    elif len(local_heap) < FILES_KEPT_PER_DIR:
                        heapq.heappush(local_heap, (size, name, mtime))
                    elif size > local_heap[0][0]:
                        small_sz += heapq.heapreplace(local_heap, (size, name, mtime))[0]
                        small_n += 1
                    else:
                        small_sz += size
                        small_n += 1
                    # Ranking global
                    if len(top_heap) < TOP_FILES:
                        heapq.heappush(top_heap, (size, entry.path, mtime))
                    elif size > top_heap[0][0]:
                        heapq.heapreplace(top_heap, (size, entry.path, mtime))
                    # Por tipo (mismo criterio que os.path.splitext, pero más barato)
                    dot = name.rfind(".")
                    if 0 < dot < len(name) - 1 and name[:dot].strip("."):
                        ext = name[dot:].lower()
                    else:
                        ext = NO_EXT
                    slot = by_ext.get(ext)
                    if slot is None:
                        by_ext[ext] = [size, 1]
                    else:
                        slot[0] += size
                        slot[1] += 1
                except OSError:
                    w.errors += 1
    except OSError as exc:
        w.errors += 1
        node.errors += 1
        if len(w.error_samples) < 50:
            w.error_samples.append(f"{node.path}: {exc.strerror or exc}")
    node.top_files.extend(local_heap)
    node.top_files.sort(reverse=True)
    node.children = children
    node.own_size = node.size = own
    node.files = nfiles
    node.cloud_size = cloud
    node.small_files_count = small_n
    node.small_files_size = small_sz
    node.done = True
    return children, own


def scan(root_path: str,
         progress: Callable[[ScanProgress], None] | None = None,
         cancel: threading.Event | None = None,
         progress_interval: float = 0.15,
         workers: int | None = None) -> ScanResult:
    """Analiza una carpeta completa.

    Varias carpetas se leen a la vez (la lectura de disco no bloquea al resto de
    hilos), lo que casi duplica la velocidad frente a un recorrido en serie. El
    avance se notifica desde el hilo que llama, cada `progress_interval` segundos.
    """
    t0 = time.monotonic()
    root_path = os.path.abspath(root_path)
    name = os.path.basename(root_path.rstrip("\\/")) or root_path
    root = DirNode(name, root_path, None)
    try:
        root.mtime = os.stat(root_path).st_mtime
    except OSError:
        pass

    n_workers = max(1, workers or min(MAX_WORKERS, os.cpu_count() or 2))
    todo: "queue.SimpleQueue[DirNode | None]" = queue.SimpleQueue()
    todo.put(root)
    lock = threading.Lock()
    finished = threading.Event()
    prog = ScanProgress()
    pending = 1                      # carpetas encoladas o en curso
    states = [_Worker() for _ in range(n_workers)]

    def work(w: _Worker) -> None:
        nonlocal pending
        while True:
            node = todo.get()
            if node is None:
                return
            children: list[DirNode] = []
            size = 0
            try:
                if cancel is None or not cancel.is_set():
                    children, size = _scan_dir(node, w)
            except Exception:  # noqa: BLE001 - un hilo caído dejaría el análisis colgado
                w.errors += 1
            finally:
                with lock:
                    pending += len(children) - 1
                    if node.done:
                        prog.dirs += 1
                        prog.files += node.files
                        prog.bytes += size
                        prog.current = node.path
                    if pending == 0:
                        finished.set()
            for child in children:
                todo.put(child)

    threads = [threading.Thread(target=work, args=(w,), daemon=True) for w in states]
    for t in threads:
        t.start()
    while not finished.wait(progress_interval):
        if progress:
            prog.elapsed = time.monotonic() - t0
            progress(prog)
    for _ in threads:
        todo.put(None)
    for t in threads:
        t.join()
    cancelled = cancel is not None and cancel.is_set()

    # Recorrido en preorden: cada carpeta aparece antes que sus subcarpetas. Las no
    # visitadas por cancelación se quitan para no mostrar ceros engañosos.
    order: list[DirNode] = []
    stack = [root]
    while stack:
        node = stack.pop()
        order.append(node)
        if cancelled:
            node.children = [c for c in node.children if c.done]
        stack.extend(node.children)
    # Propagación de tamaños de abajo arriba
    for node in reversed(order):
        node.children.sort(key=lambda n: n.size, reverse=True)
        par = node.parent
        if par is not None:
            par.size += node.size
            par.files += node.files
            par.dirs += node.dirs + 1
            par.cloud_size += node.cloud_size
            par.errors += node.errors

    by_ext: dict[str, list[int]] = {}
    error_samples: list[str] = []
    for w in states:
        for ext, (size, count) in w.by_ext.items():
            slot = by_ext.get(ext)
            if slot is None:
                by_ext[ext] = [size, count]
            else:
                slot[0] += size
                slot[1] += count
        error_samples.extend(w.error_samples)
    top = heapq.nlargest(TOP_FILES, (rec for w in states for rec in w.top_heap))
    elapsed = time.monotonic() - t0
    if progress:
        prog.elapsed = elapsed
        prog.current = ""
        progress(prog)
    return ScanResult(root, top, by_ext, sum(w.errors for w in states), root.cloud_size, elapsed,
                      cancelled, sum(w.skipped_links for w in states), error_samples[:50])


def quick_folder_size(path: str, cancel: threading.Event | None = None) -> tuple[int, int]:
    """Tamaño total y nº de archivos de una carpeta, sin guardar estructura."""
    total = 0
    count = 0
    stack = [path]
    while stack:
        if cancel is not None and cancel.is_set():
            break
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for entry in it:
                    try:
                        st = entry.stat(follow_symlinks=False)
                        mode = st.st_mode
                        attrs = st.st_file_attributes if IS_WINDOWS else 0
                        if attrs & FILE_ATTRIBUTE_REPARSE_POINT or _stat.S_ISLNK(mode):
                            continue
                        if _stat.S_ISDIR(mode):
                            stack.append(entry.path)
                        elif not attrs & CLOUD_ONLY_MASK:
                            total += st.st_size
                            count += 1
                    except OSError:
                        continue
        except OSError:
            continue
    return total, count


# Pistas para entender de un vistazo qué es una carpeta grande (valor = clave de i18n)
FOLDER_HINTS = {
    "node_modules": "hint.folder.node_modules",
    ".venv": "hint.folder.venv_dot",
    "venv": "hint.folder.venv",
    "__pycache__": "hint.folder.pycache",
    ".gradle": "hint.folder.gradle",
    ".m2": "hint.folder.m2",
    ".nuget": "hint.folder.nuget",
    ".cargo": "hint.folder.cargo",
    "target": "hint.folder.target",
    "winsxs": "hint.folder.winsxs",
    "installer": "hint.folder.installer",
    "softwaredistribution": "hint.folder.softwaredistribution",
    "temp": "hint.folder.temp",
    "cache": "hint.folder.cache",
    "crashdumps": "hint.folder.crashdumps",
    "steamapps": "hint.folder.steamapps",
    "docker": "hint.folder.docker",
    "wsl": "hint.folder.wsl",
    "onedrive": "hint.folder.onedrive",
    "downloads": "hint.folder.downloads",
    "descargas": "hint.folder.downloads",
    "$recycle.bin": "hint.folder.recyclebin",
    "system volume information": "hint.folder.svi",
    "packages": "hint.folder.packages",
    "windowsapps": "hint.folder.windowsapps",
    "program files": "hint.folder.programfiles",
    "program files (x86)": "hint.folder.programfiles86",
}

FILE_HINTS = {
    "pagefile.sys": "hint.file.pagefile",
    "hiberfil.sys": "hint.file.hiberfil",
    "swapfile.sys": "hint.file.swapfile",
    "memory.dmp": "hint.file.memorydmp",
    "ext4.vhdx": "hint.file.ext4vhdx",
}

EXT_HINTS = {
    ".iso": "hint.ext.iso", ".vhdx": "hint.ext.vhdx", ".vhd": "hint.ext.vhdx",
    ".vmdk": "hint.ext.vmdk", ".dmp": "hint.ext.dmp", ".msi": "hint.ext.msi",
    ".exe": "hint.ext.exe", ".zip": "hint.ext.archive", ".7z": "hint.ext.archive",
    ".rar": "hint.ext.archive", ".mp4": "hint.ext.video", ".mkv": "hint.ext.video", ".mov": "hint.ext.video",
    ".log": "hint.ext.log", ".tmp": "hint.ext.tmp", ".bak": "hint.ext.bak", ".pst": "hint.ext.pst",
    ".ost": "hint.ext.ost",
}


def hint_for(name: str, is_dir: bool) -> str:
    low = name.lower()
    if is_dir:
        key = FOLDER_HINTS.get(low)
    elif low in FILE_HINTS:
        key = FILE_HINTS[low]
    else:
        key = EXT_HINTS.get(os.path.splitext(low)[1])
    return i18n.t(key) if key else ""


def ext_desc(ext: str) -> str:
    """Descripción traducida de una extensión (o cadena vacía si no hay)."""
    key = EXT_HINTS.get(ext)
    return i18n.t(key) if key else ""


def ext_display(ext: str) -> str:
    """Texto a mostrar para una extensión en la tabla «por tipo»."""
    return i18n.t("scanner.no_ext") if ext == NO_EXT else ext


def file_type_label(ext: str) -> str:
    """Etiqueta de tipo para la columna «Tipo» de la pestaña de archivos."""
    key = EXT_HINTS.get(ext)
    if key:
        return i18n.t(key)
    return ext.lstrip(".").upper() or i18n.t("util.file")
