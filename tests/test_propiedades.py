"""
Tests unitarios para MS-Propiedades.

No requieren PostgreSQL: la sesión de DB se reemplaza con un AsyncMock.
Correr: pytest tests/ -v
"""

import math
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models.propiedad import Propiedad


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_propiedad(**kwargs) -> Propiedad:
    defaults = dict(
        id_propiedad=uuid.uuid4(),
        titulo="Casa en San José",
        descripcion="Descripción de prueba con más de diez caracteres.",
        precio=Decimal("500000.00"),
        moneda="CRC",
        provincia="San José",
        canton="Escazú",
        distrito="Escazú",
        tipo="casa",
        estado="disponible",
        imagenes=["https://example.com/img.jpg"],
        id_dueno=str(uuid.uuid4()),
        amenidades=["parqueo"],
        fecha_creacion=datetime.now(timezone.utc),
        fecha_actualizacion=None,
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=Propiedad)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def make_db_session(propiedades: list | None = None, propiedad: Propiedad | None = None):
    """Construye un AsyncMock de AsyncSession con respuestas predefinidas."""
    session = AsyncMock()

    if propiedades is not None:
        count_result = MagicMock()
        count_result.scalar_one.return_value = len(propiedades)

        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = propiedades

        single_result = MagicMock()
        single_result.scalar_one_or_none.return_value = propiedad

        session.execute.side_effect = [count_result, list_result]
    elif propiedad is not None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = propiedad
        session.execute.return_value = result

    return session


def override_db(session):
    async def _override():
        yield session
    return _override


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self):
        with patch("app.main.engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=False)

            with TestClient(app) as client:
                resp = client.get("/health")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestListarPropiedades:
    def test_retorna_estructura_correcta(self):
        props = [make_propiedad() for _ in range(3)]
        session = make_db_session(propiedades=props)
        app.dependency_overrides[get_db] = override_db(session)

        with TestClient(app) as client:
            resp = client.get("/propiedades")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "total" in body
        assert "page" in body
        assert "pageSize" in body
        assert "totalPages" in body
        assert body["total"] == 3
        assert body["page"] == 1

    def test_precio_min_mayor_que_max_retorna_400(self):
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            resp = client.get("/propiedades?precioMin=500000&precioMax=200000")
        assert resp.status_code == 400
        assert "precioMin" in resp.json()["detail"]

    def test_filtro_estado_acepta_disponible(self):
        props = [make_propiedad(estado="disponible")]
        session = make_db_session(propiedades=props)
        app.dependency_overrides[get_db] = override_db(session)

        with TestClient(app) as client:
            resp = client.get("/propiedades?estado=disponible")

        app.dependency_overrides.clear()
        assert resp.status_code == 200

    def test_paginacion(self):
        props = [make_propiedad() for _ in range(2)]
        session = make_db_session(propiedades=props)
        app.dependency_overrides[get_db] = override_db(session)

        with TestClient(app) as client:
            resp = client.get("/propiedades?page=2&limit=10")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["page"] == 2


class TestObtenerPropiedad:
    def test_retorna_404_si_no_existe(self):
        session = make_db_session(propiedad=None)
        app.dependency_overrides[get_db] = override_db(session)

        with TestClient(app) as client:
            resp = client.get(f"/propiedades/{uuid.uuid4()}")

        app.dependency_overrides.clear()
        assert resp.status_code == 404

    def test_retorna_propiedad_existente(self):
        prop = make_propiedad()
        session = make_db_session(propiedad=prop)
        app.dependency_overrides[get_db] = override_db(session)

        with TestClient(app) as client:
            resp = client.get(f"/propiedades/{prop.id_propiedad}")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json()["titulo"] == prop.titulo

    def test_uuid_invalido_retorna_422(self):
        with TestClient(app) as client:
            resp = client.get("/propiedades/no-es-un-uuid")
        assert resp.status_code == 422


class TestCrearPropiedad:
    def test_body_invalido_retorna_422(self):
        with TestClient(app) as client:
            resp = client.post("/propiedades", json={"titulo": "X"})
        assert resp.status_code == 422

    def test_id_dueno_invalido_retorna_422(self):
        with TestClient(app) as client:
            resp = client.post("/propiedades", json={
                "titulo": "Casa válida para test",
                "descripcion": "Descripción válida con más de 10 caracteres.",
                "precio": "450000.00",
                "moneda": "CRC",
                "provincia": "San José",
                "canton": "Escazú",
                "distrito": "Escazú",
                "tipo": "casa",
                "idDueno": "no-es-uuid",
            })
        assert resp.status_code == 422
