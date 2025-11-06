// backend/routes/rick.js

const express = require('express');
const router = express.Router();
const rateLimit = require('express-rate-limit');
const { rickAuth } = require('../middleware/rickAuth');
const rickController = require('../controllers/rickController');
const config = require('../config/rickConfig');

// Rate limiting to prevent abuse
const chatLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: config.security.rateLimit, // requests per minute
  message: {
    success: false,
    error: 'Too many requests, please slow down'
  },
  standardHeaders: true,
  legacyHeaders: false,
});

// Apply authentication to all Rick routes
router.use(rickAuth);

/**
 * POST /api/rick/chat
 * Main chat endpoint - handles messages, commands, and queries
 */
router.post('/chat', chatLimiter, rickController.handleChat);

/**
 * GET /api/rick/quick-queries
 * Get list of available pre-defined queries
 */
router.get('/quick-queries', rickController.getQuickQueries);

/**
 * GET /api/rick/health
 * Health check - verify Ollama and database are working
 */
router.get('/health', rickController.healthCheck);

/**
 * Error handling middleware for Rick routes
 */
router.use((error, req, res, next) => {
  console.error('Rick route error:', error);
  
  res.status(500).json({
    success: false,
    error: 'An unexpected error occurred',
    message: process.env.NODE_ENV === 'development' ? error.message : undefined
  });
});

module.exports = router;
