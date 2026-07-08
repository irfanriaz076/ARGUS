import os
from typing import Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user, require_admin
from backend.database.models import Setting, User
from backend.database.postgres import get_db

router = APIRouter(tags=["settings"])

DEFAULT_SETTINGS = [
    {"key": "shodan_api_key",    "value": "", "is_secret": True},
    {"key": "github_token",      "value": "", "is_secret": True},
    {"key": "nvd_api_key",       "value": "", "is_secret": True},
    {"key": "slack_webhook_url", "value": "", "is_secret": True},
    {"key": "webhook_url",       "value": "", "is_secret": True},
    {"key": "notify_on_critical","value": "true",  "is_secret": False},
    {"key": "notify_on_high",    "value": "false", "is_secret": False},
    {"key": "wpscan_api_key",    "value": "", "is_secret": True},
]


class SettingOut(BaseModel):
    key: str
    value: str
    is_secret: bool
    configured: bool


class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, str]


async def _ensure_defaults(db: AsyncSession):
    for default in DEFAULT_SETTINGS:
        result = await db.execute(select(Setting).where(Setting.key == default["key"]))
        if not result.scalar_one_or_none():
            db.add(Setting(**default))
    await db.commit()


@router.get("", response_model=List[SettingOut])
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    await _ensure_defaults(db)
    result = await db.execute(select(Setting).order_by(Setting.key))
    settings = result.scalars().all()

    out = []
    for s in settings:
        # Env vars take priority — show env value masked or DB value masked
        env_val = os.environ.get(s.key.upper(), "")
        effective = env_val or s.value
        out.append(SettingOut(
            key=s.key,
            value="••••••••" if s.is_secret and effective else effective,
            is_secret=s.is_secret,
            configured=bool(effective),
        ))
    return out


@router.put("")
async def update_settings(
    body: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    await _ensure_defaults(db)
    for key, value in body.settings.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting is not None:
            if value:  # Only update if non-empty (don't clear with "")
                setting.value = value
                # Also update runtime env so current worker picks it up
                os.environ[key.upper()] = value
    await db.commit()
    return {"saved": len(body.settings)}


async def load_settings_to_env(db: AsyncSession):
    """Called at task start to pull DB settings into os.environ."""
    result = await db.execute(select(Setting))
    for s in result.scalars().all():
        if s.value and not os.environ.get(s.key.upper()):
            os.environ[s.key.upper()] = s.value
