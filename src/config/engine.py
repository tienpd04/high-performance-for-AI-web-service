import socket as _socket
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Final as _Final

from .settings import (ENGINE_NUM_WORKERS,
                       ENGINE_UNIX_SOCKET_PATH, STORAGE_DIR)

ENGINE_SOCKET_ADDRESS: _Final[str] = ENGINE_UNIX_SOCKET_PATH
ENGINE_SOCKET_FAMILY: _Final[int] = _socket.AF_UNIX



ENGINE_SOCKET_KIND: _Final[int] = _socket.SOCK_STREAM

del _socket, _Final

class EngineSocketAPI(IntEnum):
    HEALTH_CHECK = 1
    INFERENCE = 2

class ModelName(StrEnum):
    ARC_FACE = 'ARC_FACE'

from copy import deepcopy

@dataclass(kw_only=True)
class ShmTensorSchema:
    shape: tuple[int, ...] | list[int]
    dtype: str
    shm: str
    buf_from: int = 0

    def to_dict(self):
        return deepcopy(self.__dict__)

    def origin_dict(self):
        '''
        Ensure no modify the return dict. If not sure, using 'to_dict' instead
        '''
        return self.__dict__

__all__ = [
    "ENGINE_SOCKET_ADDRESS",
    "ENGINE_SOCKET_FAMILY",
    "ENGINE_SOCKET_KIND",
    "ENGINE_NUM_WORKERS",
    "EngineSocketAPI",
    "STORAGE_DIR",
    'ShmTensorSchema'
]
