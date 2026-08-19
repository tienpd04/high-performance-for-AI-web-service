import logging
import secrets
import sys

from fastapi import Request


def setup_logging():
    log_level = logging.INFO
    logger = logging.getLogger("app_logger")
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        'logs/app.log', maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


def rq_log(request: Request, msg: str, level: int = logging.INFO):
    """
    Enhanced logging with request context
    """
    if level < logger.level:
        return

    # Get or generate request ID
    if not hasattr(request.state, 'request_id'):
        request_id = secrets.token_hex(8).upper()
        request.state.request_id = request_id
    else:
        request_id = request.state.request_id

    # Get client info
    client_ip = request.headers.get('X-Forwarded-For') or request.headers.get('X-Real-IP') or request.client.host if request.client else "unknown"
    user_agent = request.headers.get('User-Agent', 'unknown')
    if len(user_agent) > 20:
        user_agent = user_agent[:17] + '...'

    # Build enhanced log message
    log_msg = f"[{request_id}] [{client_ip} {user_agent}] [{request.method} {request.url.path}] - {msg}"

    logger.log(level, log_msg)


def rq_log_info(request: Request, msg: str):
    rq_log(request, msg, logging.INFO)


def rq_log_error(request: Request, msg: str):
    rq_log(request, msg, logging.ERROR)


def rq_log_warning(request: Request, msg: str):
    rq_log(request, msg, logging.WARNING)

def rq_log_debug(request: Request, msg: str):
    rq_log(request, msg, logging.DEBUG)


__all__ = [
    "logger",
    "rq_log",
    "rq_log_info",
    "rq_log_error",
    "rq_log_warning",
    "rq_log_debug",
]
