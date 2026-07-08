from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import FindingResponse, FindingUpdate
from backend.database.models import Finding
from backend.database.postgres import get_db

router = APIRouter(prefix="/api", tags=["findings"])


@router.get("/engagements/{engagement_id}/findings", response_model=List[FindingResponse])
async def list_findings(
    engagement_id: UUID,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Finding).where(Finding.engagement_id == engagement_id)
    if severity:
        query = query.where(Finding.severity == severity)
    if status:
        query = query.where(Finding.status == status)
    query = query.order_by(Finding.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/findings", response_model=List[FindingResponse])
async def list_all_findings(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Finding)
    if severity:
        query = query.where(Finding.severity == severity)
    if status:
        query = query.where(Finding.status == status)
    query = query.order_by(Finding.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/findings/count")
async def findings_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.count(Finding.id)))
    return {"total": result.scalar()}


@router.get("/findings/{finding_id}", response_model=FindingResponse)
async def get_finding(finding_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.patch("/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: UUID,
    payload: FindingUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(finding, field, value)

    await db.commit()
    await db.refresh(finding)
    return finding
