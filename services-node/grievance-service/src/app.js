const express = require('express');
const grievanceRoutes = require('./routes/grievance.routes');

const app = express();

app.use(express.json());

// This routes all requests starting with /grievances to your routes file
app.use('/grievances', grievanceRoutes);

module.exports = app;