import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.propiedad import Propiedad
from app.schemas.propiedad import (
    PropiedadCreate,
    PropiedadListResponse,
    PropiedadResponse,
    PropiedadUpdate,
)

router = APIRouter(prefix="/propiedades", tags=["propiedades"])


@router.get("", response_model=PropiedadListResponse)
async def listar_propiedades(
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1, le=100),
    search: str | None = Query(None),
    provincia: str | None = Query(None),
    tipo: str | None = Query(None),
    precioMin: float | None = Query(None, ge=0),
    precioMax: float | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Propiedad)

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Propiedad.titulo.ilike(term),
                Propiedad.provincia.ilike(term),
                Propiedad.canton.ilike(term),
                Propiedad.distrito.ilike(term),
            )
        )
    if provincia:
        query = query.where(Propiedad.provincia == provincia)
    if tipo:
        query = query.where(Propiedad.tipo == tipo)
    if precioMin is not None:
        query = query.where(Propiedad.precio >= precioMin)
    if precioMax is not None:
        query = query.where(Propiedad.precio <= precioMax)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * limit
    result = await db.execute(
        query.order_by(Propiedad.fecha_creacion.desc()).offset(offset).limit(limit)
    )
    propiedades = result.scalars().all()

    return PropiedadListResponse(
        data=[PropiedadResponse.from_orm(p) for p in propiedades],
        total=total,
        page=page,
        pageSize=limit,
        totalPages=math.ceil(total / limit) if total else 0,
    )


@router.post("", response_model=PropiedadResponse, status_code=status.HTTP_201_CREATED)
async def crear_propiedad(
    body: PropiedadCreate,
    db: AsyncSession = Depends(get_db),
):
    propiedad = Propiedad(
        titulo=body.titulo,
        descripcion=body.descripcion,
        precio=body.precio,
        moneda=body.moneda,
        provincia=body.provincia,
        canton=body.canton,
        distrito=body.distrito,
        tipo=body.tipo,
        estado=body.estado,
        imagenes=body.imagenes,
        id_dueno=body.idDueno,
        amenidades=body.amenidades,
    )
    db.add(propiedad)
    await db.commit()
    await db.refresh(propiedad)
    return PropiedadResponse.from_orm(propiedad)


@router.get("/dueno/{dueno_id}", response_model=list[PropiedadResponse])
async def propiedades_por_dueno(
    dueno_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Propiedad)
        .where(Propiedad.id_dueno == dueno_id)
        .order_by(Propiedad.fecha_creacion.desc())
    )
    propiedades = result.scalars().all()
    return [PropiedadResponse.from_orm(p) for p in propiedades]


@router.get("/{propiedad_id}", response_model=PropiedadResponse)
async def obtener_propiedad(
    propiedad_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Propiedad).where(Propiedad.id_propiedad == propiedad_id)
    )
    propiedad = result.scalar_one_or_none()
    if not propiedad:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")
    return PropiedadResponse.from_orm(propiedad)


@router.put("/{propiedad_id}", response_model=PropiedadResponse)
async def actualizar_propiedad(
    propiedad_id: UUID,
    body: PropiedadUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Propiedad).where(Propiedad.id_propiedad == propiedad_id)
    )
    propiedad = result.scalar_one_or_none()
    if not propiedad:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")

    updates = body.model_dump(exclude_unset=True)
    field_map = {
        "idDueno": "id_dueno",
    }
    for key, value in updates.items():
        db_key = field_map.get(key, key)
        setattr(propiedad, db_key, value)

    await db.commit()
    await db.refresh(propiedad)
    return PropiedadResponse.from_orm(propiedad)


@router.delete("/{propiedad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_propiedad(
    propiedad_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Propiedad).where(Propiedad.id_propiedad == propiedad_id)
    )
    propiedad = result.scalar_one_or_none()
    if not propiedad:
        raise HTTPException(status_code=404, detail="Propiedad no encontrada")

    await db.delete(propiedad)
    await db.commit()
