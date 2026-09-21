import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Place
from schemas import PlaceCreate, PlaceRead

router = APIRouter(prefix="/places", tags=["places"])


@router.post("/", response_model=PlaceRead, status_code=status.HTTP_201_CREATED)
async def create_place(data: PlaceCreate, db: AsyncSession = Depends(get_db)):
    place = Place(**data.model_dump())
    db.add(place)
    await db.commit()
    await db.refresh(place)
    return place


@router.get("/", response_model=list[PlaceRead])
async def list_places(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Place).order_by(Place.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{place_id}", response_model=PlaceRead)
async def get_place(place_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    place = await db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place
