import os
import signal
import socket
import sys

from src.config.engine import (ENGINE_NUM_WORKERS, ENGINE_SOCKET_ADDRESS,
                               ENGINE_SOCKET_FAMILY, ENGINE_SOCKET_KIND)

def _setup_logging():
    import logging
    from logging.handlers import TimedRotatingFileHandler
    log_level = logging.INFO
    logger = logging.getLogger("engine_master")
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(process)d] [%(levelname)s] %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    file_handler = TimedRotatingFileHandler(
        'logs/engine_master.log', when='MIDNIGHT', backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = _setup_logging()




def _signal_handler(signum, frame):
    signame = f"{signum}"
    for sig in signal.Signals:
        if signum == sig:
            signame = sig.name
            break
    logger.info("Handling signal: %s", signame)
    sys.exit(0)


def engine_target(ready_event=None):
    logger.info("Starting Engine Service")
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    server_socket = socket.socket(ENGINE_SOCKET_FAMILY, ENGINE_SOCKET_KIND)
    address = ENGINE_SOCKET_ADDRESS

    if isinstance(address, str) and os.path.exists(address):
        try:
            os.remove(address)
        except Exception:
            pass

    server_socket.bind(address)
    server_socket.listen(128)
    logger.info("Listening at: %s", str(address))
    running_workers_count = 0
    normal_exit_workers_count = 0
    child_pids = set()
    logger.info("Starting %d worker(s)...", ENGINE_NUM_WORKERS)
    while running_workers_count < ENGINE_NUM_WORKERS:
        pid = os.fork()
        if pid == 0:
            # Child process
            from engine.worker import start_server_worker
            start_server_worker(server_socket, ready_event=ready_event)
            os._exit(0)
        else:
            # Parent process
            running_workers_count += 1
            child_pids.add(pid)
            if running_workers_count < ENGINE_NUM_WORKERS:
                continue
            try:
                while normal_exit_workers_count < ENGINE_NUM_WORKERS:
                    child_pid, status = os.wait()
                    if os.WIFEXITED(status):
                        exit_code = os.WEXITSTATUS(status)
                        logger.info("Engine worker %d exited with code %d", child_pid, exit_code)
                        normal_exit_workers_count += 1
                        child_pids.discard(child_pid)
                    elif os.WIFSIGNALED(status):
                        term_signal = os.WTERMSIG(status)
                        logger.error("Engine worker %d terminated by signal %d", child_pid, term_signal)
                        running_workers_count -= 1
                        child_pids.discard(child_pid)
                        break
            except (KeyboardInterrupt, SystemExit):
                break
    for pid in child_pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for pid in child_pids:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass

    logger.info("Shutting down: Master")
    server_socket.close()
    if isinstance(address, str) and os.path.exists(address):
        try:
            os.remove(address)
        except Exception:
            pass


if __name__ == "__main__":
    engine_target()
