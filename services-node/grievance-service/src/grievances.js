const express = require('express');
const jwt = require('jsonwebtoken');
const { Pool } = require('pg');

const router = express.Router();

// Setup your database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Middleware to check the token
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ detail: "No token provided" });
  }

  // Use the SAME secret key from your Python auth service
  const secret = process.env.SECRET_KEY || "change-me-in-production";
  
  jwt.verify(token, secret, (err, decodedUser) => {
    if (err) {
      return res.status(403).json({ detail: "Invalid or expired token" });
    }
    req.user = decodedUser; // The Python service saved the user ID in "sub"
    next();
  });
};

// POST Route for Feature 1
router.post('/grievances', authenticateToken, async (req, res) => {
  const { platform, category, description, is_anonymous } = req.body;
  const worker_id = req.user.sub; // Extracted safely from the token

  try {
    // Insert into database and default status to 'Open'
    const query = `
      INSERT INTO grievance_svc.grievances 
      (worker_id, platform, category, description, status, is_anonymous, created_at)
      VALUES ($1, $2, $3, $4, 'Open', $5, NOW())
      RETURNING id, worker_id, platform, category, description, status, is_anonymous, created_at;
    `;
    const values = [worker_id, platform, category, description, is_anonymous];

    const result = await pool.query(query, values);
    const newGrievance = result.rows[0];

    // Security Rule: If anonymous, delete the worker_id before sending the response
    if (newGrievance.is_anonymous) {
      delete newGrievance.worker_id;
    }

    res.status(201).json(newGrievance);

  } catch (error) {
    console.error("Database Error:", error);
    res.status(500).json({ detail: "Failed to save grievance" });
  }
});

module.exports = router;