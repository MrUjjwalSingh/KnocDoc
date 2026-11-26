"""TravelDoc FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    HAS_SLOWAPI = True
except ImportError:
    limiter = None
    HAS_SLOWAPI = False

try:
    from sqladmin import Admin
    from app.admin.setup import AdminAuth, setup_admin
    HAS_SQLADMIN = True
except ImportError:
    HAS_SQLADMIN = False

from app.config import get_settings
from app.database import engine
from app.routers import config, events, health, providers, reviews, search


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="TravelDoc API",
        description="Medical travel directory — connect travelers with nearby trusted doctors.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Rate limiting
    if HAS_SLOWAPI and limiter:
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(search.router)
    app.include_router(providers.router)
    app.include_router(reviews.router)
    app.include_router(events.router)

    # Admin panel with Auth
    if HAS_SQLADMIN:
        admin_auth = AdminAuth(secret_key=settings.secret_key)
        admin = Admin(app, engine, title="TravelDoc Admin", base_url="/admin", authentication_backend=admin_auth)
        setup_admin(admin)

    # Global error handler
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "An unexpected error occurred."},
        )

    return app


app = create_app()

