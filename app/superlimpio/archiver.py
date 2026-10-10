"""Compresor de archivos: crea .7z y .zip como lo harían 7-Zip o WinRAR.

  * 7z  — un único bloque sólido LZMA2 (todos los archivos se comprimen juntos, que es
          lo que da los mejores índices). Con contraseña: AES-256 y cabecera cifrada,
          de modo que tampoco se ven los nombres de los archivos.
  * zip — Deflate, lo abre cualquier sistema. Con contraseña: AES-256 de WinZip (AE-2).

Todo con la biblioteca estándar (lzma, zlib, hashlib) y el AES de Windows. Los archivos
resultantes son estándar: se abren con 7-Zip, WinRAR y similares.

Principios de seguridad, como en el resto de la app:
  * Solo se LEEN los originales; nunca se modifican ni se borran desde aquí.
  * Se escribe en un archivo «.part» y solo al terminar bien se le da su nombre. Si se
    cancela o falla, no queda nada a medias.
  * No se siguen enlaces simbólicos ni junctions, y los archivos «solo en la nube» de
    OneDrive no se descargan: se omiten y se informa.
  * La contraseña vive en memoria mientras dura la operación y nunca se registra.
"""

from __future__ import annotations

import hashlib
import hmac
import lzma
import os
import stat as _stat
import struct
import time
import zipfile
import zlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from . import aes, i18n
from .plat import CLOUD_ONLY_MASK, FILE_ATTRIBUTE_REPARSE_POINT

MB = 1024 ** 2
CHUNK = MB
FORMATS = ("7z", "zip")
LEVELS = ("ultra", "max", "normal", "fast")

# nivel -> (preset de LZMA2, diccionario, nivel de Deflate). Los mismos escalones que 7-Zip.
_LEVEL = {
    "fast": (1, 1 * MB, 1),
    "normal": (6, 16 * MB, 6),
    "max": (9, 32 * MB, 9),
    "ultra": (9 | lzma.PRESET_EXTREME, 64 * MB, 9),
}


class Cancelled(Exception):
    """El usuario detuvo la operación."""


class ArchiveError(Exception):
    """El archivo no se pudo crear o no superó la verificación."""


@dataclass
class Entry:
    src: str
    arcname: str        # ruta dentro del archivo, con «/»
    size: int
    mtime: float
    is_dir: bool = False


@dataclass
class Collection:
    entries: list[Entry] = field(default_factory=list)
    total: int = 0
    files: int = 0
    dirs: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)   # (ruta, motivo)


@dataclass
class Options:
    dest: str
    fmt: str = "7z"
    level: str = "ultra"
    password: str = ""
    verify: bool = True
    ram_total: int = 0      # RAM física y libre: de ellas salen el diccionario y los hilos
    ram_free: int = 0


@dataclass
class Progress:
    phase: str              # «compress» | «verify»
    done: int
    total: int
    current: str = ""
    written: int = 0        # bytes del archivo comprimido hasta ahora


@dataclass
class Result:
    dest: str
    files: int = 0
    dirs: int = 0
    in_bytes: int = 0
    out_bytes: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)
    verified: bool | None = None    # None = no se pidió verificar
    seconds: float = 0.0

    @property
    def ratio(self) -> float:
        """Tamaño final respecto al original (0,25 = ocupa la cuarta parte)."""
        return self.out_bytes / self.in_bytes if self.in_bytes else 1.0


# =========================================================================
# Qué se va a comprimir
# =========================================================================

def _skip_reason(st) -> str:
    attrs = getattr(st, "st_file_attributes", 0)
    if _stat.S_ISLNK(st.st_mode) or attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        return i18n.t("zip.skip.link")
    if attrs & CLOUD_ONLY_MASK:
        return i18n.t("zip.skip.cloud")
    return ""


def _drop_nested(paths: list[str]) -> list[str]:
    """Quita duplicados y lo que ya está dentro de otra carpeta seleccionada."""
    norm = sorted({os.path.normpath(os.path.abspath(p)) for p in paths if p}, key=len)
    out: list[str] = []
    for p in norm:
        key = os.path.normcase(p)
        if not any(key == os.path.normcase(o) or key.startswith(os.path.normcase(o).rstrip(os.sep) + os.sep)
                   for o in out):
            out.append(p)
    return out


