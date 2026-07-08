from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import ScanResponse
from backend.database.models import Scan
from backend.database.postgres import get_db

router = APIRouter(prefix="/api", tags=["scans"])


@router.get("/engagements/{engagement_id}/scans", response_model=List[ScanResponse])
async def list_scans(engagement_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scan)
        .where(Scan.engagement_id == engagement_id)
        .order_by(Scan.started_at.desc())
    )
    return result.scalars().all()


@router.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan
