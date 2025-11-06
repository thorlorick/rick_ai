// backend/config/rickConfig.js

module.exports = {
  // Ollama settings
  ollama: {
    url: process.env.OLLAMA_URL || 'http://localhost:11434',
    model: process.env.OLLAMA_MODEL || 'qwen2.5:1.5b',
    timeout: 30000, // 30 seconds
  },

  // Database settings (RICK read-only user)
  database: {
    host: process.env.RICK_DB_HOST || 'localhost',
    user: process.env.RICK_DB_USER || 'RICK',
    password: process.env.RICK_DB_PASSWORD,
    database: process.env.RICK_DB_NAME || 'gradeinsight',
  },

  // Security settings
  security: {
    queryTimeout: parseInt(process.env.RICK_QUERY_TIMEOUT) || 5000, // 5 seconds
    rateLimit: parseInt(process.env.RICK_RATE_LIMIT) || 60, // requests per minute
    maxConversationHistory: 10, // messages to keep in context
    maxMemoriesPerQuery: 5, // relevant memories to include
  },

  // Allowed tables for SQL queries
  allowedTables: [
    'students',
    'grades',
    'assignments',
    'attendance',
    'courses',
    'classes'
  ],

  // Dangerous SQL keywords (block these)
  blockedKeywords: [
    'DROP',
    'DELETE',
    'UPDATE',
    'INSERT',
    'ALTER',
    'TRUNCATE',
    'GRANT',
    'REVOKE',
    'CREATE',
    'REPLACE',
    'EXEC',
    'EXECUTE'
  ],
};
