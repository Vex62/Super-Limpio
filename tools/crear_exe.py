"""Compila SuperLimpio.exe, el lanzador nativo de launcher\\launcher.c.

    runtime\\python\\python.exe tools\\crear_exe.py

Necesita el compilador de C de Visual Studio o de «Build Tools for Visual Studio»
(cl.exe, link.exe y lib.exe). No hace falta el SDK de Windows: las tres bibliotecas
de importación que usa el lanzador se generan aquí, y el icono (launcher\\logo.png),
la información de versión y el manifiesto se escriben directamente en un .res, sin
rc.exe.

El resultado no va empaquetado ni comprimido y se compila de forma reproducible
(/Brepro): el mismo código fuente da siempre el mismo .exe, byte a byte.
"""

from __future__ import annotations

import hashlib
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from superlimpio import APP_NAME, __version__  # noqa: E402
from superlimpio.ui import theme  # noqa: E402

SRC = ROOT / "launcher"
BUILD = ROOT / "build"
EXE = ROOT / "SuperLimpio.exe"
LOGO = SRC / "logo.png"   # PNG cuadrado con transparencia; si falta, se dibuja un icono sencillo
# Lo que usa la ventana (icono de la barra de título y logo de la barra lateral); va a git
ASSETS = ROOT / "app" / "superlimpio" / "ui" / "assets"
SIDEBAR_LOGO_SIZES = (40, 60)

# Funciones de Windows que usa launcher.c (deben coincidir con sus declaraciones)
IMPORTS = {
    "kernel32": ["GetModuleFileNameW", "GetFileAttributesW", "FindFirstFileW", "FindNextFileW", "FindClose",
                 "LoadLibraryExW", "GetProcAddress", "GetCommandLineW", "GetProcessHeap", "HeapAlloc",
                 "ExitProcess"],
    "user32": ["MessageBoxW"],
    "shell32": ["CommandLineToArgvW"],
}

RT_ICON, RT_GROUP_ICON, RT_VERSION, RT_MANIFEST = 3, 14, 16, 24
LANG_NEUTRAL, LANG_SPANISH = 0x0000, 0x0C0A
ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 256)


