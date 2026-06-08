"""
Cliente PostgreSQL minimalista (pure Python, sin librerías externas).
Compatible con Python 3.9+. Soporta SCRAM-SHA-256.
"""
import base64, hashlib, hmac, os, ssl, socket, struct, uuid
from datetime import datetime, timezone

HOST = "ms-propiedades-53383.postgres.database.azure.com"
PORT = 5432
DB   = "propiedades_db"
USER = "pgadmin"
PASS = "Arr3nd@Xpwu18Ml!"

# ── wire protocol helpers ──────────────────────────────────────────────────

def _pack_msg(tag, payload):
    if tag:
        return tag + struct.pack(">I", len(payload) + 4) + payload
    return struct.pack(">I", len(payload) + 4) + payload

def _read_msg(sock):
    tag = sock.recv(1)
    if not tag:
        raise EOFError("connection closed")
    length = struct.unpack(">I", _recv_exact(sock, 4))[0]
    body   = _recv_exact(sock, length - 4)
    return tag, body

def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("connection closed mid-message")
        buf += chunk
    return buf

def _cstring(s):
    return s.encode() + b"\x00"

# ── connect ────────────────────────────────────────────────────────────────

def pg_connect():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE

    raw = socket.create_connection((HOST, PORT), timeout=15)
    raw.sendall(struct.pack(">II", 8, 80877103))   # SSLRequest
    if raw.recv(1) != b"S":
        raise RuntimeError("Server denied SSL")

    sock = ctx.wrap_socket(raw, server_hostname=HOST)

    # StartupMessage
    payload = struct.pack(">I", 196608)  # protocol 3.0
    for k, v in [("user", USER), ("database", DB), ("application_name", "seed")]:
        payload += _cstring(k) + _cstring(v)
    payload += b"\x00"
    sock.sendall(struct.pack(">I", len(payload) + 4) + payload)

    # Auth loop
    scram_state = {}
    while True:
        tag, body = _read_msg(sock)
        if tag == b"R":
            auth_type = struct.unpack(">I", body[:4])[0]
            if auth_type == 0:
                break   # AuthenticationOk
            elif auth_type == 5:   # MD5
                salt = body[4:8]
                inner = hashlib.md5((PASS + USER).encode()).hexdigest()
                hashed = "md5" + hashlib.md5((inner + salt.decode("latin-1")).encode()).hexdigest()
                sock.sendall(_pack_msg(b"p", _cstring(hashed)))
            elif auth_type == 3:   # cleartext
                sock.sendall(_pack_msg(b"p", _cstring(PASS)))
            elif auth_type == 10:  # SASL – offer SCRAM-SHA-256
                # body[4:] is null-separated list of mechanisms ending with double null
                nonce = base64.b64encode(os.urandom(18)).decode()
                client_first_bare = f"n=*,r={nonce}"
                client_first = f"n,,{client_first_bare}"
                scram_state["nonce"] = nonce
                scram_state["client_first_bare"] = client_first_bare
                mech = b"SCRAM-SHA-256\x00"
                cf_bytes = client_first.encode()
                payload = mech + struct.pack(">I", len(cf_bytes)) + cf_bytes
                sock.sendall(_pack_msg(b"p", payload))
            elif auth_type == 11:  # SASLContinue
                server_first = body[4:].decode()
                parts = dict(p.split("=", 1) for p in server_first.split(","))
                server_nonce = parts["r"]
                salt_b64 = parts["s"]
                iters = int(parts["i"])
                if not server_nonce.startswith(scram_state["nonce"]):
                    raise RuntimeError("SCRAM: server nonce mismatch")
                salt = base64.b64decode(salt_b64)
                salted_pw = hashlib.pbkdf2_hmac("sha256", PASS.encode(), salt, iters)
                client_key = hmac.new(salted_pw, b"Client Key", "sha256").digest()
                stored_key = hashlib.sha256(client_key).digest()
                channel_binding = base64.b64encode(b"n,,").decode()
                client_final_no_proof = f"c={channel_binding},r={server_nonce}"
                auth_msg = (f"{scram_state['client_first_bare']},"
                            f"{server_first},{client_final_no_proof}").encode()
                client_sig = hmac.new(stored_key, auth_msg, "sha256").digest()
                client_proof = bytes(a ^ b for a, b in zip(client_key, client_sig))
                proof_b64 = base64.b64encode(client_proof).decode()
                client_final = f"{client_final_no_proof},p={proof_b64}"
                scram_state["server_key"] = hmac.new(salted_pw, b"Server Key", "sha256").digest()
                scram_state["auth_msg"] = auth_msg
                sock.sendall(_pack_msg(b"p", client_final.encode()))
            elif auth_type == 12:  # SASLFinal – verify server signature
                server_final = body[4:].decode()
                parts = dict(p.split("=", 1) for p in server_final.split(","))
                expected = base64.b64encode(
                    hmac.new(scram_state["server_key"], scram_state["auth_msg"], "sha256").digest()
                ).decode()
                if parts.get("v") != expected:
                    raise RuntimeError("SCRAM: server signature mismatch")
            else:
                raise RuntimeError(f"Unsupported auth type {auth_type}")
        elif tag == b"E":
            raise RuntimeError("Auth error: " + body.decode("utf-8", "replace"))

    # Drain startup messages (ParameterStatus, BackendKeyData, ReadyForQuery)
    while True:
        tag, _ = _read_msg(sock)
        if tag == b"Z":
            break

    return sock

