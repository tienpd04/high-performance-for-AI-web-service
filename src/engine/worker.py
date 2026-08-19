
import os
import socket

from src.engine.core.engine import Engine
from src.engine.utils.logging import logger
from src.libs.socket_protocol.server import SocketApplicaltion


def create_engine():

    return Engine(face_recog_model_path="weights/face_extraction.bin")

def create_app(sock: socket.socket, engine: Engine) -> SocketApplicaltion:
    app = SocketApplicaltion(sock, logger=logger, timeout=None)
    setattr(app.state, "engine", engine)
    from src.config.engine import EngineSocketAPI
    from src.engine.api.healthcheck import health_check
    from src.engine.api.inference import inference
    app.register(EngineSocketAPI.HEALTH_CHECK, health_check, "Health Check API")
    app.register(EngineSocketAPI.INFERENCE, inference, "Inference API")
    return app


def start_server_worker(sock: socket.socket, ready_event=None) -> None:
    """Start a simple server worker that listens on a Unix domain socket."""
    pid = os.getpid()
    logger.info("Booting worker with pid: %d", pid)
    logger.info("Waiting for application startup.")
    engine = create_engine()
    app = create_app(sock=sock, engine=engine)
    logger.info("Application startup complete.")
    logger.info("Started server process [%d]", pid)
    if ready_event is not None:
        ready_event.set() # type: ignore
    try:
        app.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    logger.info("Shutting down")
    logger.info("Waiting for application shutdown.")
    engine.cleanup()
    logger.info("Application shutdown complete.")
    logger.info("Finished server process [%d]", pid)


__all__ = [
    "start_server_worker",
]