def _arc_base(paths: list[str]) -> str | None:
    try:
        return os.path.commonpath([os.path.dirname(p.rstrip(os.sep)) or p for p in paths])
    except ValueError:      # unidades distintas: no hay carpeta común
        return None


def _valid_text(name: str) -> str:
    """En Linux un nombre de archivo puede no ser UTF-8 válido; Python lo representa con
    marcas que no se pueden escribir en un 7z ni en un ZIP. Se cambian por el signo de sustitución (U+FFFD)."""
    try:
        name.encode("utf-8")
        return name
    except UnicodeEncodeError:
        return name.encode("utf-8", "surrogateescape").decode("utf-8", "replace")


def _arcname(path: str, base: str | None) -> str:
    if base is not None:
        rel = os.path.relpath(path, base)
        if rel not in (".", "") and not rel.startswith(".."):
            return _valid_text(rel.replace(os.sep, "/"))
    drive, rest = os.path.splitdrive(path)
    name = "/".join(x for x in (drive.rstrip(":"), rest.strip("\\/").replace(os.sep, "/")) if x)
    return _valid_text(name) or "root"


def collect(paths: list[str], should_stop=None, progress=None) -> Collection:
    """Recorre lo seleccionado y devuelve la lista de archivos y carpetas a guardar."""
    col = Collection()
    tops = _drop_nested(paths)
    base = _arc_base(tops) if tops else None
    stack: list[str] = []

    def add(path: str, st) -> None:
        why = _skip_reason(st)
        if why:
            col.skipped.append((path, why))
        elif _stat.S_ISDIR(st.st_mode):
            col.entries.append(Entry(path, _arcname(path, base), 0, st.st_mtime, True))
            col.dirs += 1
            stack.append(path)
        elif _stat.S_ISREG(st.st_mode):
            col.entries.append(Entry(path, _arcname(path, base), st.st_size, st.st_mtime))
            col.files += 1
            col.total += st.st_size

    for p in tops:
        try:
            add(p, os.lstat(p))
        except OSError as exc:
            col.skipped.append((p, exc.strerror or str(exc)))
    while stack:
        if should_stop and should_stop():
            raise Cancelled()
        folder = stack.pop()
        try:
            with os.scandir(folder) as it:
                for entry in it:
                    try:
                        add(entry.path, entry.stat(follow_symlinks=False))
                    except OSError as exc:
                        col.skipped.append((entry.path, exc.strerror or str(exc)))
        except OSError as exc:
            col.skipped.append((folder, exc.strerror or str(exc)))
        if progress:
            progress(col)
    col.entries.sort(key=lambda e: e.arcname.lower())
    return col


def default_dest(paths: list[str], fmt: str = "7z") -> str:
    """Nombre propuesto: junto a lo seleccionado, sin pisar nada que ya exista."""
    tops = _drop_nested(paths)
    if not tops:
        return ""
    first = tops[0].rstrip(os.sep)
    folder = os.path.dirname(first) or first
    if len(tops) == 1:
        name = os.path.basename(first) or "archive"
        if os.path.isfile(first):
            name = os.path.splitext(name)[0] or name
    else:
        name = os.path.basename(folder.rstrip(os.sep)) or "archive"
    return unique_path(os.path.join(folder, f"{name}.{fmt}"))


def unique_path(path: str) -> str:
    stem, ext = os.path.splitext(path)
    n, out = 2, path
    while os.path.exists(out):
        out = f"{stem} ({n}){ext}"
        n += 1
    return out


def password_ok(fmt: str, password: str) -> bool:
    """El formato zip no dice en qué codificación va la contraseña y cada programa elige
    una distinta: con tildes o «ñ» el archivo se abriría en unos sí y en otros no. Por eso
    en zip solo se admiten caracteres ASCII (lo mismo que hace 7-Zip). En 7z no hay límite."""
    return fmt != "zip" or all(32 <= ord(ch) < 127 for ch in password)


@dataclass
class Plan:
    """Cómo se va a comprimir en 7z: lo que 7-Zip enseña como «uso de memoria»."""
    dict_size: int
    threads: int
    block: int          # tamaño de los bloques que se reparten entre hilos (0 = un solo flujo)
    memory: int         # memoria aproximada que usará el compresor


def _encoder_memory(level: str, dict_size: int) -> int:
    return int(dict_size * (11.5 if level != "fast" else 7.5)) + 32 * MB


