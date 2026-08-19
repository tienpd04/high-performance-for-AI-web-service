
from fastapi import FastAPI


def create_app() -> FastAPI:
    from src.web.routers import api_router
    app = FastAPI()
    app.include_router(api_router)
    return app

app = create_app()