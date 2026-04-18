const express = require('express');
const certificateRoutes = require('./routes/certificate.routes');
const { verifyDbConnection } = require('./db/pool');
require('dotenv').config();

const app = express();
app.use(express.json());

// Mount the routes
app.use('/certificates', certificateRoutes);

const PORT = process.env.PORT || 8005; // Fallback to 8005 for Certificate Service

// Start the server and verify the DB Connection immediately
app.listen(PORT, async () => {
  console.log(`🚀 Certificate Service is running on port ${PORT}`);
  await verifyDbConnection();
});