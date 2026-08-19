import logging
import os
import random
import sys
from logging.handlers import RotatingFileHandler

from fastapi import Request


def setup_logging():
    log_level = logging.INFO
    logger = logging.getLogger("engine_logger")
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(process)d] [%(levelname)s] %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    file_handler = RotatingFileHandler(
        'logs/engine.log', maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()