const app = require('./src/app');
const { verifyDbConnection } = require('./src/db/pool');

// CORRECTED: Analytics runs on 8005, not 8006 (Certificate is 8006)
const PORT = process.env.PORT || 8006;

app.listen(PORT, async () => {
  console.log(`Analytics Service is running on port ${PORT}`);
  await verifyDbConnection();
});