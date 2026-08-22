import sys
from multiprocessing.shared_memory import SharedMemory


def _web_process():
    from src.web.target import web_target
    web_target()


def _engine_process(ready_event=None):
    from src.engine.target import engine_target
    engine_target(ready_event=ready_event)



_logger = None


def _setup_logging():
    import logging
    log_level = logging.INFO
    logger = logging.getLogger("main_logger")
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)
    from logging.handlers import TimedRotatingFileHandler

    file_handler = TimedRotatingFileHandler(
        'logs/main.log', when='MIDNIGHT', backupCount=7)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def _create_resources() -> tuple[list, dict[str, int]]:

    from src.config.settings import (NUM_WORKERS, RESOURCE_NUM_SHM_PER_WORKER,
                                     RESOURCE_SHM_SIZE_MB)
    _logger.info("Creating shared resources using beween processes")

    RESOURCE_NUM_SHM = RESOURCE_NUM_SHM_PER_WORKER * (NUM_WORKERS + 2) # backup more 2 for sometime web worker crash
    shm_list: list[SharedMemory] = []
    for i in range(RESOURCE_NUM_SHM):
        shm = SharedMemory(name=f"Shm_{i:02d}", create=True, size=RESOURCE_SHM_SIZE_MB * 1024 * 1024)
        shm_list.append(shm)
    _logger.info("Created %d shared memory with each size %d MB", RESOURCE_NUM_SHM, RESOURCE_SHM_SIZE_MB)
    resources = {k.name: k.size for k in shm_list}
    return shm_list, resources


def _cleanup_resources(shm_list: list[SharedMemory]):
    for shm in shm_list:
        try:
            shm.close()
            shm.unlink()
        except Exception as e:
            _logger.warning(f"Error while releasing shared memory: {e}")


def _load_env():
    import argparse
    parser = argparse.ArgumentParser(
        description="Check resource and engine services is ready")

    parser.add_argument("-e", "--env_file", default=None,
                        help="Envirionment file to load. Default to None")

    args = parser.parse_args()
    env_file = args.env_file
    if env_file:
        import dotenv
        dotenv.load_dotenv(env_file)


def main():

    _load_env()

    global _logger
    _logger = _setup_logging()

    shm_list, resources = _create_resources()
    from src import resourcesmng
    resourcesmng.initialize(resouces=resources)

    from multiprocessing import Event, Process

    _logger.info("Starting Engine and Web Application")


    _logger.info("Starting Engine Application")
    engine_ready_event = Event()
    engine_p = Process(target=_engine_process, args=(engine_ready_event,))
    engine_p.start()

    # Wait for the engine process to signal that it's ready
    if not engine_ready_event.wait(timeout=30):
        _logger.error("Engine process failed to start.")
        _cleanup_resources(shm_list)
        sys.exit(1)


    _logger.info("Start & Running Web Application")

    try:
        _web_process()
    except KeyboardInterrupt:
        _logger.info("Shutting down program")
    except Exception:
        import traceback
        _logger.error(traceback.format_exc())
    except SystemExit as e:
        if e.code != 0:
            from src.config.settings import ERROR_LOG_FILE
            _logger.error(
                "Unable to start the web application. Please open '%s' to view the details.", ERROR_LOG_FILE)

    _logger.info("Terminate Engine Application")
    engine_p.terminate()
    engine_p.join()


    _logger.info("Cleanup shared resources")
    _cleanup_resources(shm_list)
    _logger.info("Program terminated successfully.")


if __name__ == '__main__':
    main()
