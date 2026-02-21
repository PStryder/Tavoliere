from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.routes import router as auth_router
from backend.api.tables import router as tables_router
from backend.api.actions import router as actions_router
from backend.api.chat import router as chat_router
from backend.api.consent import router as consent_router
from backend.api.research import router as research_router
from backend.api.ws import router as ws_router
from backend.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(tables_router)
    app.include_router(actions_router)
    app.include_router(chat_router)
    app.include_router(research_router)
    app.include_router(consent_router)
    app.include_router(ws_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
