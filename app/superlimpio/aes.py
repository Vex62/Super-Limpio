"""AES-256 con la criptografía del propio Windows (CNG, bcrypt.dll).

Super Limpio no lleva una implementación propia del cifrado: usa la del sistema,
que es la que está auditada y acelerada por hardware. Solo se necesita para poner
contraseña a los archivos comprimidos, así que fuera de Windows simplemente no
está disponible (`AVAILABLE` es False).
"""

from __future__ import annotations

import sys

AVAILABLE = sys.platform == "win32"
BLOCK = 16

if AVAILABLE:
    import ctypes
    from ctypes import wintypes

    _bcrypt = ctypes.WinDLL("bcrypt")
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
    _CRYPT_ARGS = [ctypes.c_void_p, ctypes.c_char_p, wintypes.ULONG, ctypes.c_void_p, ctypes.c_void_p,
                   wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG, ctypes.POINTER(wintypes.ULONG),
                   wintypes.ULONG]
    _bcrypt.BCryptEncrypt.restype = _NTSTATUS
    _bcrypt.BCryptEncrypt.argtypes = _CRYPT_ARGS
    _bcrypt.BCryptDecrypt.restype = _NTSTATUS
    _bcrypt.BCryptDecrypt.argtypes = _CRYPT_ARGS
    _bcrypt.BCryptDestroyKey.argtypes = [ctypes.c_void_p]
    _bcrypt.BCryptCloseAlgorithmProvider.argtypes = [ctypes.c_void_p, wintypes.ULONG]


class AesError(OSError):
    pass


class Aes:
    """Clave AES en modo ECB o CBC. En CBC el vector se va encadenando entre llamadas,
    así que se puede cifrar un flujo por trozos (siempre múltiplos de 16 bytes)."""

    def __init__(self, key: bytes, mode: str = "ECB", iv: bytes | None = None):
        if not AVAILABLE:
            raise AesError("AES is only available on Windows")
        if len(key) not in (16, 24, 32):
            raise ValueError("invalid AES key size")
        if mode == "CBC" and (iv is None or len(iv) != BLOCK):
            raise ValueError("CBC needs a 16-byte IV")
        self._alg = ctypes.c_void_p()
        self._key = ctypes.c_void_p()
        self._check(_bcrypt.BCryptOpenAlgorithmProvider(ctypes.byref(self._alg), "AES", None, 0))
        chaining = ctypes.create_unicode_buffer(f"ChainingMode{mode}")
        self._check(_bcrypt.BCryptSetProperty(self._alg, "ChainingMode", chaining, ctypes.sizeof(chaining), 0))
        self._check(_bcrypt.BCryptGenerateSymmetricKey(self._alg, ctypes.byref(self._key), None, 0,
                                                       key, len(key), 0))
        self._iv = ctypes.create_string_buffer(iv, BLOCK) if mode == "CBC" else None

    @staticmethod
    def _check(status: int) -> None:
        if status != 0:
            raise AesError(f"Windows cryptography error {status & 0xFFFFFFFF:#010x}")

    def _run(self, fn, data: bytes) -> bytes:
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

    def __del__(self):  # noqa: D105
        try:
            self.close()
        except Exception:  # noqa: BLE001
            pass


class Ctr:
    """AES en modo contador tal como lo define el formato ZIP de WinZip: contador de
    16 bytes en little-endian que empieza en 1. Cifrar y descifrar son la misma operación."""

    def __init__(self, key: bytes):
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
