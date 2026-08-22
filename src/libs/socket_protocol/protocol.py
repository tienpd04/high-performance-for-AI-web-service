
from enum import IntEnum
from typing import Final, Tuple

__all__ = [
    "RequestContentType",
    "ResponseContentType",
    "API_MIN",
    "API_MAX",
    "REQUEST_HEADER_SIZE",
    "RESPONSE_HEADER_SIZE",
    "STATUS_CODE_MIN",
    "STATUS_CODE_MAX",
    "pack_request_header",
    "unpack_request_header",
    "pack_response_header",
    "unpack_response_header"
]

STATUS_CODE_MIN: Final[int] = 0
STATUS_CODE_MAX: Final[int] = 65535

CONTENT_TYPE_MIN: Final[int] = 0
CONTENT_TYPE_MAX: Final[int] = 65535

API_MIN: Final[int] = 0
API_MAX: Final[int] = 65535


class RequestContentType(IntEnum):
    BYTES = 1
    TEXT = 2
    JSON = 3

class ResponseContentType(IntEnum):
    BYTES = 1
    TEXT = 2
    JSON = 3


REQUEST_HEADER_SIZE: Final[int] = 8
RESPONSE_HEADER_SIZE: Final[int] = 8


def pack_request_header(api: int, content_type: int, content: bytes | memoryview) -> bytes:
    return api.to_bytes(2,'little') + \
            content_type.to_bytes(2,'little') + \
                len(content).to_bytes(4,'little')

def unpack_request_header(buff: bytes) -> Tuple[int, int, int]:
    if len(buff) < REQUEST_HEADER_SIZE:
        raise ValueError(f"\'buff\' required at least {REQUEST_HEADER_SIZE} number of bytes")

    api = int.from_bytes(buff[:2],'little')
    content_type = int.from_bytes(buff[2:4],'little')
    content_len = int.from_bytes(buff[4:8],'little')
    return api, content_type, content_len


def pack_response_header(status_code: int, content_type: int, content: bytes) -> bytes:
    return status_code.to_bytes(2,'little') + \
            content_type.to_bytes(2,'little') + \
                len(content).to_bytes(4,'little')

def unpack_response_header(buff: bytes) -> Tuple[int, int, int]:
    if len(buff) < RESPONSE_HEADER_SIZE:
        raise ValueError(f"\'buff\' required at least {RESPONSE_HEADER_SIZE} number of bytes")

    status_code = int.from_bytes(buff[:2],'little')
    content_type = int.from_bytes(buff[2:4],'little')
    content_len = int.from_bytes(buff[4:8],'little')
    return status_code, content_type, content_len


