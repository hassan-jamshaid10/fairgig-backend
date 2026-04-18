const path = require('path');
const dotenv = require('dotenv');

const runtimeEnv = (process.env.ENV || process.env.NODE_ENV || 'local').toLowerCase();
const envFile = (runtimeEnv === 'prod' || runtimeEnv === 'production')
  ? '.env.production'
  : '.env.local';

dotenv.config({ path: path.join(__dirname, envFile) });
console.log(`[startup] Loaded env file: ${envFile}`);

const app = require('./src/app');
const { verifyDbConnection, getDatabaseUrl } = require('./src/db/pool');

const PORT = process.env.PORT || 8004;

async function start() {
  try {
    const { env, isProd } = getDatabaseUrl();
    console.log(`[startup] env=${env} mode=${isProd ? 'prod' : 'local'}`);

    await verifyDbConnection();

    app.listen(PORT, () => {
      console.log(`Grievance Service is running on port ${PORT}`);
    });
  } catch (error) {
    console.error('[startup] Failed to initialize DB connection:', error.message);
    process.exit(1);
  }
}

start();