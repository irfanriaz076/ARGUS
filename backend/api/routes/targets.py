from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import TargetCreate, TargetResponse
from backend.database.models import Engagement, Target
from backend.database.postgres import get_db

router = APIRouter(prefix="/api/engagements", tags=["targets"])


@router.get("/{engagement_id}/targets", response_model=List[TargetResponse])
async def list_targets(engagement_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Target).where(Target.engagement_id == engagement_id)
    )
    return result.scalars().all()


@router.post(
    "/{engagement_id}/targets",
    response_model=TargetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_target(
    engagement_id: UUID,
    payload: TargetCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Engagement not found")

    target = Target(engagement_id=engagement_id, **payload.model_dump())
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{engagement_id}/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    engagement_id: UUID,
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Target).where(Target.id == target_id, Target.engagement_id == engagement_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    await db.delete(target)
    await db.commit()
