import pg8000.native

conn = pg8000.native.Connection(
    host="pgprop-53383.postgres.database.azure.com",
    port=5432,
    database="propiedades_db",
    user="pgadmin",
    password="Arr3nd@Xpwu18Ml!",
    ssl_context=True,
)

total_antes = conn.run("SELECT COUNT(*) FROM propiedades")[0][0]
print(f"Total antes: {total_antes}")

dist_antes = conn.run("SELECT id_dueno, COUNT(*) FROM propiedades GROUP BY id_dueno ORDER BY id_dueno")
print("Distribución antes:")
for row in dist_antes:
    print(f"  {row[0]}: {row[1]}")

conn.run("UPDATE propiedades SET id_dueno = 'usr-083'")
print("\nUPDATE ejecutado.")

dist_despues = conn.run("SELECT id_dueno, COUNT(*) FROM propiedades GROUP BY id_dueno ORDER BY id_dueno")
print("Distribución después:")
for row in dist_despues:
    print(f"  {row[0]}: {row[1]}")

conn.close()
