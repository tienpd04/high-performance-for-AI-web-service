import os as _os
from typing import Literal as _Literal
from typing import Type as _Type
from typing import cast as _cast


class _EnvironmentSettingError(EnvironmentError):
    pass


def _getenv(key: str, default=None, strip=True, required=False, cast: _Type = None) -> str | int | None:
    v = _os.getenv(key, default)
    if strip and isinstance(v, str):
        v = v.strip()

    if required and not v:
        raise _EnvironmentSettingError(
            f"Environment \"{key}\" is required") from None

    if cast is not None:
        try:
            v = cast(v)
        except Exception:
            raise _EnvironmentSettingError(
                f"Environment \"{key}\" must be a {cast.__name__}: '{v}'") from None
    return v


HOST: str = _getenv("HOST", "0.0.0.0")

PORT: int = _getenv("PORT", 8000, cast=int)

NUM_WORKERS: int = _getenv("ENGINE_SOCKET_PORT", 4, cast=int)

WORKER_CONNECTIONS: int = _getenv(
    "WORKER_CONNECTIONS", 64, cast=int)

ERROR_LOG_FILE: str = _getenv(
    "ERROR_LOG_FILE", "logs/gunicorn-error.log")

ACCESS_LOG_FILE: str = _getenv("ACCESS_LOG_FILE", "-")

LOG_LEVEL: _Literal['error', 'warning', 'info', 'debug'] = {k: k for k in ('error', 'warning', 'info', 'debug')}.get(
    _cast(str, _getenv("LOG_LEVEL", "info")).lower(), 'info')



STORAGE_DIR: str = _getenv("STORAGE_DIR", "/tmp/storage")


ENGINE_UNIX_SOCKET_PATH: str | None = _getenv("ENGINE_UNIX_SOCKET_PATH") if _os.name == 'posix' else None

ENGINE_SOCKET_PORT: int | None = _getenv("ENGINE_SOCKET_PORT", 4000, cast=int) if not ENGINE_UNIX_SOCKET_PATH else None

ENGINE_NUM_WORKERS: int = _getenv("ENGINE_NUM_WORKERS", 1, cast=int)

RESOURCE_SHM_SIZE_MB: int = _getenv("RESOURCE_SHM_SIZE_MB", 32, cast=int)

RESOURCE_NUM_SHM_PER_WORKER: int = _getenv("RESOURCE_NUM_SHM_PER_WORKER", 1, cast=int)

RESOURCE_SHM_USE_TIMEOUT: int = _getenv("RESOURCE_SHM_USE_TIMEOUT", 1800, cast=int)


ARC_FACE_MODEL_PATH: str = _getenv('ARC_FACE_MODEL_PATH', "weights/face_extraction.bin")



del _Type, _os, _getenv, _cast

__all__ = [x for x in locals() if not x.startswith("_")]
