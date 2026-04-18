const express = require('express');
const jwt = require('jsonwebtoken');
const { 
  previewCertificateData,
  getWorkerCertificateData,
  getWorkerCertificateById 
} = require('../controllers/certificate.controller');

const router = express.Router();

const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) return res.status(401).json({ detail: "No token provided" });

  const secret = process.env.SECRET_KEY || "change-me-in-production";
  jwt.verify(token, secret, (err, decodedUser) => {
    if (err) return res.status(403).json({ detail: "Invalid or expired token" });
    req.user = decodedUser;
    next();
  });
};

// 1. Preview API (Optional/Testing)
router.get('/preview', authenticateToken, previewCertificateData);

// 2. Feature 2: Worker requests their own
router.get('/me', authenticateToken, getWorkerCertificateData);

// 3. Feature 3: Request by ID (MUST BE AT THE BOTTOM)
router.get('/:worker_id', authenticateToken, getWorkerCertificateById);

module.exports = router;