def plan(fmt: str, level: str, total: int, ram_total: int = 0, ram_free: int = 0,
         cpus: int | None = None) -> Plan:
    """Elige diccionario e hilos. El diccionario es el del nivel, sin pasarse de los datos
    ni de la RAM del equipo. Con varios hilos los datos se parten en bloques independientes
    (como el LZMA2 multihilo de 7-Zip): es varias veces más rápido y apenas pierde compresión."""
    if fmt != "7z":
        return Plan(0, 1, 0, 8 * MB)
    size = _LEVEL[level][1]
    while size > MB and size >= 2 * max(total, 1):
        size //= 2
    while ram_total and size > MB and _encoder_memory(level, size) > ram_total // 4:
        size //= 2
    block = max(2 * size, 4 * MB)
    per_thread = _encoder_memory(level, size) + 2 * block
    budget = max(int(ram_free * 0.6), ram_total // 5) if ram_total else 2048 * MB
    threads = max(1, min(cpus or os.cpu_count() or 1, budget // per_thread, -(-total // block)))
    if threads == 1:
        return Plan(size, 1, 0, _encoder_memory(level, size))
    return Plan(size, threads, block, threads * per_thread)


# =========================================================================
# Utilidades comunes de escritura
# =========================================================================

class _Reporter:
    """Avisa del progreso como mucho unas diez veces por segundo."""

    def __init__(self, callback, should_stop, total: int):
        self.callback, self.should_stop, self.total = callback, should_stop, total
        self.phase, self.done, self.written, self._last = "compress", 0, 0, 0.0

    def start(self, phase: str, total: int) -> None:
        self.phase, self.total, self.done, self._last = phase, total, 0, 0.0

    def step(self, n: int, current: str = "", written: int | None = None, force: bool = False) -> None:
        if self.should_stop and self.should_stop():
            raise Cancelled()
        self.done += n
        if written is not None:
            self.written = written
        now = time.monotonic()
        if self.callback and (force or now - self._last >= 0.1):
            self._last = now
            self.callback(Progress(self.phase, self.done, self.total, current, self.written))


def _read_chunks(entry: Entry, skipped: list, tick):
    """Va entregando el contenido del archivo. Si no se puede abrir, se omite entero; si
    falla a mitad, se guarda lo leído y se deja constancia. `tick(n, ruta)` se llama tras
    cada trozo (ahí se comprueba si el usuario ha detenido la operación)."""
    try:
        fh = open(entry.src, "rb")
    except OSError as exc:
        skipped.append((entry.src, exc.strerror or str(exc)))
        return
    with fh:
        yield b""   # el archivo existe y se puede leer: cuenta aunque esté vacío
        while True:
            try:
                chunk = fh.read(CHUNK)
            except OSError as exc:
                skipped.append((entry.src, i18n.t("zip.skip.partial", why=exc.strerror or str(exc))))
                return
            if not chunk:
                return
            yield chunk
            tick(len(chunk), entry.src)


# =========================================================================
# Formato 7z
# =========================================================================

_7Z_SIGNATURE = b"7z\xbc\xaf\x27\x1c"
_7Z_AES_ID = b"\x06\xf1\x07\x01"
_7Z_CYCLES = 19     # 2^19 vueltas de SHA-256 para derivar la clave: lo mismo que 7-Zip


def _num(n: int) -> bytes:
    """Entero de longitud variable del formato 7z."""
    first = 0
    for extra in range(8):
        if n < 1 << (7 * (extra + 1)):
            return bytes([first | (n >> (8 * extra))]) + (n & ((1 << (8 * extra)) - 1)).to_bytes(extra, "little")
        first |= 0x80 >> extra
    return b"\xff" + n.to_bytes(8, "little")


def _bits(flags: list[bool]) -> bytes:
    out = bytearray((len(flags) + 7) // 8)
    for i, on in enumerate(flags):
        if on:
            out[i // 8] |= 0x80 >> (i % 8)
    return bytes(out)


def _7z_key(password: str) -> bytes:
    pw = password.encode("utf-16-le")
    h = hashlib.sha256()
    step = 4096
    for start in range(0, 1 << _7Z_CYCLES, step):
        h.update(b"".join(pw + i.to_bytes(8, "little") for i in range(start, start + step)))
    return h.digest()


def _7z_aes_props(iv: bytes) -> bytes:
    return bytes([_7Z_CYCLES | 0x40, len(iv) - 1]) + iv   # sin sal, vector de 16 bytes


def _lzma2_dict_prop(size: int) -> int:
    return 2 * (size.bit_length() - 1 - 12)    # el diccionario siempre es potencia de 2


@dataclass
class _Item:
    name: str
    is_dir: bool
    size: int
    crc: int
    mtime: float

    @property
    def has_stream(self) -> bool:
        return not self.is_dir and self.size > 0


@dataclass
class _SevenMeta:
    items: list[_Item]
    pack_size: int = 0      # bytes en disco del bloque sólido
    lzma_size: int = 0      # bytes que salieron del compresor (antes de cifrar)
    key: bytes = b""
    iv: bytes = b""
    filters: list = field(default_factory=list)


def _7z_header(meta: _SevenMeta) -> bytes:
    items = meta.items
    streams = [it for it in items if it.has_stream]
    out = bytearray(b"\x01")                                        # kHeader
    if streams:
        dict_prop = bytes([_lzma2_dict_prop(meta.filters[0]["dict_size"])])
        lzma2 = b"\x21\x21" + _num(1) + dict_prop                   # 1 byte de id + propiedades
        total = sum(it.size for it in streams)
        if meta.key:
            props = _7z_aes_props(meta.iv)
            folder = (_num(2) + lzma2 + b"\x24" + _7Z_AES_ID + _num(len(props)) + props
                      + _num(0) + _num(1))                          # la entrada de LZMA2 sale del AES
            sizes = _num(total) + _num(meta.lzma_size)
        else:
            folder = _num(1) + lzma2
            sizes = _num(total)
        out += b"\x04"                                              # kMainStreamsInfo
        out += b"\x06" + _num(0) + _num(1) + b"\x09" + _num(meta.pack_size) + b"\x00"
        out += b"\x07\x0b" + _num(1) + b"\x00" + folder + b"\x0c" + sizes + b"\x00"
        out += b"\x08\x0d" + _num(len(streams))
        if len(streams) > 1:
            out += b"\x09" + b"".join(_num(it.size) for it in streams[:-1])
        out += b"\x0a\x01" + b"".join(struct.pack("<I", it.crc) for it in streams) + b"\x00"
        out += b"\x00"
    out += b"\x05" + _num(len(items))                               # kFilesInfo
    empty = [not it.has_stream for it in items]
    if any(empty):
        vec = _bits(empty)
        out += b"\x0e" + _num(len(vec)) + vec
        empty_files = [not it.is_dir for it in items if not it.has_stream]
        if any(empty_files):
            vec = _bits(empty_files)
            out += b"\x0f" + _num(len(vec)) + vec
    names = b"\x00" + b"".join(it.name.encode("utf-16-le") + b"\x00\x00" for it in items)
    out += b"\x11" + _num(len(names)) + names
    times = b"\x01\x00" + b"".join(struct.pack("<Q", max(0, int((it.mtime + 11644473600) * 10_000_000)))
                                   for it in items)
    out += b"\x14" + _num(len(times)) + times
    attrs = b"\x01\x00" + b"".join(struct.pack("<I", 0x10 if it.is_dir else 0x20) for it in items)
    out += b"\x15" + _num(len(attrs)) + attrs
    out += b"\x00\x00"                                              # fin de FilesInfo y de Header
    return bytes(out)


class _CbcSink:
    """Cifra en AES-CBC lo que le llega y lo escribe; rellena con ceros el último bloque."""

    def __init__(self, out, key: bytes, iv: bytes):
        self.out, self.aes, self.buf, self.written = out, aes.Aes(key, "CBC", iv), b"", 0

    def write(self, data: bytes) -> None:
        self.buf += data
        cut = len(self.buf) - len(self.buf) % aes.BLOCK
        if cut:
            self.out.write(self.aes.encrypt(self.buf[:cut]))
            self.written += cut
            self.buf = self.buf[cut:]

    def finish(self) -> int:
        if self.buf:
            self.write(b"\x00" * (aes.BLOCK - len(self.buf)))
        self.aes.close()
        return self.written


def _lzma2_block(block: bytes, filters: list) -> bytes:
    """Comprime un bloque independiente y le quita el byte de fin de flujo, para poder
    encadenarlo con el siguiente (cada bloque empieza reiniciando el diccionario)."""
    comp = lzma.LZMACompressor(lzma.FORMAT_RAW, filters=filters)
    data = comp.compress(block) + comp.flush()
    if not data.endswith(b"\x00"):
        raise ArchiveError("unexpected LZMA2 stream end")
    return data[:-1]


def _write_7z(out, entries: list[Entry], opt: Options, skipped: list, report: _Reporter) -> _SevenMeta:
    total = sum(e.size for e in entries)
    how = plan("7z", opt.level, total, opt.ram_total, opt.ram_free)
    filters = [{"id": lzma.FILTER_LZMA2, "preset": _LEVEL[opt.level][0], "dict_size": how.dict_size}]
    meta = _SevenMeta([], filters=filters)
    out.write(b"\x00" * 32)                                         # hueco para la cabecera inicial
    sink = None
    if opt.password:
        meta.key, meta.iv = _7z_key(opt.password), os.urandom(16)
        sink = _CbcSink(out, meta.key, meta.iv)

    def emit(data: bytes) -> None:
        if data:
            meta.lzma_size += len(data)
            (sink or out).write(data)

    def written() -> int:
        return 32 + meta.lzma_size

    pool = ThreadPoolExecutor(how.threads) if how.threads > 1 else None
    try:
        if pool is None:        # un solo flujo: bloque totalmente sólido
            comp = lzma.LZMACompressor(lzma.FORMAT_RAW, filters=filters)

            def feed(chunk: bytes) -> None:
                emit(comp.compress(chunk))

            def tick(n: int, src: str) -> None:
                report.step(n, src, written())

            def finish() -> None:
                emit(comp.flush())
        else:                   # varios hilos: bloques en paralelo, escritos en orden
            buf = bytearray()
            queue: deque = deque()

            def drain(everything: bool) -> None:
                while queue and (everything or len(queue) > how.threads or queue[0][0].done()):
                    future, size = queue.popleft()
                    emit(future.result())
                    report.step(size, "", written())

            def submit(block: bytes) -> None:
                queue.append((pool.submit(_lzma2_block, block, filters), len(block)))
                drain(False)

            def feed(chunk: bytes) -> None:
                buf.extend(chunk)
                while len(buf) >= how.block:
                    submit(bytes(buf[:how.block]))
                    del buf[:how.block]

            def tick(_n: int, src: str) -> None:
                report.step(0, src)     # el avance se cuenta cuando el bloque ya está escrito

            def finish() -> None:
                if buf:
                    submit(bytes(buf))
                drain(True)
                emit(b"\x00")           # fin del flujo LZMA2

        # Como 7-Zip: los archivos del mismo tipo van seguidos, y el bloque sólido aprovecha
        # lo que se parecen entre sí.
        for e in sorted(entries, key=lambda e: (os.path.splitext(e.arcname)[1].lower(), e.arcname.lower())):
            if e.is_dir:
                meta.items.append(_Item(e.arcname, True, 0, 0, e.mtime))
                continue
            crc, size, opened = 0, 0, False
            for chunk in _read_chunks(e, skipped, tick):
                opened = True
                crc = zlib.crc32(chunk, crc)
                size += len(chunk)
                feed(chunk)
            if opened:
                meta.items.append(_Item(e.arcname, False, size, crc, e.mtime))
        finish()
    finally:
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
    meta.pack_size = sink.finish() if sink else meta.lzma_size
    if not any(it.has_stream for it in meta.items):                 # solo carpetas o archivos vacíos
        out.seek(32)
        out.truncate()
        meta.pack_size = meta.lzma_size = 0

    header = _7z_header(meta)
    if opt.password:   # cabecera cifrada: sin la contraseña no se ven ni los nombres
        iv = os.urandom(16)
        hsink = _CbcSink(out, meta.key, iv)
        hsink.write(header)
        packed = hsink.finish()
        props = _7z_aes_props(iv)
        header = (b"\x17" + b"\x06" + _num(meta.pack_size) + _num(1) + b"\x09" + _num(packed) + b"\x00"
                  + b"\x07\x0b" + _num(1) + b"\x00" + _num(1) + b"\x24" + _7Z_AES_ID + _num(len(props)) + props
                  + b"\x0c" + _num(len(header)) + b"\x0a\x01" + struct.pack("<I", zlib.crc32(header)) + b"\x00"
                  + b"\x00")
        next_offset = meta.pack_size + packed
    else:
        next_offset = meta.pack_size
    out.write(header)
    start = struct.pack("<QQI", next_offset, len(header), zlib.crc32(header))
    out.seek(0)
    out.write(_7Z_SIGNATURE + b"\x00\x04" + struct.pack("<I", zlib.crc32(start)) + start)
    return meta


def _verify_7z(path: str, meta: _SevenMeta, report: _Reporter) -> None:
    """Vuelve a leer el archivo del disco, lo descifra y descomprime entero y compara el
    CRC de cada archivo con el que se calculó al leer el original."""
    with open(path, "rb") as fh:
        head = fh.read(32)
        if head[:6] != _7Z_SIGNATURE or zlib.crc32(head[12:32]) != struct.unpack("<I", head[8:12])[0]:
            raise ArchiveError(i18n.t("zip.err.verify_header"))
        next_offset, next_size, next_crc = struct.unpack("<QQI", head[12:32])
        fh.seek(32 + next_offset)
        if zlib.crc32(fh.read(next_size)) != next_crc:
            raise ArchiveError(i18n.t("zip.err.verify_header"))
        streams = [it for it in meta.items if it.has_stream]
        if not streams:
            return
        fh.seek(32)
        cipher = aes.Aes(meta.key, "CBC", meta.iv) if meta.key else None
        dec = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=meta.filters)
        pending = iter(streams)
        cur = next(pending)
        crc, left = 0, cur.size
        remaining = meta.pack_size
        while remaining > 0:
            block = fh.read(min(CHUNK, remaining))
            if not block:
                break
            remaining -= len(block)
            data = cipher.decrypt(block) if cipher else block
            while not dec.eof:      # tras el final del flujo solo queda relleno del cifrado
                plain = dec.decompress(data, CHUNK)
                data = b""
                while plain:
                    if cur is None:
                        raise ArchiveError(i18n.t("zip.err.verify_header"))
                    part, plain = plain[:left], plain[left:]
                    crc = zlib.crc32(part, crc)
                    left -= len(part)
                    if left == 0:
                        if crc != cur.crc:
                            raise ArchiveError(i18n.t("zip.err.verify_data", name=cur.name))
                        cur = next(pending, None)
                        crc, left = 0, cur.size if cur else 0
                if dec.needs_input:
                    break
            report.step(len(block), cur.name if cur else "")
        if cipher:
            cipher.close()
        if cur is not None or not dec.eof:
            raise ArchiveError(i18n.t("zip.err.verify_data", name=cur.name if cur else os.path.basename(path)))


# =========================================================================
# Formato zip
# =========================================================================

_ZIP64_AT = 0xF0000000      # a partir de aquí se reserva sitio para tamaños de 64 bits
_U32 = 0xFFFFFFFF
_AES_OVERHEAD = 16 + 2 + 10   # sal + comprobación de contraseña + código de autenticación


def _dos_time(ts: float) -> tuple[int, int]:
    try:
        t = time.localtime(ts)
    except (OverflowError, OSError, ValueError):
        t = time.localtime(315532800)
    year = min(max(t.tm_year, 1980), 2107)
    return (t.tm_hour << 11) | (t.tm_min << 5) | (t.tm_sec // 2), ((year - 1980) << 9) | (t.tm_mon << 5) | t.tm_mday


def _zip_keys(password: str, salt: bytes) -> tuple[bytes, bytes, bytes]:
    material = hashlib.pbkdf2_hmac("sha1", password.encode("utf-8"), salt, 1000, 66)
    return material[:32], material[32:64], material[64:66]


@dataclass
class _ZipRecord:
    name: bytes
    flags: int
    method: int
    dos: tuple[int, int]
    crc: int
    csize: int
    usize: int
    offset: int
    aes_extra: bytes
    is_dir: bool
    version: int


def _write_zip(out, entries: list[Entry], opt: Options, skipped: list, report: _Reporter) -> None:
    level = _LEVEL[opt.level][2]
    records: list[_ZipRecord] = []
    for e in entries:
        name = (e.arcname + ("/" if e.is_dir else "")).encode("utf-8")
        dos = _dos_time(e.mtime)
        offset = out.tell()
        if e.is_dir:
            out.write(struct.pack("<4sHHHHHIIIHH", b"PK\x03\x04", 20, 0x800, 0, dos[0], dos[1], 0, 0, 0,
                                  len(name), 0) + name)
            records.append(_ZipRecord(name, 0x800, 0, dos, 0, 0, 0, offset, b"", True, 20))
            continue
        chunks = _read_chunks(e, skipped, lambda n, src: report.step(n, src, out.tell()))
        if next(chunks, None) is None:
            continue    # no se pudo abrir: no se escribe nada de este archivo
        encrypted = bool(opt.password)
        big = e.size >= _ZIP64_AT
        aes_extra = struct.pack("<HHH2sBH", 0x9901, 7, 2, b"AE", 3, 8) if encrypted else b""
        extra = (struct.pack("<HHQQ", 1, 16, 0, 0) if big else b"") + aes_extra
        flags = 0x800 | (1 if encrypted else 0)
        method = 99 if encrypted else 8
        version = 51 if encrypted else (45 if big else 20)
        out.write(struct.pack("<4sHHHHHIIIHH", b"PK\x03\x04", version, flags, method, dos[0], dos[1], 0, 0, 0,
                              len(name), len(extra)) + name + extra)
        data_start = out.tell()
        ctr = mac = None
        if encrypted:
            salt = os.urandom(16)
            ekey, mkey, check = _zip_keys(opt.password, salt)
            ctr, mac = aes.Ctr(ekey), hmac.new(mkey, digestmod="sha1")
            out.write(salt + check)

        def emit(data: bytes) -> None:
            if data:
                if ctr:
                    data = ctr.process(data)
                    mac.update(data)
                out.write(data)

        comp = zlib.compressobj(level, zlib.DEFLATED, -15)
        crc = usize = 0
        for chunk in chunks:
            crc = zlib.crc32(chunk, crc)
            usize += len(chunk)
            emit(comp.compress(chunk))
        emit(comp.flush())
        if encrypted:
            out.write(mac.digest()[:10])
            crc = 0     # AE-2: la integridad la da el código de autenticación, no el CRC
        end = out.tell()
        csize = end - data_start
        if not big and (csize >= _U32 or usize >= _U32):
            raise ArchiveError(i18n.t("zip.err.grew", name=e.src))
        out.seek(offset + 14)
        out.write(struct.pack("<III", crc, _U32 if big else csize, _U32 if big else usize))
        if big:
            out.seek(offset + 30 + len(name) + 4)
            out.write(struct.pack("<QQ", usize, csize))
        out.seek(end)
        records.append(_ZipRecord(name, flags, method, dos, crc, csize, usize, offset, aes_extra, False, version))

    cd_start = out.tell()
    for r in records:
        fields = [v for v in (r.usize, r.csize, r.offset) if v >= _U32]
        z64 = struct.pack(f"<HH{len(fields)}Q", 1, 8 * len(fields), *fields) if fields else b""
        extra = z64 + r.aes_extra
        out.write(struct.pack("<4sHHHHHHIIIHHHHHII", b"PK\x01\x02", 63, max(r.version, 45 if fields else 0),
                              r.flags, r.method, r.dos[0], r.dos[1], r.crc, min(r.csize, _U32),
                              min(r.usize, _U32), len(r.name), len(extra), 0, 0, 0, 0x10 if r.is_dir else 0x20,
                              min(r.offset, _U32)) + r.name + extra)
    cd_size = out.tell() - cd_start
    count = len(records)
    if count >= 0xFFFF or cd_size >= _U32 or cd_start >= _U32:
        z64_start = out.tell()
        out.write(struct.pack("<4sQHHIIQQQQ", b"PK\x06\x06", 44, 45, 45, 0, 0, count, count, cd_size, cd_start))
        out.write(struct.pack("<4sIQI", b"PK\x06\x07", 0, z64_start, 1))
    out.write(struct.pack("<4sHHHHIIH", b"PK\x05\x06", 0, 0, min(count, 0xFFFF), min(count, 0xFFFF),
                          min(cd_size, _U32), min(cd_start, _U32), 0))


def _verify_zip(path: str, password: str, report: _Reporter) -> None:
    with zipfile.ZipFile(path) as zf, open(path, "rb") as raw:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not password:        # lector independiente de la biblioteca estándar: comprueba el CRC
                try:
                    with zf.open(info) as fh:
                        while True:
                            block = fh.read(CHUNK)
                            if not block:
                                break
                            report.step(len(block), info.filename)
                except (zipfile.BadZipFile, zlib.error, OSError) as exc:
                    raise ArchiveError(i18n.t("zip.err.verify_data", name=info.filename)) from exc
                continue
            raw.seek(info.header_offset)
            fixed = raw.read(30)
            name_len, extra_len = struct.unpack("<HH", fixed[26:30])
            raw.seek(name_len + extra_len, 1)
            salt, check = raw.read(16), raw.read(2)
            ekey, mkey, expected = _zip_keys(password, salt)
            left = info.compress_size - _AES_OVERHEAD
            if check != expected or left < 0:
                raise ArchiveError(i18n.t("zip.err.verify_data", name=info.filename))
            ctr, mac = aes.Ctr(ekey), hmac.new(mkey, digestmod="sha1")
            inflate, size = zlib.decompressobj(-15), 0
            while left > 0:
                block = raw.read(min(CHUNK, left))
                if not block:
                    break
                left -= len(block)
                mac.update(block)
                try:
                    size += len(inflate.decompress(ctr.process(block)))
                except zlib.error as exc:
                    raise ArchiveError(i18n.t("zip.err.verify_data", name=info.filename)) from exc
                report.step(len(block), info.filename)
            size += len(inflate.flush())
            if left or not hmac.compare_digest(raw.read(10), mac.digest()[:10]) or size != info.file_size:
                raise ArchiveError(i18n.t("zip.err.verify_data", name=info.filename))


# =========================================================================
# Operación completa
# =========================================================================

def compress(collection: Collection, opt: Options, progress=None, should_stop=None) -> Result:
    """Crea el archivo comprimido. Lanza Cancelled si se detiene y ArchiveError si algo
    impide terminarlo; en ambos casos no deja ningún archivo a medias."""
    if opt.fmt not in FORMATS or opt.level not in _LEVEL:
        raise ValueError("unknown format or level")
    if opt.password and not aes.AVAILABLE:
        raise ArchiveError(i18n.t("zip.err.no_aes"))
    if opt.password and not password_ok(opt.fmt, opt.password):
        raise ArchiveError(i18n.t("zip.err.ascii_password"))
    dest = os.path.abspath(opt.dest)
    part = dest + ".part"
    sources = {os.path.normcase(os.path.abspath(e.src)) for e in collection.entries}
    if os.path.normcase(dest) in sources:   # al terminar se reemplazaría uno de los originales
        raise ArchiveError(i18n.t("zip.err.dest_is_source"))
    entries = [e for e in collection.entries
               if os.path.normcase(os.path.abspath(e.src)) != os.path.normcase(part)]
    if not entries:
        raise ArchiveError(i18n.t("zip.err.nothing"))
    skipped = list(collection.skipped)
    total = sum(e.size for e in entries)
    report = _Reporter(progress, should_stop, total)
    started = time.monotonic()
    result = Result(dest, dirs=sum(1 for e in entries if e.is_dir))
    try:
        with open(part, "w+b") as out:
            if opt.fmt == "7z":
                meta = _write_7z(out, entries, opt, skipped, report)
            else:
                meta = None
                _write_zip(out, entries, opt, skipped, report)
            out.flush()
            os.fsync(out.fileno())
        result.out_bytes = os.path.getsize(part)
        result.in_bytes = report.done
        report.step(0, "", result.out_bytes, force=True)
        if opt.verify:
            report.start("verify", result.out_bytes)
            if opt.fmt == "7z":
                _verify_7z(part, meta, report)
            else:
                _verify_zip(part, opt.password, report)
            result.verified = True
            report.step(0, "", result.out_bytes, force=True)
        os.replace(part, dest)
    except OSError as exc:
        _discard(part)
        raise ArchiveError(exc.strerror or str(exc)) from exc
    except BaseException:
        _discard(part)
        raise
    unreadable = {p for p, _why in skipped}
    result.files = sum(1 for e in entries if not e.is_dir and e.src not in unreadable)
    result.skipped = skipped
    result.seconds = time.monotonic() - started
    return result


def _discard(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