# ------------------------------------------------------------------- icono
def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def _read_png(path: Path) -> tuple[int, list[bytearray]]:
    """Lee un PNG RGBA de 8 bits (solo biblioteca estándar). Devuelve el lado y las filas."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{path.name} no es un PNG")
    pos, idat, info = 8, [], None
    while pos < len(data):
        length, tag = struct.unpack(">I4s", data[pos:pos + 8])
        if tag == b"IHDR":
            info = struct.unpack(">IIBBBBB", data[pos + 8:pos + 8 + length])
        elif tag == b"IDAT":
            idat.append(data[pos + 8:pos + 8 + length])
        pos += 12 + length
    if not info or info[0] != info[1] or info[0] < 256 or info[2:] != (8, 6, 0, 0, 0):
        raise SystemExit(f"{path.name} debe ser un PNG cuadrado de 256 px o más, RGBA de 8 bits y sin entrelazar")
    side, stride = info[0], info[0] * 4
    raw = zlib.decompress(b"".join(idat))
    rows, prev = [], bytearray(stride)
    for y in range(side):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        if kind == 1:                                   # filtros de fila del formato PNG
            for i in range(4, stride):
                line[i] = (line[i] + line[i - 4]) & 255
        elif kind == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif kind == 3:
            for i in range(stride):
                line[i] = (line[i] + (((line[i - 4] if i >= 4 else 0) + prev[i]) >> 1)) & 255
        elif kind == 4:
            for i in range(stride):
                a, b, c = (line[i - 4], prev[i], prev[i - 4]) if i >= 4 else (0, prev[i], 0)
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return side, rows


def _premultiply(rows: list[bytearray]) -> list[list[list[int]]]:
    """Planos R·A, G·A, B·A y A: así los bordes transparentes no ensucian el color al reducir."""
    planes: list[list[list[int]]] = [[], [], [], []]
    for row in rows:
        alpha = list(row[3::4])
        for c in range(3):
            planes[c].append([v * a for v, a in zip(row[c::4], alpha)])
        planes[3].append(alpha)
    return planes


def _shrink(planes: list[list[list[int]]], side: int, size: int) -> bytes:
    """Reduce el logo a size x size promediando cada bloque de píxeles. Devuelve RGBA."""
    edges = [i * side // size for i in range(size + 1)]
    out = bytearray()
    for ty in range(size):
        sums = [[0] * size for _ in range(4)]
        for y in range(edges[ty], edges[ty + 1]):
            for c in range(4):
                row, acc = planes[c][y], sums[c]
                for tx in range(size):
                    acc[tx] += sum(row[edges[tx]:edges[tx + 1]])
        height = edges[ty + 1] - edges[ty]
        for tx in range(size):
            alpha = sums[3][tx]
            if alpha:
                area = height * (edges[tx + 1] - edges[tx])
                out += bytes(min(255, (sums[c][tx] + alpha // 2) // alpha) for c in range(3))
                out.append((alpha + area // 2) // area)
            else:
                out += b"\0\0\0\0"
    return bytes(out)


def _render_icon(size: int) -> bytes:
    """Mismo motivo que el icono de la ventana: disco verde con un destello blanco. Devuelve RGBA."""
    accent, dark = _rgb(theme.ACCENT), _rgb(theme.ACCENT_DARK)
    ss = 4 if size >= 64 else 8          # muestras por lado en cada píxel (suavizado de bordes)
    step = 2.0 / (size * ss)
    out = bytearray()
    for py in range(size):
        for px in range(size):
            r = g = b = a = 0
            for sy in range(ss):
                y = -1.0 + (py * ss + sy + 0.5) * step
                for sx in range(ss):
                    x = -1.0 + (px * ss + sx + 0.5) * step
                    d2 = x * x + y * y
                    if d2 > 0.9025:                                             # fuera del disco (r = 0,95)
                        continue
                    if abs(x) ** 0.55 + abs(y) ** 0.55 <= 0.775:                # destello de 4 puntas
                        c = (255, 255, 255)
                    else:
                        c = dark if d2 > 0.7225 else accent                     # borde más oscuro
                    r += c[0]
                    g += c[1]
                    b += c[2]
                    a += 1
            if a:
                out += bytes((r // a, g // a, b // a, a * 255 // (ss * ss)))
            else:
                out += b"\0\0\0\0"
    return bytes(out)


def _png(size: int, rgba: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    rows = b"".join(b"\0" + rgba[y * size * 4:(y + 1) * size * 4] for y in range(size))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def _dib(size: int, rgba: bytes) -> bytes:
    """Formato clásico de icono: cabecera + BGRA de abajo arriba + máscara de 1 bit."""
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    pixels = bytearray()
    for y in range(size - 1, -1, -1):
        row = rgba[y * size * 4:(y + 1) * size * 4]
        for x in range(0, len(row), 4):
            pixels += bytes((row[x + 2], row[x + 1], row[x], row[x + 3]))
    mask = bytes(((size + 31) // 32) * 4) * size
    return header + bytes(pixels) + mask


def _icons() -> list[tuple[int, bytes]]:
    """Imágenes del icono, y de paso los archivos que usa la ventana en ASSETS."""
    images = []
    side, planes = 0, None
    if LOGO.is_file():
        side, rows = _read_png(LOGO)
        planes = _premultiply(rows)
    for size in ICON_SIZES:
        rgba = _shrink(planes, side, size) if planes else _render_icon(size)
        images.append((size, _png(size, rgba) if size >= 256 else _dib(size, rgba)))
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "superlimpio.ico").write_bytes(_ico_file(images))
    for size in SIDEBAR_LOGO_SIZES if planes else ():
        (ASSETS / f"logo-{size}.png").write_bytes(_png(size, _shrink(planes, side, size)))
    return images


def _ico_file(images: list[tuple[int, bytes]]) -> bytes:
    out = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    for size, data in images:
        out += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return out + b"".join(data for _, data in images)


def _group_icon(images: list[tuple[int, bytes]]) -> bytes:
    out = struct.pack("<HHH", 0, 1, len(images))
    for number, (size, data) in enumerate(images, 1):
        out += struct.pack("<BBBBHHIH", size % 256, size % 256, 0, 0, 1, 32, len(data), number)
    return out


# -------------------------------------------------- información de versión
def _pad4(data: bytes) -> bytes:
    return data + b"\0" * (-len(data) % 4)


def _node(key: str, value: bytes = b"", is_text: bool = False, children: tuple[bytes, ...] = ()) -> bytes:
    """Bloque de VS_VERSIONINFO: longitud, longitud del valor, tipo, clave, valor e hijos."""
    body = _pad4(b"\0" * 6 + key.encode("utf-16-le") + b"\0\0") + value
    for child in children:
        body = _pad4(body) + child
    value_len = len(value) // 2 if is_text else len(value)
    return struct.pack("<HHH", len(body), value_len, int(is_text)) + body[6:]


def _version_info() -> bytes:
    parts = ([int(p) for p in __version__.split(".")] + [0, 0, 0, 0])[:4]
    ms, ls = (parts[0] << 16) | parts[1], (parts[2] << 16) | parts[3]
    fixed = struct.pack("<13I", 0xFEEF04BD, 0x00010000, ms, ls, ms, ls, 0x3F, 0, 0x00040004, 1, 0, 0, 0)
    strings = {
        "CompanyName": f"{APP_NAME} (código abierto)",
        "FileDescription": APP_NAME,
        "FileVersion": __version__,
        "InternalName": "SuperLimpio",
        "LegalCopyright": "Código fuente legible incluido en la carpeta app",
        "OriginalFilename": EXE.name,
        "ProductName": APP_NAME,
        "ProductVersion": __version__,
    }
    table = _node(f"{LANG_SPANISH:04X}04B0", children=tuple(
        _node(key, (text + "\0").encode("utf-16-le"), is_text=True) for key, text in strings.items()))
    return _node("VS_VERSION_INFO", fixed, children=(
        _node("StringFileInfo", is_text=True, children=(table,)),
        _node("VarFileInfo", is_text=True, children=(
            _node("Translation", struct.pack("<HH", LANG_SPANISH, 1200)),)),
    ))


# ------------------------------------------------------------ archivo .res
def _res_entry(res_type: int, res_id: int, data: bytes, lang: int) -> bytes:
    header = struct.pack("<IIHHHHIHHII", len(data), 32, 0xFFFF, res_type, 0xFFFF, res_id, 0, 0x1030, lang, 0, 0)
    return header + _pad4(data)


def write_resources() -> Path:
    images = _icons()
    manifest = (SRC / "SuperLimpio.manifest").read_text(encoding="utf-8").replace(
        "@VERSION@", ".".join((__version__.split(".") + ["0"] * 4)[:4]))
    res = _res_entry(0, 0, b"", LANG_NEUTRAL)  # cabecera obligatoria del formato de 32 bits
    for number, (_, data) in enumerate(images, 1):
        res += _res_entry(RT_ICON, number, data, LANG_NEUTRAL)
    res += _res_entry(RT_GROUP_ICON, 1, _group_icon(images), LANG_NEUTRAL)
    res += _res_entry(RT_VERSION, 1, _version_info(), LANG_SPANISH)
    res += _res_entry(RT_MANIFEST, 1, manifest.encode("utf-8"), LANG_NEUTRAL)
    out = BUILD / "recursos.res"
    out.write_bytes(res)
    return out


# -------------------------------------------------------------- compilador
def _version_key(path: Path) -> tuple[int, ...]:
    return tuple(int(p) for p in path.parents[2].name.split(".") if p.isdigit())


def find_msvc() -> Path:
    """Carpeta bin\\Hostx64\\x64 del compilador de C más reciente que haya instalado."""
    program_files = [os.environ.get(v) for v in ("ProgramFiles(x86)", "ProgramFiles")]
    roots: list[Path] = []
    vswhere = Path(program_files[0] or "", "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if vswhere.is_file():
        found = subprocess.run([str(vswhere), "-all", "-prerelease", "-products", "*", "-utf8",
                                "-property", "installationPath"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
        roots += [Path(line.strip()) for line in found.stdout.splitlines() if line.strip()]
    for base in filter(None, program_files):
        roots += Path(base, "Microsoft Visual Studio").glob("*/*")
    bins = [b for root in roots for b in root.glob("VC/Tools/MSVC/*/bin/Hostx64/x64")
            if all((b / tool).is_file() for tool in ("cl.exe", "link.exe", "lib.exe"))]
    if not bins:
        raise SystemExit("No se ha encontrado el compilador de C de Visual Studio (cl.exe, link.exe, lib.exe).\n"
                         "Instala «Build Tools for Visual Studio» con la carga «Desarrollo para el escritorio "
                         "con C++».")
    return max(bins, key=_version_key)


def _run(bin_dir: Path, tool: str, *args: str) -> None:
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    done = subprocess.run([str(bin_dir / tool), "/nologo", *args], cwd=BUILD, env=env,
                          capture_output=True, text=True, encoding="oem", errors="replace")
    output = (done.stdout + done.stderr).strip()
    if done.returncode:
        raise SystemExit(f"{tool} falló (código {done.returncode}):\n{output}")
    for line in output.splitlines():
        if "warning" in line.lower():
            print("  ", line)


def build() -> Path:
    bin_dir = find_msvc()
    BUILD.mkdir(exist_ok=True)
    print(f"Compilador: {bin_dir}")

    libs = []
    for dll, names in IMPORTS.items():
        (BUILD / f"{dll}.def").write_text(f"LIBRARY {dll}.dll\nEXPORTS\n" + "".join(f"  {n}\n" for n in names),
                                          encoding="ascii")
        _run(bin_dir, "lib.exe", "/machine:x64", f"/def:{dll}.def", f"/out:{dll}.lib")
        libs.append(f"{dll}.lib")

    resources = write_resources()
    # /O1 tamaño · /GS- y /Zl: sin biblioteca de C · /Brepro: compilación reproducible
    _run(bin_dir, "cl.exe", "/c", "/O1", "/W4", "/WX", "/GS-", "/Zl", "/utf-8", "/Brepro",
         "/Folauncher.obj", str(SRC / "launcher.c"))
    # /RELEASE escribe la suma de comprobación del PE; sin /DEBUG no se guarda ninguna ruta de este equipo
    _run(bin_dir, "link.exe", "/machine:x64", "/subsystem:windows", "/entry:entry", "/nodefaultlib",
         "/opt:ref", "/opt:icf", "/release", "/Brepro", "/manifest:no", "/dynamicbase", "/nxcompat",
         "/highentropyva", f"/out:{EXE}", "launcher.obj", resources.name, *libs)

    data = EXE.read_bytes()
    print(f"{EXE}\n{len(data) / 1024:.1f} KB · SHA-256 {hashlib.sha256(data).hexdigest()}")
    return EXE


if __name__ == "__main__":
    build()
