const express = require('express');
const cors = require('cors');
const grievanceRoutes = require('./routes/grievance.routes');

const app = express();

app.use(
	cors({
		origin: true,
		credentials: true,
		methods: ['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'],
	})
);
app.options('*', cors());

app.use(express.json());

// This routes all requests starting with /grievances to your routes file
app.use('/grievances', grievanceRoutes);

module.exports = app;