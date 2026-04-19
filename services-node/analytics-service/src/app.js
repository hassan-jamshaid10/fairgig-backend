const express = require('express');
const cors = require('cors');
const analyticsRoutes = require('./routes/analytics.routes');
require('dotenv').config();

const app = express();

app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'analytics', 
    port: process.env.PORT || 8006
  });
});

app.use('/analytics', analyticsRoutes);

module.exports = app;