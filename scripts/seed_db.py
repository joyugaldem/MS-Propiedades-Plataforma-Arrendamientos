"""
Seed script: inserta 100 propiedades de prueba en propiedades_db.

Uso local (requiere .env con DATABASE_URL):
    python scripts/seed_db.py

Uso apuntando a Azure directo:
    DATABASE_URL="postgresql+asyncpg://..." python scripts/seed_db.py
"""

import argparse
import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Permite importar app.* desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.propiedad import Propiedad

# ---------------------------------------------------------------------------
# Datos de referencia — Costa Rica
# ---------------------------------------------------------------------------

UBICACIONES = [
    ("San José",    "San José",          "Carmen"),
    ("San José",    "San José",          "Merced"),
    ("San José",    "Escazú",            "Escazú"),
    ("San José",    "Escazú",            "San Rafael"),
    ("San José",    "Desamparados",      "Desamparados"),
    ("San José",    "Santa Ana",         "Santa Ana"),
    ("San José",    "Montes de Oca",     "San Pedro"),
    ("San José",    "Moravia",           "San Vicente"),
    ("San José",    "Tibás",             "San Juan"),
    ("San José",    "Curridabat",        "Curridabat"),
    ("Alajuela",    "Alajuela",          "Alajuela"),
    ("Alajuela",    "Alajuela",          "San José"),
    ("Alajuela",    "San Ramón",         "San Ramón"),
    ("Alajuela",    "Grecia",            "Grecia"),
    ("Alajuela",    "Atenas",            "Atenas"),
    ("Alajuela",    "La Garita",         "La Garita"),
    ("Cartago",     "Cartago",           "Oriental"),
    ("Cartago",     "Cartago",           "Occidental"),
    ("Cartago",     "La Unión",          "Tres Ríos"),
    ("Cartago",     "El Guarco",         "El Tejar"),
    ("Heredia",     "Heredia",           "Heredia"),
    ("Heredia",     "Heredia",           "Mercedes"),
    ("Heredia",     "San Pablo",         "San Pablo"),
    ("Heredia",     "Barva",             "Barva"),
    ("Heredia",     "Santa Bárbara",     "Santa Bárbara"),
    ("Guanacaste",  "Liberia",           "Liberia"),
    ("Guanacaste",  "Nicoya",            "Nicoya"),
    ("Guanacaste",  "Tamarindo",         "Villarreal"),
    ("Guanacaste",  "Playas del Coco",   "Sardinal"),
    ("Puntarenas",  "Puntarenas",        "Puntarenas"),
    ("Puntarenas",  "Quepos",            "Quepos"),
    ("Puntarenas",  "Jacó",              "Tárcoles"),
    ("Limón",       "Limón",             "Limón"),
    ("Limón",       "Pococí",            "Guápiles"),
]

TIPOS = ["casa", "apartamento", "local", "bodega", "oficina"]
ESTADOS = ["disponible"] * 7 + ["alquilada"] * 25 + ["mantenimiento"] * 5 + ["disponible"] * 63
MONEDAS = ["CRC", "CRC", "CRC", "USD", "USD", "USD", "CRC", "USD", "CRC", "CRC"]

RANGOS_PRECIO = {
    # (crc_min, crc_max, usd_min, usd_max)
    "apartamento": (300_000,  600_000,  500,  1_200),
    "casa":        (400_000,  900_000,  800,  2_500),
    "local":       (500_000, 1_500_000, 1_000, 4_000),
    "oficina":     (400_000, 1_200_000,  800,  3_000),
    "bodega":      (300_000,  800_000,  600,  2_000),
}

TITULOS = {
    "apartamento": [
        "Apartamento moderno en {canton}",
        "Apto amueblado con vista en {canton}",
        "Apartamento céntrico en {distrito}",
        "Apartamento ejecutivo en {canton}",
        "Apto nuevo con parqueo en {distrito}",
    ],
    "casa": [
        "Casa familiar en {canton}",
        "Casa con jardín en {distrito}",
        "Casa de dos plantas en {canton}",
        "Casa independiente en {distrito}",
        "Casa amplia con cochera en {canton}",
    ],
    "local": [
        "Local comercial en zona céntrica de {canton}",
        "Local para negocio en {distrito}",
        "Espacio comercial en {canton}",
        "Local en plaza comercial, {canton}",
        "Local amplio con vitrina en {distrito}",
    ],
    "bodega": [
        "Bodega industrial en {canton}",
        "Bodega con acceso de camión en {distrito}",
        "Bodega para almacenaje en {canton}",
        "Bodega mediana en zona industrial de {canton}",
        "Bodega con rampa de carga en {distrito}",
    ],
    "oficina": [
        "Oficina corporativa en {canton}",
        "Oficina privada en edificio de {distrito}",
        "Espacio de oficina en {canton}",
        "Oficina ejecutiva con sala de reuniones en {canton}",
        "Oficina en piso alto, {distrito}",
    ],
}

