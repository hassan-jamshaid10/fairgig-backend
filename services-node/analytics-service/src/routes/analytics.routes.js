const express = require('express');
const jwt = require('jsonwebtoken');
const {
  getCityMedian,
  getCommissionTrends,
  getZoneDistribution,
  getVulnerabilityFlags,
  getTopComplaints,
  getPlatforms
} = require('../controllers/analytics.controller');

const router = express.Router();

// ============================================
// JWT Middleware — verify Bearer token
// ============================================
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ detail: "No token provided" });
  }

  const secret = process.env.SECRET_KEY || "change-me-in-production";
  
  jwt.verify(token, secret, (err, decodedUser) => {
    if (err) {
      return res.status(403).json({ detail: "Invalid or expired token" });
    }
    req.user = decodedUser;
    next();
  });
};

// ============================================
// Routes
// ============================================

// Endpoint 1: City-wide median hourly rate (any role)
router.get('/city-median', authenticateToken, getCityMedian);

// Endpoint 2: Commission trends over time (any role)
router.get('/commission-trends', authenticateToken, getCommissionTrends);

// Endpoint 3: Zone income distribution (Advocate only — enforced in controller)
router.get('/zone-distribution', authenticateToken, getZoneDistribution);

// Endpoint 4: Vulnerability flags (Advocate only — enforced in controller)
router.get('/vulnerability-flags', authenticateToken, getVulnerabilityFlags);

// Endpoint 5: Top complaints this week (Advocate only — enforced in controller)
router.get('/top-complaints', authenticateToken, getTopComplaints);

// Endpoint 6: List of all platforms (any role)
router.get('/platforms', authenticateToken, getPlatforms);

module.exports = router;