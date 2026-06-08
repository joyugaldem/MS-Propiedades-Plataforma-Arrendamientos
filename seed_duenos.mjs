import pg from 'pg';
import { randomUUID } from 'crypto';
const { Client } = pg;

const client = new Client({
  host: 'pgprop-53383.postgres.database.azure.com',
  port: 5432,
  database: 'propiedades_db',
  user: 'pgadmin',
  password: 'Arr3nd@Xpwu18Ml!',
  ssl: { rejectUnauthorized: false },
});

const PROP = {
  titulo: 'Propiedad de prueba – asignada automáticamente',
  descripcion: 'Propiedad de muestra creada por script de seed para verificar el flujo de dueño.',
  precio: '350000.00',
  moneda: 'CRC',
  provincia: 'San José',
  canton: 'San José',
  distrito: 'Carmen',
  tipo: 'apartamento',
  estado: 'disponible',
  imagenes: [],
  amenidades: ['parqueo', 'agua'],
};

await client.connect();

// ── 1. Tablas disponibles ──────────────────────────────────────────────────
const tablesRes = await client.query(
  "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name"
);
const tables = tablesRes.rows.map(r => r.table_name);
console.log('=== Tablas en propiedades_db ===');
tables.forEach(t => console.log(`  • ${t}`));

// ── 2. Usuarios o dueños ───────────────────────────────────────────────────
let duenos = [];
if (tables.includes('usuarios')) {
  const usersRes = await client.query('SELECT * FROM usuarios ORDER BY id');
  console.log('\n=== Todos los usuarios ===');
  usersRes.rows.forEach(u => console.log(u));
  duenos = usersRes.rows.filter(u => u.rol === 'dueno').map(u => String(u.id));
  console.log(`\n=== Usuarios con rol 'dueno' (${duenos.length}) ===`);
  duenos.forEach(d => console.log(`  ${d}`));
} else {
  console.log('\n[INFO] No existe tabla "usuarios". Usando id_dueno de propiedades.');
  const dRes = await client.query(
    'SELECT id_dueno, COUNT(*) AS total_props FROM propiedades GROUP BY id_dueno ORDER BY id_dueno'
  );
  console.log('\n=== Dueños registrados en propiedades ===');
  dRes.rows.forEach(r => console.log(`  id_dueno=${r.id_dueno}  propiedades=${r.total_props}`));
  duenos = dRes.rows.map(r => r.id_dueno);
}

if (!duenos.length) {
  console.log('\n[WARN] No se encontraron dueños. Abortando.');
  await client.end();
  process.exit(0);
}

// ── 3. Insertar una propiedad por cada dueño ──────────────────────────────
console.log(`\n=== Insertando 1 propiedad para cada uno de los ${duenos.length} dueños ===`);
const now = new Date().toISOString();
for (const dueno_id of duenos) {
  const newId = randomUUID();
  await client.query(
    `INSERT INTO propiedades (
       id_propiedad, titulo, descripcion, precio, moneda,
       provincia, canton, distrito, tipo, estado,
       imagenes, id_dueno, amenidades, fecha_creacion
     ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)`,
    [
      newId, PROP.titulo, PROP.descripcion, PROP.precio, PROP.moneda,
      PROP.provincia, PROP.canton, PROP.distrito, PROP.tipo, PROP.estado,
      PROP.imagenes, dueno_id, PROP.amenidades, now,
    ]
  );
  console.log(`  ✓ dueño=${dueno_id}  nueva propiedad=${newId}`);
}

// ── 4. Verificación final ─────────────────────────────────────────────────
const total = (await client.query('SELECT COUNT(*) AS total FROM propiedades')).rows[0].total;
console.log(`\nTotal propiedades en DB después del seed: ${total}`);
await client.end();
