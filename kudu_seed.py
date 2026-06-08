import asyncio, uuid, ssl
from datetime import datetime, timezone

import asyncpg

async def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        host="pgprop-53383.postgres.database.azure.com",
        port=5432,
        database="propiedades_db",
        user="pgadmin",
        password="Arr3nd@Xpwu18Ml!",
        ssl=ctx,
    )

    tables = await conn.fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name"
    )
    table_names = [r['table_name'] for r in tables]
    print("=== Tablas ===")
    for t in table_names:
        print(f"  {t}")

    if 'usuarios' in table_names:
        users = await conn.fetch("SELECT * FROM usuarios ORDER BY id")
        print("\n=== Todos los usuarios ===")
        for u in users:
            print(dict(u))
        duenos = [str(u['id']) for u in users if u.get('rol') == 'dueno']
        print(f"\n=== Dueños ({len(duenos)}) ===")
        for d in duenos: print(f"  {d}")
    else:
        rows = await conn.fetch(
            "SELECT id_dueno, COUNT(*) AS total FROM propiedades "
            "GROUP BY id_dueno ORDER BY id_dueno"
        )
        print("\n=== Dueños en propiedades ===")
        for r in rows:
            print(f"  id_dueno={r['id_dueno']}  props={r['total']}")
        duenos = [r['id_dueno'] for r in rows]

    if not duenos:
        print("No se encontraron dueños.")
        await conn.close()
        return

    print(f"\n=== Insertando propiedad a {len(duenos)} dueños ===")
    now = datetime.now(timezone.utc)
    for did in duenos:
        nid = uuid.uuid4()
        await conn.execute("""
            INSERT INTO propiedades (
                id_propiedad,titulo,descripcion,precio,moneda,
                provincia,canton,distrito,tipo,estado,
                imagenes,id_dueno,amenidades,fecha_creacion
            ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        """,
            nid,
            "Propiedad de prueba – asignada automáticamente",
            "Propiedad de muestra creada por script de seed para verificar el flujo de dueño.",
            "350000.00",
            "CRC",
            "San José","San José","Carmen",
            "apartamento","disponible",
            [],"{}".format(did),["parqueo","agua"],
            now,
        )
        print(f"  ✓ dueño={did}  id_propiedad={nid}")

    total = await conn.fetchval("SELECT COUNT(*) FROM propiedades")
    print(f"\nTotal propiedades en DB: {total}")
    await conn.close()

asyncio.run(main())
