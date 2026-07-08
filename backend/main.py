import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.api.routes import engagements, findings, scans, targets
from backend.api.routes.auth import router as auth_router
from backend.api.routes.graph import router as graph_router
from backend.api.routes.reports import router as reports_router
from backend.api.routes.settings import router as settings_router
from backend.api.websocket import router as ws_router
from backend.auth.dependencies import get_current_user
from backend.auth.jwt import hash_password
from backend.database.models import User
from backend.database.postgres import create_tables, get_db

SCREENSHOT_DIR = "/tmp/argus/screenshots"
log = logging.getLogger("argus")


async def _seed_admin():
    """Create default admin user on first run."""
    from sqlalchemy import select
    from backend.database.postgres import async_session_factory
    async with async_session_factory() as db:
        result = await db.execute(select(User))
        if not result.scalars().first():
            admin = User(
                username="admin",
                email="admin@argus.local",
                hashed_password=hash_password("argus-admin-2025"),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            log.warning(
                "Default admin created — username: admin  password: argus-admin-2025  "
                "CHANGE THIS IMMEDIATELY in Settings → Users."
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await _seed_admin()

    try:
        from backend.database.neo4j_db import init_driver
        await init_driver()
        log.info("Neo4j connected")
    except Exception as exc:
        log.warning("Neo4j unavailable — graph features disabled: %s", exc)

    yield

    try:
        from backend.database.neo4j_db import close_driver
        await close_driver()
    except Exception:
        pass


app = FastAPI(
    title="ARGUS",
    description="Autonomous Reconnaissance & Guided Unified Scanner",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Public routes (no auth) ───────────────────────────────────
app.include_router(auth_router, prefix="/api/auth")
app.include_router(ws_router)

# ── Protected routes (require Bearer token) ───────────────────
_auth = [Depends(get_current_user)]
app.include_router(engagements.router,  dependencies=_auth)
app.include_router(targets.router,      dependencies=_auth)
app.include_router(scans.router,        dependencies=_auth)
app.include_router(findings.router,     dependencies=_auth)
app.include_router(graph_router,        dependencies=_auth)
app.include_router(reports_router,      dependencies=_auth)
app.include_router(settings_router, prefix="/api/settings", dependencies=_auth)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "argus-backend", "version": "2.0.0"}


@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str, _=Depends(get_current_user)):
    path = os.path.join(SCREENSHOT_DIR, filename)
    if not os.path.exists(path) or not filename.endswith(".png"):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(path, media_type="image/png")
