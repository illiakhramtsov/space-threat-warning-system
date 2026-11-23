import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import admin, auth, home, threats, users
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.event_broker import event_broker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize database tables and background EDA consumer on startup."""
    from app.models import threat, user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    event_broker.start(SessionLocal)
    try:
        yield
    finally:
        await event_broker.stop()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()
    application = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        debug=settings.DEBUG,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def attach_server_identity(request: Request, call_next):
        """Attach X-Server-ID header and mask 500 stack traces in Production."""
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception("Unhandled application error: %s", exc)
            current_settings = get_settings()
            content: dict[str, str] = {
                "detail": "Internal Server Error",
                "server_id": current_settings.INSTANCE_NAME,
            }
            if current_settings.DEBUG:
                content["debug_error"] = str(exc)
            response = JSONResponse(status_code=500, content=content)
        response.headers["X-Server-ID"] = get_settings().INSTANCE_NAME
        return response

    @application.get("/", tags=["System"])
    def root() -> dict:
        current_settings = get_settings()
        return {
            "service": current_settings.APP_NAME,
            "domain": "Space Threat Warning System (EDA - Variant 9)",
            "environment": current_settings.APP_ENV,
            "debug": current_settings.DEBUG,
            "server_id": current_settings.INSTANCE_NAME,
        }

    @application.get("/health", tags=["System"])
    def healthcheck() -> dict:
        return {
            "status": "ok",
            "server_id": get_settings().INSTANCE_NAME,
            "broker": event_broker.stats(),
        }

    @application.get("/api/v1/system/simulate-error", tags=["System"])
    def simulate_internal_error() -> None:
        """Endpoint for verifying safe 500 error masking in Production."""
        raise RuntimeError("Simulated internal telemetry parser crash")

    application.include_router(auth.router)
    application.include_router(users.router)
    application.include_router(home.router)
    application.include_router(threats.router)
    application.include_router(admin.router)

    return application


app = create_app()
