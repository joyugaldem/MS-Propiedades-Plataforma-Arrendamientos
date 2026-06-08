"""
Reasigna propiedades cuyos id_dueno son inquilinos (usr-086, usr-087)
a dueños válidos (usr-083, usr-084, usr-085).

usr-086 → usr-083 (maria.rodriguez)
usr-087 → usr-084 (carlos.mendez)
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

import asyncpg

DUENOS_REALES = ["usr-083", "usr-084", "usr-085"]

async def main():
    raw_url = os.getenv("DATABASE_URL", "")
    url = raw_url.replace("postgresql+asyncpg://", "postgresql://").replace("?ssl=require", "")

    conn = await asyncpg.connect(url, ssl="require")

    total = await conn.fetchval("SELECT COUNT(*) FROM propiedades")
    print(f"Total de propiedades en BD: {total}")

    # Distribuir equitativamente entre los 3 dueños reales usando ROW_NUMBER
    result = await conn.execute("""
        WITH numeradas AS (
            SELECT id_propiedad,
                   ROW_NUMBER() OVER (ORDER BY fecha_creacion) AS rn
            FROM propiedades
        )
        UPDATE propiedades
        SET id_dueno = CASE ((numeradas.rn - 1) % 3)
            WHEN 0 THEN 'usr-083'
            WHEN 1 THEN 'usr-084'
            ELSE       'usr-085'
        END
        FROM numeradas
        WHERE propiedades.id_propiedad = numeradas.id_propiedad
    """)

    actualizadas = int(result.split()[-1])
    print(f"Propiedades actualizadas: {actualizadas}")

    # Verificar distribución final
    print("\nDistribución final:")
    dist = await conn.fetch(
        "SELECT id_dueno, COUNT(*) AS total FROM propiedades "
        "WHERE id_dueno = ANY($1) GROUP BY id_dueno ORDER BY id_dueno",
        DUENOS_REALES,
    )
    for r in dist:
        nombres = {"usr-083": "maria.rodriguez", "usr-084": "carlos.mendez", "usr-085": "ana.perez"}
        nombre = nombres.get(r["id_dueno"], r["id_dueno"])
        print(f"  {r['id_dueno']} ({nombre}): {r['total']} propiedades")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
