
def uvicorn_target():
    import os

    from src.config.settings import (HOST, LOG_LEVEL, NUM_WORKERS, PORT,
                                     WORKER_CONNECTIONS)
    if os.name == 'nt':
        import multiprocessing
        multiprocessing.freeze_support()

    import uvicorn
    uvicorn.run('src.web.asgi_app:app', host=HOST, port=PORT, workers=NUM_WORKERS, limit_concurrency=WORKER_CONNECTIONS,  access_log=False, log_level=LOG_LEVEL)


def gunicorn_target():

    import sys

    from src.config.settings import (ACCESS_LOG_FILE, ERROR_LOG_FILE, HOST,
                                     LOG_LEVEL, NUM_WORKERS, PORT,
                                     WORKER_CONNECTIONS)
    sys.argv.clear()
    sys.argv.append("gunicorn")
    sys.argv.append(f"-b {HOST}:{PORT}")
    sys.argv.append(f"--workers={NUM_WORKERS}")
    sys.argv.append(f"--worker-class=uvicorn.workers.UvicornWorker")
    sys.argv.append(f"--timeout=300")
    sys.argv.append(f"--log-level={LOG_LEVEL}")
    sys.argv.append(f"--access-logfile={ACCESS_LOG_FILE}")
    sys.argv.append(f"--error-logfile={ERROR_LOG_FILE}")
    sys.argv.append(f"--worker-connections={WORKER_CONNECTIONS}")
    sys.argv.append("src.web.asgi_app:app")
    from gunicorn.app.wsgiapp import run
    run()

if __name__ == "__main__":
    gunicorn_target()