DESCRIPCIONES = {
    "apartamento": [
        "Hermoso apartamento con acabados de primera calidad. Cuenta con sala-comedor espacioso, cocina integral, dos habitaciones con closets y baño completo. Excelente ubicación con fácil acceso al centro y transporte público.",
        "Apartamento totalmente amueblado y equipado, ideal para ejecutivos o profesionales. Incluye internet fibra óptica, agua caliente, lavadora y secadora. Edificio seguro con guarda las 24 horas.",
        "Moderno apartamento en condominio cerrado con amenidades de primer nivel. Vista despejada, ventilación natural y mucha luz. A pasos de supermercados, farmacias y restaurantes.",
        "Acogedor apartamento con diseño contemporáneo. Pisos de cerámica, ventanas amplias y balcón privado. Condominio con piscina, gimnasio y área BBQ de uso exclusivo para residentes.",
    ],
    "casa": [
        "Espaciosa casa en residencial tranquilo y seguro. Cuenta con 3 habitaciones, 2 baños, sala-comedor, cocina amplia y jardín privado. Cochera para dos vehículos. Ideal para familia.",
        "Casa de dos plantas en excelente estado. Planta baja: sala, comedor, cocina y servicios. Planta alta: 3 habitaciones con baño compartido y cuarto de servicio. Jardín y cochera techada.",
        "Hermosa casa con acabados finos en residencial con vigilancia. Área construida de 180 m², 4 habitaciones, 3 baños, sala de entretenimiento y terraza. Cerca de colegios y centros comerciales.",
        "Casa independiente en zona residencial consolidada. 3 habitaciones, sala, comedor, cocina y patio trasero. Acceso conveniente a servicios públicos y autopista principal.",
    ],
    "local": [
        "Excelente local comercial sobre calle principal con alto flujo peatonal y vehicular. Espacio abierto, fácil de adaptar para cualquier tipo de negocio. Servicio eléctrico trifásico disponible.",
        "Local en centro comercial con gran afluencia de público. Cuenta con vitrina al pasillo principal, baño propio y depósito. Incluye estacionamiento para clientes.",
        "Amplio local en zona comercial consolidada. Planta libre sin columnas, aire acondicionado, puertas de seguridad tipo shutter. Ideal para tienda, restaurante u oficina.",
        "Local en esquina con doble acceso vehicular y peatonal. Visibilidad excelente desde la calle. Instalaciones de agua, luz y teléfono. Parqueo propio para 5 vehículos.",
    ],
    "bodega": [
        "Bodega industrial con altura libre de 6 metros, piso de concreto reforzado y amplio portón para acceso de camiones de carga. Sistema eléctrico trifásico. Área de oficinas incluida.",
        "Bodega en parque industrial con vigilancia 24/7. Rampa de descarga, iluminación industrial y ventilación natural. Fácil acceso desde la autopista. Disponibilidad inmediata.",
        "Bodega mediana ideal para distribución o manufactura ligera. Portón eléctrico, servicio de agua y alcantarillado, área de maniobras para camiones. Oficina administrativa en segundo nivel.",
        "Espacio de almacenamiento con fácil acceso vehicular. Piso nivelado, techos de zinc termo-acústico, iluminación artificial completa y sistema contra incendios.",
    ],
    "oficina": [
        "Oficina moderna en edificio corporativo de categoría A. Acabados de primera, aire acondicionado central, sistema de seguridad biométrico y fibra óptica. Parqueo incluido.",
        "Espacio de oficina en planta abierta con opción de dividirse en cubículos. Ventanas al exterior, sala de reuniones compartida, recepción y cafetería en el edificio.",
        "Oficina privada con excelente vista en edificio inteligente. Incluye generador de emergencia, UPS central y conexión a fibra óptica de alta velocidad. Muy bien comunicada.",
        "Moderno espacio de trabajo en edificio de oficinas con amenidades premium. Sala de conferencias, área de descanso, cafetería y estacionamiento techado para empleados.",
    ],
}

