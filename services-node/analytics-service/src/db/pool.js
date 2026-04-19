const { Pool } = require('pg');
const path = require('path');
const dotenv = require('dotenv');

function getAppEnv() {
  return (process.env.ENV || process.env.NODE_ENV || 'local').toLowerCase();
}

function getDatabaseUrl() {
  const env = getAppEnv();
  const isProd = env === 'prod' || env === 'production';

  if (!process.env.SUPABASE_DB_URL && !process.env.DATABASE_URL) {
    const envFile = isProd ? '.env.production' : '.env.local';
    const envPath = path.resolve(__dirname, '../../', envFile);
    dotenv.config({ path: envPath });
  }

  const databaseUrl = isProd
    ? (process.env.SUPABASE_DB_URL || process.env.DATABASE_URL)
    : process.env.DATABASE_URL;

  if (!databaseUrl) {
    throw new Error(
      isProd
        ? 'Missing SUPABASE_DB_URL (or DATABASE_URL fallback) for production env'
        : 'Missing DATABASE_URL for local env'
    );
  }

  return { databaseUrl, env, isProd };
}

function normalizeDbUrl(rawUrl) {
  try {
    new URL(rawUrl);
    return rawUrl;
  } catch {
    const match = rawUrl.match(/^(postgres(?:ql)?:\/\/[^:]+:)([^@]+)(@.+)$/i);
    if (!match) {
      throw new Error('Invalid URL');
    }
    const prefix = match[1];
    const rawPassword = match[2];
    const suffix = match[3];
    const encodedPassword = encodeURIComponent(rawPassword);
    const repaired = `${prefix}${encodedPassword}${suffix}`;
    new URL(repaired);
    return repaired;
  }
}

function maskDbUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    const user = parsed.username || 'user';
    return `${parsed.protocol}//${user}:***@${parsed.host}${parsed.pathname}`;
  } catch {
    return '<invalid-db-url>';
  }
}

const { databaseUrl, env, isProd } = getDatabaseUrl();
const normalizedDbUrl = normalizeDbUrl(databaseUrl);

const pool = new Pool({
  connectionString: normalizedDbUrl,
  ssl: false,
});

async function verifyDbConnection() {
  const client = await pool.connect();
  try {
    const result = await client.query('SELECT current_database() AS db, now() AS ts');
    const row = result.rows[0] || {};
    console.log(`[db] env=${env} connected db=${row.db || 'unknown'} at=${row.ts || 'unknown'}`);
    console.log(`[db] url=${maskDbUrl(normalizedDbUrl)}`);
  } catch (error) {
    console.error(`[db] Failed to connect:`, error.message);
  } finally {
    client.release();
  }
}

module.exports = {
  pool,
  verifyDbConnection,
  getDatabaseUrl,
};