# ── query helpers ──────────────────────────────────────────────────────────

def pg_query(sock, sql):
    """Simple Query (no parameters). Returns list of rows as dicts."""
    sock.sendall(_pack_msg(b"Q", _cstring(sql)))

    columns = []
    rows    = []
    while True:
        tag, body = _read_msg(sock)
        if tag == b"T":   # RowDescription
            count = struct.unpack(">H", body[:2])[0]
            pos   = 2
            for _ in range(count):
                end  = body.index(b"\x00", pos)
                name = body[pos:end].decode()
                pos  = end + 1 + 18   # skip type OIDs etc.
                columns.append(name)
        elif tag == b"D":  # DataRow
            count = struct.unpack(">H", body[:2])[0]
            pos   = 2
            row   = {}
            for col in columns:
                length = struct.unpack(">i", body[pos:pos+4])[0]
                pos   += 4
                if length == -1:
                    row[col] = None
                else:
                    row[col] = body[pos:pos+length].decode("utf-8", "replace")
                    pos += length
            rows.append(row)
        elif tag == b"C":   # CommandComplete
            pass
        elif tag == b"Z":   # ReadyForQuery
            break
        elif tag == b"E":   # ErrorResponse
            raise RuntimeError("Query error: " + body.decode("utf-8", "replace"))

    return rows

def pg_exec(sock, sql):
    """Execute a statement, return command tag."""
    sock.sendall(_pack_msg(b"Q", _cstring(sql)))
    tag_str = ""
    while True:
        tag, body = _read_msg(sock)
        if tag == b"C":
            tag_str = body.rstrip(b"\x00").decode()
        elif tag == b"Z":
            break
        elif tag == b"E":
            raise RuntimeError("Exec error: " + body.decode("utf-8", "replace"))
    return tag_str

# ── seed logic ─────────────────────────────────────────────────────────────

def escape_str(s):
    return s.replace("'", "''")

def main():
    print("Conectando a PostgreSQL en Azure...")
    sock = pg_connect()
    print("Conectado OK\n")

    # debug: verify connection
    dbname = pg_query(sock, "SELECT current_database() AS db, current_user AS usr")
    print("Connected to db:", dbname)

    # Try pg_catalog directly
    raw_tables = pg_query(sock,
        "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' ORDER BY tablename")
    print("pg_catalog tables:", raw_tables)

    # 1. Tablas
    tables = [r["tablename"] for r in raw_tables]
    print("=== Tablas ===")
    for t in tables:
        print(f"  {t}")

    # 2. Usuarios o dueños
    if "usuarios" in tables:  # noqa: SIM108
        users = pg_query(sock, "SELECT * FROM usuarios ORDER BY id")
        print("\n=== Todos los usuarios ===")
        for u in users:
            print(u)
        duenos = [u["id"] for u in users if u.get("rol") == "dueno"]
        print(f"\n=== Dueños ({len(duenos)}) ===")
        for d in duenos:
            print(f"  {d}")
    else:
        print("\n[INFO] No hay tabla 'usuarios'. Usando id_dueno de propiedades.")
        rows = pg_query(sock,
            "SELECT id_dueno, COUNT(*) AS total FROM propiedades "
            "GROUP BY id_dueno ORDER BY id_dueno")
        print("\n=== Dueños registrados ===")
        for r in rows:
            print(f"  id_dueno={r['id_dueno']}  propiedades={r['total']}")
        duenos = [r["id_dueno"] for r in rows]

    if not duenos:
        print("No se encontraron dueños.")
        sock.close()
        return

    # 3. Insertar una propiedad por dueño
    print(f"\n=== Insertando 1 propiedad para cada uno de los {len(duenos)} dueños ===")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
    for did in duenos:
        nid = str(uuid.uuid4())
        amenidades_pg = "ARRAY['parqueo','agua']"
        sql = f"""
INSERT INTO propiedades (
    id_propiedad,titulo,descripcion,precio,moneda,
    provincia,canton,distrito,tipo,estado,
    imagenes,id_dueno,amenidades,fecha_creacion
) VALUES (
    '{nid}',
    'Propiedad de prueba – asignada automáticamente',
    'Propiedad de muestra creada por script de seed para verificar el flujo de dueño.',
    350000.00, 'CRC',
    'San José','San José','Carmen',
    'apartamento','disponible',
    ARRAY[]::text[], '{escape_str(did)}',
    {amenidades_pg},
    '{now}'
)"""
        pg_exec(sock, sql)
        print(f"  ✓ dueño={did}  id_propiedad={nid}")

    # 4. Verificación
    total = pg_query(sock, "SELECT COUNT(*) AS total FROM propiedades")[0]["total"]
    print(f"\nTotal propiedades en DB: {total}")
    sock.close()

main()
