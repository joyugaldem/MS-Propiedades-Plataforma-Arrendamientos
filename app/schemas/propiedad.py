from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class TipoPropiedad(str, Enum):
    casa = "casa"
    apartamento = "apartamento"
    local = "local"
    bodega = "bodega"
    oficina = "oficina"


class EstadoPropiedad(str, Enum):
    disponible = "disponible"
    alquilada = "alquilada"
    mantenimiento = "mantenimiento"


class Moneda(str, Enum):
    CRC = "CRC"
    USD = "USD"


class PropiedadCreate(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10)
    precio: float = Field(gt=0)
    moneda: Moneda
    provincia: str
    canton: str
    distrito: str
    tipo: TipoPropiedad
    estado: EstadoPropiedad = EstadoPropiedad.disponible
    imagenes: list[str] = []
    idDueno: str
    amenidades: list[str] = []


class PropiedadUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, min_length=10)
    precio: float | None = Field(default=None, gt=0)
    moneda: Moneda | None = None
    provincia: str | None = None
    canton: str | None = None
    distrito: str | None = None
    tipo: TipoPropiedad | None = None
    estado: EstadoPropiedad | None = None
    imagenes: list[str] | None = None
    amenidades: list[str] | None = None


class PropiedadResponse(BaseModel):
    idPropiedad: UUID
    titulo: str
    descripcion: str
    precio: float
    moneda: Moneda
    provincia: str
    canton: str
    distrito: str
    tipo: TipoPropiedad
    estado: EstadoPropiedad
    imagenes: list[str]
    idDueno: str
    amenidades: list[str]
    fechaCreacion: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj):
        return cls(
            idPropiedad=obj.id_propiedad,
            titulo=obj.titulo,
            descripcion=obj.descripcion,
            precio=float(obj.precio),
            moneda=obj.moneda,
            provincia=obj.provincia,
            canton=obj.canton,
            distrito=obj.distrito,
            tipo=obj.tipo,
            estado=obj.estado,
            imagenes=obj.imagenes or [],
            idDueno=obj.id_dueno,
            amenidades=obj.amenidades or [],
            fechaCreacion=obj.fecha_creacion,
        )


class PropiedadListResponse(BaseModel):
    data: list[PropiedadResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int
