import asyncio
import asyncpg

# Fix para Python 3.14 en Windows — el ProactorEventLoop falla con SSL
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    conn = await asyncpg.connect(
        host="pgprop-53383.postgres.database.azure.com",
        port=5432,
        database="propiedades_db",
        user="pgadmin",
        password="Arr3nd@Xpwu18Ml!",
        ssl="require"
    )
    count = await conn.fetchval("SELECT COUNT(*) FROM propiedades")
    rows = await conn.fetch(
        "SELECT id_propiedad, titulo, provincia, tipo, estado, precio, moneda, id_dueno "
        "FROM propiedades ORDER BY fecha_creacion DESC LIMIT 20"
    )
    await conn.close()
    print(f"Total propiedades: {count}")
    for r in rows:
        print(dict(r))

asyncio.run(main())
