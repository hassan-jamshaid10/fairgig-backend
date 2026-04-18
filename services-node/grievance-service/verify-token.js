const path = require('path');
const dotenv = require('dotenv');
const jwt = require('jsonwebtoken');

function getArg(name, fallback = null) {
  const arg = process.argv.find((item) => item.startsWith(`--${name}=`));
  return arg ? arg.split('=')[1] : fallback;
}

const env = (getArg('env', process.env.ENV || process.env.NODE_ENV || 'local') || 'local').toLowerCase();
const token = getArg('token');

if (!token) {
  console.error('Missing --token=<jwt>');
  process.exit(1);
}

const envFile = env === 'prod' || env === 'production' ? '.env.production' : '.env.local';
dotenv.config({ path: path.join(__dirname, envFile) });

const secret = (process.env.SECRET_KEY || process.env.JWT_SECRET || '').trim();
if (!secret) {
  console.error(`Missing SECRET_KEY in ${envFile}`);
  process.exit(1);
}

try {
  const payload = jwt.verify(token, secret, { algorithms: ['HS256'] });
  console.log('Token valid');
  console.log(payload);
} catch (err) {
  console.error(`Token invalid: ${err.message}`);
  process.exit(1);
}
