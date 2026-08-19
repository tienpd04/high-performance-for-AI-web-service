import os
import signal
import socket
import sys

from src.config.engine import (ENGINE_NUM_WORKERS, ENGINE_SOCKET_ADDRESS,
                               ENGINE_SOCKET_FAMILY, ENGINE_SOCKET_KIND)

if ENGINE_NUM_WORKERS == 1:
    from src.engine.utils.logging import logger as logger

else:
    import logging
    logger = logging.getLogger("engine_main")
    def worker_signal_handler(signum, frame):
        sys.exit(0)

    def worker_process(server_socket, ready_event):
        from src.engine.worker import start_server_worker
        start_server_worker(server_socket, ready_event=ready_event)



def signal_handler(signum, frame):
    signame = f"{signum}"
    for sig in signal.Signals:
        if signum == sig:
            signame = sig.name
            break
    logger.info("Handling signal: %s", signame)
    sys.exit(0)


def engine_target(ready_event=None):
    logger.info("Starting Engine Socket")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
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
    if ENGINE_NUM_WORKERS == 1:

        from src.engine.worker import start_server_worker
        start_server_worker(server_socket, ready_event=ready_event)
    else:
        from multiprocessing import Process
        workers: list[Process] = []
        for _ in range(ENGINE_NUM_WORKERS):
            worker = Process(target=worker_process, args=(server_socket, ready_event))
            worker.start()
            workers.append(worker)

        try:
            for worker in workers:
                worker.join()
        except KeyboardInterrupt | SystemExit:
            pass

        for worker in workers:
            worker.terminate()
            worker.join()

    logger.info("Shutting down: Master")
    server_socket.close()
    if isinstance(address, str) and os.path.exists(address):
        try:
            os.remove(address)
        except Exception:
            pass


if __name__ == "__main__":
    engine_target()
