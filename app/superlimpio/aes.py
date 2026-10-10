"""AES-256 con la criptografía del propio sistema operativo.

Super Limpio no lleva una implementación propia del cifrado: usa la del sistema, que es
la que está auditada y acelerada por hardware. En Windows es CNG (bcrypt.dll); en Linux
y otros Unix, OpenSSL (libcrypto), que traen todas las distribuciones. Solo se necesita
para poner contraseña a los archivos comprimidos; si en un equipo no hubiera ninguna de
las dos, `AVAILABLE` es False y esa opción se rechaza.
"""

from __future__ import annotations

import sys
from typing import Any

_WINDOWS = sys.platform == "win32"
BLOCK = 16

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    from .plat.windows import system_dll

    _bcrypt = system_dll("bcrypt")   # solo desde System32, nunca una copia junto a la aplicación
    _NTSTATUS = ctypes.c_long
    _bcrypt.BCryptOpenAlgorithmProvider.restype = _NTSTATUS
    _bcrypt.BCryptOpenAlgorithmProvider.argtypes = [
        ctypes.POINTER(ctypes.c_void_p), wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.ULONG]
    _bcrypt.BCryptSetProperty.restype = _NTSTATUS
    _bcrypt.BCryptSetProperty.argtypes = [
        ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.ULONG, wintypes.ULONG]
    _bcrypt.BCryptGenerateSymmetricKey.restype = _NTSTATUS
    _bcrypt.BCryptGenerateSymmetricKey.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, wintypes.ULONG,
        ctypes.c_char_p, wintypes.ULONG, wintypes.ULONG]
    _CRYPT_ARGS: list[Any] = [ctypes.c_void_p, ctypes.c_char_p, wintypes.ULONG, ctypes.c_void_p, ctypes.c_void_p,
                   wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG),
                   wintypes.ULONG]
    _bcrypt.BCryptEncrypt.restype = _NTSTATUS
    _bcrypt.BCryptEncrypt.argtypes = _CRYPT_ARGS
    _bcrypt.BCryptDecrypt.restype = _NTSTATUS
    _bcrypt.BCryptDecrypt.argtypes = _CRYPT_ARGS
    _bcrypt.BCryptDestroyKey.restype = _NTSTATUS
    _bcrypt.BCryptDestroyKey.argtypes = [ctypes.c_void_p]
    _bcrypt.BCryptCloseAlgorithmProvider.restype = _NTSTATUS
    _bcrypt.BCryptCloseAlgorithmProvider.argtypes = [ctypes.c_void_p, wintypes.ULONG]


class AesError(OSError):
    pass


def _check_args(key: bytes, mode: str, iv: bytes | None) -> None:
    if len(key) not in (16, 24, 32):
        raise ValueError("invalid AES key size")
    if mode not in ("ECB", "CBC"):
        raise ValueError("unknown AES mode")
    if mode == "CBC" and (iv is None or len(iv) != BLOCK):
        raise ValueError("CBC needs a 16-byte IV")


if sys.platform == "win32":
    class _CngAes:
        """AES de Windows (CNG)."""

        def __init__(self, key: bytes, mode: str = "ECB", iv: bytes | None = None) -> None:
            _check_args(key, mode, iv)
            self._alg: Any = ctypes.c_void_p()
            self._key: Any = ctypes.c_void_p()
            self._check(_bcrypt.BCryptOpenAlgorithmProvider(ctypes.byref(self._alg), "AES", None, 0))
            chaining = ctypes.create_unicode_buffer(f"ChainingMode{mode}")
            self._check(_bcrypt.BCryptSetProperty(self._alg, "ChainingMode", chaining, ctypes.sizeof(chaining), 0))
            self._check(_bcrypt.BCryptGenerateSymmetricKey(self._alg, ctypes.byref(self._key), None, 0,
                                                           key, len(key), 0))
            self._iv = ctypes.create_string_buffer(iv or b"", BLOCK) if mode == "CBC" else None

        @staticmethod
        def _check(status: int) -> None:
            if status != 0:
                raise AesError(f"Windows cryptography error {status & 0xFFFFFFFF:#010x}")

        def _run(self, fn: Any, data: bytes) -> bytes:
            if len(data) % BLOCK:
                raise ValueError("data must be a multiple of 16 bytes")
            if not data:
                return b""
            out = ctypes.create_string_buffer(len(data))
            done = wintypes.ULONG()
            self._check(fn(self._key, data, len(data), None, self._iv, BLOCK if self._iv is not None else 0,
                           out, len(data), ctypes.byref(done), 0))
            return out.raw[:done.value]

        def encrypt(self, data: bytes) -> bytes:
            return self._run(_bcrypt.BCryptEncrypt, data)

        def decrypt(self, data: bytes) -> bytes:
            return self._run(_bcrypt.BCryptDecrypt, data)

        def close(self) -> None:
            if getattr(self, "_key", None):
                _bcrypt.BCryptDestroyKey(self._key)
                self._key = None
            if getattr(self, "_alg", None):
                _bcrypt.BCryptCloseAlgorithmProvider(self._alg, 0)
                self._alg = None

        def __del__(self) -> None:  # noqa: D105
            try:
                self.close()
            except (OSError, AttributeError, TypeError):
                pass   # al cerrar el intérprete la biblioteca puede haberse descargado ya: no queda nada que liberar


