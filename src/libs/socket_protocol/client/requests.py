import json
import socket
from typing import Any

from ..protocol import (API_MAX, API_MIN, RESPONSE_HEADER_SIZE,
                        RequestContentType, ResponseContentType,
                        pack_request_header, unpack_response_header)
from .exceptions import *

_JSON = Any


class ClientRequest:
    content_type = RequestContentType.BYTES
    charset = "utf-8"

    def __init__(
        self,
        api: int,
        content: Any = None,

    ) -> None:
        self.api = api
        self.content = content

    def render(self, content: Any) -> bytes | memoryview:
        if content is None:
            return b""
        if isinstance(content, bytes | memoryview):
            return content
        return content.encode(self.charset)  # type: ignore

    def pack(self) -> bytes:
        content = self.render(self.content)
        header = pack_request_header(self.api, self.content_type, content)
        return header + content


class PlainTextRequest(ClientRequest):
    content_type = RequestContentType.TEXT


class JSONRequest(ClientRequest):
    content_type = RequestContentType.JSON

    def __init__(
        self,
        api: int,
        content: Any

    ) -> None:
        super().__init__(api, content)

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


class Response:
    _content: bytes
    status_code: int
    content_type: ResponseContentType

    def __init__(self, status_code: int, content: bytes, content_type: ResponseContentType):
        self.status_code = status_code
        self._content = content
        self.content_type = content_type

    @property
    def content(self) -> bytes | None:
        return self._content

    @property
    def text(self) -> str:
        try:
            return self.content.decode()
        except Exception:
            raise ContentDecodingError("Failed to decode content as text")

    def json(self) -> Any:
        try:
            return json.loads(self.content)
        except Exception:
            raise ContentDecodingError("Failed to decode content as JSON")

    def parser(self) -> bytes | str | _JSON:
        match self.content_type:
            case ResponseContentType.TEXT:
                return self.text
            case ResponseContentType.JSON:
                return self.json()
            case _:
                return self.content

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise StatusCodeError(f"Status code = {self.status_code}")


def _recv_enough(sock: socket.socket, size: int) -> bytes:
    chunks = []
    while size > 0:
        chunk = sock.recv(size)
        if not chunk:
            break
        chunks.append(chunk)
        size -= len(chunk)

    return b''.join(chunks)


def request(
    address: tuple[str, int] | str,
    api: int,
    *,
    data: bytes | str | _JSON = None,
    address_family: int = socket.AF_INET,
    socket_kind: int = socket.SOCK_STREAM,
    timeout: float = None,
    first_rcv_size: int = 65536,

) -> Response:
    if not isinstance(api, int) or api < API_MIN or api > API_MAX:
        raise ValueError(f"\'api\' must be an integer between {API_MIN} and {API_MAX}")
    if data is None or isinstance(data, bytes | memoryview):
        req = ClientRequest(api, data)
    elif isinstance(data, str):
        req = PlainTextRequest(api, data)
    else:
        req = JSONRequest(api, data)
    try:
        req_data = req.pack()
    except Exception as e:
        raise ContentEncodingError(
            "'data' must be a bytes, memoryview, str or jsonable data type") from e

    with socket.socket(address_family, socket_kind) as client:
        try:
            if timeout:
                client.settimeout(timeout)
            client.connect(address)
            client.sendall(req_data)
            buff = client.recv(max(first_rcv_size, RESPONSE_HEADER_SIZE))
            try:
                status_code, content_type, content_len = unpack_response_header(
                    buff)
            except ValueError:
                raise ProtocolError(
                    f"Required at least {RESPONSE_HEADER_SIZE} bytes of header to received, atual received: {len(buff)}")

            content = buff[RESPONSE_HEADER_SIZE:]
            remaining_len = content_len - len(content)
            if remaining_len > 0:
                content += _recv_enough(
                    client, remaining_len)
            if len(content) != content_len:
                raise ProtocolError(
                    f"Not enough content length received, expected: {content_len}, actual: {len(content)}")
            response = Response(status_code, content, content_type)
            return response
        except socket.timeout as e:
            raise RequestTimeoutError(
                f"Timeout after {timeout}s when connecting to {address}") from e
        except ConnectionRefusedError as e:
            raise RequestConnectionError(
                f"Connection refused to socket: {address}") from e
        except BrokenPipeError as e:
            raise RequestConnectionError(
                f"The connection was disconnected during the request to the socket: {address}") from e