AMENIDADES_POOL = [
    ["parqueo", "seguridad 24h", "internet fibra óptica"],
    ["parqueo", "agua caliente", "lavadora"],
    ["piscina", "gimnasio", "parqueo", "seguridad 24h"],
    ["aire acondicionado", "parqueo", "internet"],
    ["seguridad 24h", "CCTV", "generador"],
    ["piscina", "área BBQ", "jardín", "parqueo"],
    ["gimnasio", "sala de reuniones", "parqueo", "seguridad"],
    ["agua caliente", "lavandería", "ascensor", "parqueo"],
    ["parqueo para visitas", "cuarto de servicio", "bodega"],
    [],
]

DUENOS = [
    "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "d4e5f6a7-b8c9-0123-defa-234567890123",
    "e5f6a7b8-c9d0-1234-efab-345678901234",
]

IMAGENES_BASE = [
    "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
    "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800",
    "https://images.unsplash.com/photo-1484154218962-a197022b5858?w=800",
    "https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=800",
    "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800",
    "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800",
    "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800",
    "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800",
    "https://images.unsplash.com/photo-1565183997392-2f6f122e5912?w=800",
]


def precio_aleatorio(tipo: str, moneda: str) -> float:
    crc_min, crc_max, usd_min, usd_max = RANGOS_PRECIO[tipo]
    if moneda == "CRC":
        return round(random.randint(crc_min // 1000, crc_max // 1000) * 1000, 2)
    return round(random.uniform(usd_min, usd_max), 2)


def generar_propiedad(i: int) -> Propiedad:
    ubicacion = random.choice(UBICACIONES)
    provincia, canton, distrito = ubicacion
    tipo = random.choices(TIPOS, weights=[30, 35, 15, 10, 10])[0]
    moneda = random.choice(MONEDAS)
    estado = random.choice(ESTADOS)

    titulo_tpl = random.choice(TITULOS[tipo])
    titulo = titulo_tpl.format(canton=canton, distrito=distrito)

    descripcion = random.choice(DESCRIPCIONES[tipo])

    imagenes = random.sample(IMAGENES_BASE, k=random.randint(1, 4))

    amenidades = random.choice(AMENIDADES_POOL)

    dias_atras = random.randint(0, 365)
    fecha = datetime.now(timezone.utc) - timedelta(days=dias_atras)

    return Propiedad(
        id_propiedad=uuid.uuid4(),
        titulo=titulo,
        descripcion=descripcion,
        precio=precio_aleatorio(tipo, moneda),
        moneda=moneda,
        provincia=provincia,
        canton=canton,
        distrito=distrito,
        tipo=tipo,
        estado=estado,
        imagenes=imagenes,
        id_dueno=random.choice(DUENOS),
        amenidades=list(amenidades),
        fecha_creacion=fecha,
    )


async def seed(n: int = 100, clean: bool = False):
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as session:
        if clean:
            await session.execute(delete(Propiedad))
            await session.commit()
            print("Tabla limpiada.")

    propiedades = [generar_propiedad(i) for i in range(n)]

    async with Session() as session:
        session.add_all(propiedades)
        await session.commit()

    await engine.dispose()

    conteo = {}
    for p in propiedades:
        conteo[p.tipo] = conteo.get(p.tipo, 0) + 1

    print(f"\n✓ {n} propiedades insertadas correctamente\n")
    print("Distribución por tipo:")
    for tipo, cnt in sorted(conteo.items()):
        print(f"  {tipo:<12} {cnt}")

    estados = {}
    for p in propiedades:
        estados[p.estado] = estados.get(p.estado, 0) + 1
    print("\nDistribución por estado:")
    for estado, cnt in sorted(estados.items()):
        print(f"  {estado:<15} {cnt}")

    monedas_cnt = {}
    for p in propiedades:
        monedas_cnt[p.moneda] = monedas_cnt.get(p.moneda, 0) + 1
    print("\nDistribución por moneda:")
    for moneda, cnt in sorted(monedas_cnt.items()):
        print(f"  {moneda}  {cnt}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed de propiedades de prueba")
    parser.add_argument("--n", type=int, default=100, help="Número de propiedades a insertar")
    parser.add_argument("--clean", action="store_true", help="Borrar datos existentes antes de insertar")
    args = parser.parse_args()
    try:
        asyncio.run(seed(n=args.n, clean=args.clean))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
