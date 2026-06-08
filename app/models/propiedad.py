import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base


class Propiedad(Base):
    __tablename__ = "propiedades"

    id_propiedad: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    provincia: Mapped[str] = mapped_column(String(50), nullable=False)
    canton: Mapped[str] = mapped_column(String(100), nullable=False)
    distrito: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="disponible")
    imagenes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=lambda: [])
    id_dueno: Mapped[str] = mapped_column(String(100), nullable=False)
    amenidades: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=lambda: [])
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    fecha_actualizacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_propiedades_id_dueno", "id_dueno"),
        Index("ix_propiedades_provincia_tipo", "provincia", "tipo"),
        Index("ix_propiedades_precio", "precio"),
        Index("ix_propiedades_estado", "estado"),
    )