def _load_openssl() -> Any:
    """libcrypto de OpenSSL, o None si este equipo no la tiene."""
    import ctypes
    import ctypes.util

    for name in (ctypes.util.find_library("crypto"), "libcrypto.so.3", "libcrypto.so.1.1", "libcrypto.dylib"):
        if not name:
            continue
        try:
            lib = ctypes.CDLL(name)
            lib.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
            lib.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]
            lib.EVP_CIPHER_CTX_set_padding.argtypes = [ctypes.c_void_p, ctypes.c_int]
            lib.EVP_CipherInit_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                              ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
            lib.EVP_CipherUpdate.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int),
                                             ctypes.c_char_p, ctypes.c_int]
            for bits in (128, 192, 256):
                for mode in ("ecb", "cbc"):
                    getattr(lib, f"EVP_aes_{bits}_{mode}").restype = ctypes.c_void_p
            return lib
        except (OSError, AttributeError):
            continue
    return None


_openssl: Any = None if _WINDOWS else _load_openssl()


class _OpenSslAes:
    """AES de OpenSSL (interfaz EVP), sin relleno: los datos van siempre en bloques de 16."""

    def __init__(self, key: bytes, mode: str = "ECB", iv: bytes | None = None) -> None:
        _check_args(key, mode, iv)
        self._key, self._mode, self._iv = key, mode.lower(), iv
        self._ctx: dict[int, int] = {}   # 1 = cifrar, 0 = descifrar; cada sentido lleva su encadenado

    def _context(self, encrypt: int) -> Any:
        import ctypes
        ctx = self._ctx.get(encrypt)
        if ctx is None:
            ctx = _openssl.EVP_CIPHER_CTX_new()
            cipher = getattr(_openssl, f"EVP_aes_{len(self._key) * 8}_{self._mode}")()
            if not ctx or not cipher or _openssl.EVP_CipherInit_ex(
                    ctypes.c_void_p(ctx), ctypes.c_void_p(cipher), None, self._key, self._iv, encrypt) != 1:
                raise AesError("OpenSSL could not initialise AES")
            _openssl.EVP_CIPHER_CTX_set_padding(ctypes.c_void_p(ctx), 0)
            self._ctx[encrypt] = ctx
        return ctypes.c_void_p(ctx)

    def _run(self, encrypt: int, data: bytes) -> bytes:
        import ctypes
        if len(data) % BLOCK:
            raise ValueError("data must be a multiple of 16 bytes")
        if not data:
            return b""
        out = ctypes.create_string_buffer(len(data) + BLOCK)
        done = ctypes.c_int(0)
        if _openssl.EVP_CipherUpdate(self._context(encrypt), out, ctypes.byref(done), data, len(data)) != 1:
            raise AesError("OpenSSL AES error")
        return out.raw[:done.value]

    def encrypt(self, data: bytes) -> bytes:
        return self._run(1, data)

    def decrypt(self, data: bytes) -> bytes:
        return self._run(0, data)

    def close(self) -> None:
        import ctypes
        for ctx in getattr(self, "_ctx", {}).values():
            _openssl.EVP_CIPHER_CTX_free(ctypes.c_void_p(ctx))
        self._ctx = {}

    def __del__(self) -> None:  # noqa: D105
        try:
            self.close()
        except (OSError, AttributeError, TypeError):
            pass   # al cerrar el intérprete la biblioteca puede haberse descargado ya: no queda nada que liberar


class _NoAes:
    def __init__(self, *_args: Any, **_kw: Any) -> None:
        raise AesError("this system has no AES provider (CNG or OpenSSL)")


# Clave AES en modo ECB o CBC. En CBC el vector se va encadenando entre llamadas, así que
# se puede cifrar un flujo por trozos (siempre múltiplos de 16 bytes).
Aes: Any
if sys.platform == "win32":
    Aes = _CngAes
else:
    Aes = _OpenSslAes if _openssl is not None else _NoAes
AVAILABLE = Aes is not _NoAes


class Ctr:
    """AES en modo contador tal como lo define el formato ZIP de WinZip: contador de
    16 bytes en little-endian que empieza en 1. Cifrar y descifrar son la misma operación."""

    def __init__(self, key: bytes) -> None:
        self._aes = Aes(key, "ECB")
        self._counter = 1
        self._pending = b""   # resto de flujo de clave del último bloque

    def process(self, data: bytes) -> bytes:
        if not data:
            return b""
        need = len(data) - len(self._pending)
        if need > 0:
            blocks = (need + BLOCK - 1) // BLOCK
            start = self._counter
            counters = b"".join(i.to_bytes(BLOCK, "little") for i in range(start, start + blocks))
            self._counter += blocks
            self._pending += self._aes.encrypt(counters)
        stream, self._pending = self._pending[:len(data)], self._pending[len(data):]
        return (int.from_bytes(data, "little") ^ int.from_bytes(stream, "little")).to_bytes(len(data), "little")
