const express = require('express');
const jwt = require('jsonwebtoken');

// CHANGE 1: I added "getGrievances" to this import list
const { 
  createGrievance, 
  getGrievances, 
  getGrievanceById, 
  getCommentsByGrievanceId,
  addComment,
  addAdvocateTag,
  getTrendingTags,
  clusterGrievances,
  getClusterSummaries,
  getTrendingTagsVolume // <--- MUST BE IMPORTED HERE
} = require('../controllers/grievance.controller');
const router = express.Router();

const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ detail: "No token provided" });
  }

  const secret = process.env.SECRET_KEY || "change-me-in-production";
  
  jwt.verify(token, secret, (err, decodedUser) => {
    if (err) {
      console.error("JWT FAILURE REASON:", err.message);
      return res.status(403).json({ detail: "Invalid or expired token" });
    }
    req.user = decodedUser;
    next();
  });
};

// The endpoint is just '/' because app.js already handles the '/grievances' part
router.post('/', authenticateToken, createGrievance);

// CHANGE 2: I added this brand new GET route right before the export
router.get('/', authenticateToken, getGrievances);

router.get('/trends', authenticateToken, getTrendingTags);

router.post('/cluster', authenticateToken, clusterGrievances);

router.get('/clusters/summary', authenticateToken, getClusterSummaries);

router.get('/trending-tags', authenticateToken, getTrendingTagsVolume);

router.get('/:id', authenticateToken, getGrievanceById);

router.get('/:id/comments', authenticateToken, getCommentsByGrievanceId);

router.post('/:id/comments', authenticateToken, addComment);

router.patch('/:id/tag', authenticateToken, addAdvocateTag);



module.exports = router;