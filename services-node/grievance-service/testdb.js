const path = require('path');
const dotenv = require('dotenv');

function getArgEnv() {
  const arg = process.argv.find((item) => item.startsWith('--env='));
  if (!arg) return null;
  return arg.split('=')[1] || null;
}

const argEnv = getArgEnv();
if (argEnv) {
  process.env.ENV = argEnv;
}

const runtimeEnv = (process.env.ENV || process.env.NODE_ENV || 'local').toLowerCase();
const envFile = (runtimeEnv === 'prod' || runtimeEnv === 'production')
  ? '.env.production'
  : '.env.local';

dotenv.config({ path: path.join(__dirname, envFile) });
console.log(`[testdb] Loaded env file: ${envFile}`);

const { pool, getDatabaseUrl } = require('./src/db/pool');

async function testConnection() {
  const { env, isProd } = getDatabaseUrl();
  console.log('Testing grievance-service DB connection');
  console.log(`  ENV  : ${env}`);
  console.log(`  Mode : ${isProd ? 'prod (SUPABASE_DB_URL)' : 'local (DATABASE_URL)'}`);

  try {
    const versionResult = await pool.query('SELECT version() AS version');
    const dbResult = await pool.query('SELECT current_database() AS db');

    const version = (versionResult.rows[0] && versionResult.rows[0].version) || 'unknown';
    const db = (dbResult.rows[0] && dbResult.rows[0].db) || 'unknown';

    console.log(`Connected. database=${db}`);
    console.log(`PostgreSQL: ${version.substring(0, 80)}`);

    const schemaResult = await pool.query(`
      SELECT table_schema, table_name
      FROM information_schema.tables
      WHERE table_schema = 'grievance_svc'
      ORDER BY table_name
    `);

    if (schemaResult.rows.length > 0) {
      console.log(`Found ${schemaResult.rows.length} grievance_svc tables:`);
      for (const row of schemaResult.rows) {
        console.log(`  ${row.table_schema}.${row.table_name}`);
      }
    } else {
      console.log('No grievance_svc tables found. Run schema.sql on this DB.');
    }
  } catch (error) {
    console.error(`Connection failed: ${error.message}`);
    process.exitCode = 1;
  } finally {
    await pool.end();
  }
}

testConnection();
