
import logging
import socket
import traceback
from socket import SocketType
from typing import Any, Callable, Dict

# from ..client.requests import REQUEST_HEADER_SIZE, ClientRequest
from ..protocol import (API_MAX, API_MIN, REQUEST_HEADER_SIZE,
                        unpack_request_header)
from .request import Request
from .response import JSONResponse, PlainTextResponse, Response

RequestHandler = Callable[[Request], Response]

ExceptionHandler = Callable[[Request, Exception], Response]


def _document_api(req: Request) -> Response:
    '''
    Desctiption for all of APIs
    '''
    app: SocketApplicaltion = req.app
    return PlainTextResponse(app.api_documents())


def _recv_enough(sock: SocketType, size: int) -> bytes:
    chunks = []
    while size > 0:
        chunk = sock.recv(size)
        if not chunk:
            break
        chunks.append(chunk)
        size -= len(chunk)

    return b''.join(chunks)


class _AppState:
    pass


class ClientDisconected(Exception):
    pass


DOCUMENT_API = API_MAX  # API for document of all registered APIs, current value is 65535
REGISTER_API_MIN = API_MIN
REGISTER_API_MAX = DOCUMENT_API - 1


_FIRST_RECV_SIZE = 65536
class SocketApplicaltion:
    _server_sock: SocketType
    _state : _AppState
    _api_handles: Dict[int, RequestHandler]
    _api_documents: Dict[int, tuple[str, str, str]]

    _default_response_class: type[Response]
    _timeout: int | float | None

    _exception_handlers: list[tuple[type[Exception], ExceptionHandler]]

    _logger: logging.Logger | None = None

    def __init__(
        self,
        # NOTE: server_socket must be binded and listesning before run the application
        server_socket: socket.socket,
        *,
        timeout: float | int | None = 300,
        logger: logging.Logger | str = None,
        default_response_class: type[Response] = JSONResponse
    ):
        if not isinstance(server_socket, SocketType):
            raise TypeError(
                f"'server_socket' must be a socket.socket type, not {type(server_socket)}")

        if not isinstance(timeout, float | int | None):
            raise TypeError(
                f"'timeout' must be int, float or None, not {type(timeout)}")

        if not isinstance(default_response_class, type) or not issubclass(default_response_class, Response):
            raise TypeError(
                f"'default_response_class' must be a subclass of {Response.__name__}")

        if timeout is not None and timeout <= 0:
            timeout = None

        self._server_sock = server_socket
        self._timeout = timeout
        self._default_response_class = default_response_class
        self._api_handles = {}
        self._exception_handlers = []
        self._api_documents = {}
        self._state = _AppState()


        if isinstance(logger, logging.Logger):
            self._logger = logger
        elif isinstance(logger, str):
            self._logger = logging.getLogger(logger)

        self._register(DOCUMENT_API, _document_api)

    @property
    def state(self) -> _AppState:
        return self._state

    def register(self, api: int, handle: RequestHandler, description: str = None):
        if not isinstance(api, int) or not REGISTER_API_MIN <= api <= REGISTER_API_MAX:
            raise ValueError(
                f"'api' must be an integer from {REGISTER_API_MIN} to {REGISTER_API_MAX}") from None
        return self._register(api, handle, description)

    def add_exception_handle(self, exp_class: type[Exception], handle: ExceptionHandler):
        if not isinstance(exp_class, type):
            raise ValueError("'exp_class' must be a class type")

        if not issubclass(exp_class, Exception):
            raise ValueError("'exp_class' must be a subclass of Exception")

        insert_index = len(self._exception_handlers)
        for i, (added_exp_class, _) in enumerate(self._exception_handlers):
            if exp_class is added_exp_class:
                raise ValueError(
                    f"Duplicated exception handle. The handle for the exception class '{exp_class.__name__}' already added.")
            if issubclass(exp_class, added_exp_class):
                insert_index = i
                break
        self._exception_handlers.insert(insert_index, (exp_class, handle))

    def api_documents(self) -> str:
        document_list: list[str] = []
        for api in sorted(self._api_documents):
            descript, endpoint, handle_doc = self._api_documents[api]
            doc_str = f"=========\nAPI ID: {api}\nDESCRIPTION: {descript}\nENDPOINT: {endpoint}\nDOCUMENT STRING:\n{handle_doc}"
            document_list.append(doc_str)
        return "\n\n".join(document_list)

    def run(self, raise_exception: bool = False):
        server_sock = self._server_sock
        logger = self._logger
        while True:
            try:
                conn, address = server_sock.accept()
                self._handle(conn, address)
                conn.close()
            except socket.timeout:
                if logger is not None:
                    logger.warning(
                        "Connection timeout from address: '%s'", str(address))
            except ConnectionError:
                if logger is not None:
                    logger.warning(
                        "Disconnected from address: '%s'", str(address))
            except Exception:
                if raise_exception:
                    raise
                else:
                    if logger is not None:
                        logger.error(
                            "Exception from Socket Application:\n%s", traceback.format_exc())

    def _prepare_request(self, conn: SocketType, address) -> Request | None:

        data = conn.recv(_FIRST_RECV_SIZE)
        try:
            api, content_type, content_len = unpack_request_header(data)
        except ValueError:
            res = PlainTextResponse(
                f"Request header required at least {REQUEST_HEADER_SIZE} bytes", status_code=400)
            conn.sendall(res.data)
            return None
        if api not in self._api_handles:
            res = PlainTextResponse(
                f"Request not found with api: {api}", status_code=404)
            conn.sendall(res.data)
            return None
        content = data[REQUEST_HEADER_SIZE:]
        remaining_len = content_len - len(content)

        if remaining_len > 0:
            content += _recv_enough(conn, remaining_len)

        if len(content) != content_len:
            res = PlainTextResponse(
                f"Request content length error, expected {content_len}, got {len(content)}", status_code=400)
            conn.sendall(res.data)
            return None

        return Request(scope={'app': self, 'conn': conn, 'api': api,
                              'content_type': content_type, 'client': address}, content=content)

    def _handle(self, conn: SocketType, address):
        if self._timeout:
            conn.settimeout(self._timeout)
        req = self._prepare_request(conn, address)
        if req is None:
            return
        try:
            response = self._api_handles[req.api](req)
            if not isinstance(response, Response):
                response = self._default_response_class(response)
        except Exception as e:
            found = False
            for exp_cls, exp_handler in self._exception_handlers:
                if isinstance(e, exp_cls):
                    response = exp_handler(req, e)
                    if not isinstance(response, Response):
                        raise TypeError(
                            f"Exception handle must return a Response object, not {type(response)}. Check your exception handler at {exp_handler.__code__.co_filename}:{exp_handler.__code__.co_firstlineno}") from None
                    found = True
                    break
            if not found:
                raise e

        conn.sendall(response.data)

    def _register(self, api: int, handle: RequestHandler, description: str = None):
        api = int(api)
        self._api_handles[api] = handle
        self._api_documents[api] = (
            description or "", handle.__module__ + "." + handle.__name__, handle.__doc__ or "")
