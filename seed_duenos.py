"""
Script: listar usuarios/dueños en la DB y asignarles una propiedad de prueba.
Paso 1 – muestra qué tablas existen y los dueños distintos en propiedades.
Paso 2 – inserta una propiedad por cada dueño.
"""

import ssl
import uuid
from datetime import datetime, timezone

import pg8000.native

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE
ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_2

DSN = dict(
    host="pgprop-53383.postgres.database.azure.com",
    port=5432,
    database="propiedades_db",
    user="pgadmin",
    password="Arr3nd@Xpwu18Ml!",
    ssl_context=ssl_ctx,
)

PROP_TEMPLATE = dict(
    titulo="Propiedad de prueba – asignada automáticamente",
    descripcion="Propiedad de muestra creada por script de seed para verificar el flujo de dueño.",
    precio="350000.00",
    moneda="CRC",
    provincia="San José",
    canton="San José",
    distrito="Carmen",
    tipo="apartamento",
    estado="disponible",
    imagenes=[],
    amenidades=["parqueo", "agua"],
)


def cols_to_dict(columns, rows):
    return [dict(zip(columns, row)) for row in rows]


def main():
    conn = pg8000.native.Connection(**DSN)

    # ── 1. Tablas disponibles ────────────────────────────────────────────────
    rows = conn.run(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' ORDER BY table_name"
    )
    tables = [r[0] for r in rows]
    print("=== Tablas en propiedades_db ===")
    for t in tables:
        print(f"  • {t}")

    # ── 2. ¿Existe tabla de usuarios? ────────────────────────────────────────
    if "usuarios" in tables:
        rows = conn.run("SELECT * FROM usuarios ORDER BY id")
        cols = [c["name"] for c in conn.columns]
        users = cols_to_dict(cols, rows)
        print("\n=== Todos los usuarios ===")
        for u in users:
            print(u)
        duenos = [str(u["id"]) for u in users if u.get("rol") == "dueno"]
        print(f"\n=== Usuarios con rol 'dueno' ({len(duenos)}) ===")
        for d in duenos:
            print(f"  {d}")
    else:
        print("\n[INFO] No existe tabla 'usuarios'. Usando id_dueno distintos de propiedades.")
        rows = conn.run(
            "SELECT id_dueno, COUNT(*) AS total_props "
            "FROM propiedades GROUP BY id_dueno ORDER BY id_dueno"
        )
        cols = [c["name"] for c in conn.columns]
        data = cols_to_dict(cols, rows)
        print("\n=== Dueños registrados en propiedades ===")
        for r in data:
            print(f"  id_dueno={r['id_dueno']}  propiedades={r['total_props']}")
        duenos = [r["id_dueno"] for r in data]

    if not duenos:
        print("\n[WARN] No se encontraron dueños. Abortando.")
        conn.close()
        return

    # ── 3. Insertar una propiedad por cada dueño ─────────────────────────────
    print(f"\n=== Insertando 1 propiedad para cada uno de los {len(duenos)} dueños ===")
    now = datetime.now(timezone.utc)
    for dueno_id in duenos:
        new_id = str(uuid.uuid4())
        conn.run(
            """
            INSERT INTO propiedades (
                id_propiedad, titulo, descripcion, precio, moneda,
                provincia, canton, distrito, tipo, estado,
                imagenes, id_dueno, amenidades, fecha_creacion
            ) VALUES (
                :id_propiedad, :titulo, :descripcion, :precio, :moneda,
                :provincia, :canton, :distrito, :tipo, :estado,
                :imagenes, :id_dueno, :amenidades, :fecha_creacion
            )
            """,
            id_propiedad=new_id,
            titulo=PROP_TEMPLATE["titulo"],
            descripcion=PROP_TEMPLATE["descripcion"],
            precio=PROP_TEMPLATE["precio"],
            moneda=PROP_TEMPLATE["moneda"],
            provincia=PROP_TEMPLATE["provincia"],
            canton=PROP_TEMPLATE["canton"],
            distrito=PROP_TEMPLATE["distrito"],
            tipo=PROP_TEMPLATE["tipo"],
            estado=PROP_TEMPLATE["estado"],
            imagenes=PROP_TEMPLATE["imagenes"],
            id_dueno=dueno_id,
            amenidades=PROP_TEMPLATE["amenidades"],
            fecha_creacion=now,
        )
        print(f"  ✓ dueño={dueno_id}  nueva propiedad={new_id}")

    # ── 4. Verificación final ─────────────────────────────────────────────────
    total = conn.run("SELECT COUNT(*) FROM propiedades")[0][0]
    print(f"\nTotal propiedades en DB después del seed: {total}")
    conn.close()


main()
