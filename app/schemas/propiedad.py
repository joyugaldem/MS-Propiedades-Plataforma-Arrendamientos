from datetime import datetime
from decimal import Decimal
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
    titulo: str = Field(min_length=3, max_length=200, description="Título descriptivo de la propiedad")
    descripcion: str = Field(min_length=10, max_length=2000, description="Descripción detallada de la propiedad")
    precio: Decimal = Field(gt=0, description="Precio mensual de arrendamiento")
    moneda: Moneda = Field(description="Moneda del precio: CRC o USD")
    provincia: str = Field(description="Provincia de Costa Rica")
    canton: str = Field(description="Cantón dentro de la provincia")
    distrito: str = Field(description="Distrito dentro del cantón")
    tipo: TipoPropiedad = Field(description="Tipo de propiedad")
    estado: EstadoPropiedad = Field(default=EstadoPropiedad.disponible, description="Estado actual de la propiedad")
    imagenes: list[str] = Field(default=[], description="URLs de imágenes de la propiedad")
    idDueno: UUID = Field(description="ID UUID del usuario propietario")
    amenidades: list[str] = Field(default=[], description="Lista de amenidades disponibles")


class PropiedadUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descripcion: str | None = Field(default=None, min_length=10, max_length=2000)
    precio: Decimal | None = Field(default=None, gt=0)
    moneda: Moneda | None = None
    provincia: str | None = None
    canton: str | None = None
    distrito: str | None = None
    tipo: TipoPropiedad | None = None
    estado: EstadoPropiedad | None = None
    imagenes: list[str] | None = None
    idDueno: UUID | None = None
    amenidades: list[str] | None = None


class PropiedadResponse(BaseModel):
    idPropiedad: UUID
    titulo: str
    descripcion: str
    precio: Decimal
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
    fechaActualizacion: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj):
        return cls(
            idPropiedad=obj.id_propiedad,
            titulo=obj.titulo,
            descripcion=obj.descripcion,
            precio=obj.precio,
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
            fechaActualizacion=obj.fecha_actualizacion,
        )


class PropiedadListResponse(BaseModel):
    data: list[PropiedadResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int
