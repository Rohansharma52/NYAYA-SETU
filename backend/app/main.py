"""NYAYA SETU — Integrated Institution Complaint Monitoring Platform (AICTE, SIH PS 26264)."""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _scan_once() -> None:
    from app.services.intelligence import run_alert_scan
    db = SessionLocal()
    try:
        result = run_alert_scan(db)
        if result["total"]:
            logger.info("Alert scan generated %s alerts", result["total"])
    finally:
        db.close()


async def _alert_loop() -> None:
    """Periodic timeline / reminder / escalation / overlap alerting."""
    await asyncio.sleep(5)
    while True:
        try:
            await asyncio.to_thread(_scan_once)
        except Exception as exc:  # never let the loop die
            logger.warning("Alert scan skipped: %s", exc)
        await asyncio.sleep(max(settings.ALERT_SCAN_INTERVAL_MINUTES, 1) * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s — %s", settings.APP_NAME, settings.APP_ENV)
    task = asyncio.create_task(_alert_loop()) if settings.ALERT_SCAN_ENABLED else None
    yield
    if task:
        task.cancel()
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title="NYAYA SETU API",
    description=(
        "Integrated Institution Complaint Monitoring & Coordination Platform for AICTE "
        "(Smart India Hackathon PS 26264). Identity resolution, overlap & conflict intelligence, "
        "lead-bureau coordination, SLA alerts and performance analytics. "
        "All data is DEMO / SYNTHETIC unless explicitly stated."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# ── Health endpoints ───────────────────────────────────────────────────────────

def _check_db() -> str:
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return "connected"
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        return "error"


@app.get("/health", tags=["health"])
@app.get("/api/v1/health", tags=["health"])
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "database": _check_db(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/ready", tags=["health"])
async def ready():
    db_status = _check_db()
    if db_status != "connected":
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": db_status})
    return {"status": "ready", "database": db_status}


# ── Routers ────────────────────────────────────────────────────────────────────
from app.api.v1.router import api_router  # noqa: E402
app.include_router(api_router, prefix="/api/v1")


# ── Single-URL deployment: serve the built React app from the same server ─────
# Used by the Docker / Render image (FRONTEND_DIST=/app/static). Local development
# keeps using the Vite dev server on :5173, so nothing changes there.
import os  # noqa: E402

from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

_DIST = os.environ.get("FRONTEND_DIST", "")
if _DIST and os.path.isfile(os.path.join(_DIST, "index.html")):
    if os.path.isdir(os.path.join(_DIST, "assets")):
        app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        candidate = os.path.realpath(os.path.join(_DIST, full_path))
        if full_path and candidate.startswith(os.path.realpath(_DIST)) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_DIST, "index.html"))
