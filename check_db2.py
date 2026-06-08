import psycopg2
import json

conn = psycopg2.connect(
    host="pgprop-53383.postgres.database.azure.com",
    port=5432,
    dbname="propiedades_db",
    user="pgadmin",
    password="Arr3nd@Xpwu18Ml!",
    sslmode="require"
)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM propiedades;")
total = cur.fetchone()[0]
print(f"Total propiedades: {total}")

cur.execute("""
    SELECT id_propiedad, titulo, provincia, tipo, estado, precio::text, moneda, id_dueno
    FROM propiedades
    ORDER BY fecha_creacion DESC
    LIMIT 20;
""")
rows = cur.fetchall()
cols = [d[0] for d in cur.description]
for row in rows:
    print(dict(zip(cols, row)))

cur.close()
conn.close()
