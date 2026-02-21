from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.auth.routes import router as auth_router
from backend.api.tables import router as tables_router
from backend.api.actions import router as actions_router
from backend.api.chat import router as chat_router
from backend.api.consent import router as consent_router
from backend.api.research import router as research_router
from backend.api.history import router as history_router
from backend.api.profile import router as profile_router
from backend.api.admin import router as admin_router
from backend.api.conventions import router as conventions_router
from backend.api.research_sessions import router as research_sessions_router
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
    app.include_router(history_router)
    app.include_router(profile_router)
    app.include_router(admin_router)
    app.include_router(conventions_router)
    app.include_router(research_sessions_router)
    app.include_router(ws_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # Serve React SPA — all non-API routes return index.html
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        index = frontend_dist / "index.html"
        if index.is_file():
            return FileResponse(index)
        return {"detail": "Frontend not built. Run: cd frontend && npm run build"}

    return app


app = create_app()
