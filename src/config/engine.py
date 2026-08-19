import socket as _socket
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Final as _Final

from .settings import (ENGINE_NUM_WORKERS, ENGINE_SOCKET_PORT,
                       ENGINE_UNIX_SOCKET_PATH, STORAGE_DIR)

if ENGINE_UNIX_SOCKET_PATH and hasattr(_socket, "AF_UNIX"):
    ENGINE_SOCKET_ADDRESS: _Final[str] = ENGINE_UNIX_SOCKET_PATH
    ENGINE_SOCKET_FAMILY: _Final[int] = _socket.AF_UNIX

else:
    ENGINE_SOCKET_ADDRESS: _Final[tuple[str, int]] = (
        "127.0.0.1", ENGINE_SOCKET_PORT)
    ENGINE_SOCKET_FAMILY: _Final[int] = _socket.AF_INET


ENGINE_SOCKET_KIND: _Final[int] = _socket.SOCK_STREAM

del _socket, _Final

class EngineSocketAPI(IntEnum):
    HEALTH_CHECK = 1
    INFERENCE = 2

class ModelName(StrEnum):
    ARC_FACE = 'ARC_FACE'

@dataclass(kw_only=True)
class ShmTensorSchema:
    shape: tuple[int, ...] | list[int]
    dtype: str
    shm: str
    buf_from: int = 0

    def to_dict(self):
        return {
            'shape': self.shape,
            'dtype': self.dtype,
            'shm': self.shm,
            'buf_from': self.buf_from
        }


__all__ = [
    "ENGINE_SOCKET_ADDRESS",
    "ENGINE_SOCKET_FAMILY",
    "ENGINE_SOCKET_KIND",
    "ENGINE_NUM_WORKERS",
    "EngineSocketAPI",
    "STORAGE_DIR",
    'ShmTensorSchema'
]
