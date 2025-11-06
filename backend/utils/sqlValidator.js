// backend/utils/sqlValidator.js

const config = require('../config/rickConfig');

/**
 * Validate SQL query for security
 * Returns: { valid: boolean, error: string | null }
 */
const validateSQL = (sql, teacherId) => {
  const upperSQL = sql.toUpperCase();

  // Check 1: Must be a SELECT statement
  if (!upperSQL.trim().startsWith('SELECT')) {
    return {
      valid: false,
      error: 'Only SELECT queries are allowed'
    };
  }

  // Check 2: No dangerous keywords
  for (const keyword of config.blockedKeywords) {
    if (upperSQL.includes(keyword)) {
      return {
        valid: false,
        error: `Blocked keyword detected: ${keyword}`
      };
    }
  }

  // Check 3: Must query from allowed tables only
  const tablePattern = /FROM\s+(\w+)/gi;
  const tables = [...sql.matchAll(tablePattern)].map(match => match[1].toLowerCase());
  
  for (const table of tables) {
    if (!config.allowedTables.includes(table)) {
      return {
        valid: false,
        error: `Table '${table}' is not allowed`
      };
    }
  }

  // Check 4: Must include teacher_id filter (basic check)
  // This is a simple check - we'll also inject it to be safe
  if (!sql.toLowerCase().includes('teacher_id')) {
    return {
      valid: false,
      error: 'Query must filter by teacher_id'
    };
  }

  return {
    valid: true,
    error: null
  };
};

/**
 * Inject teacher_id filter into SQL query
 * Ensures teacher can only see their own data
 */
const injectTeacherFilter = (sql, teacherId) => {
  // Simple approach: add to WHERE clause or create one
  const lowerSQL = sql.toLowerCase();
  
  if (lowerSQL.includes('where')) {
    // Add to existing WHERE clause
    return sql.replace(/where/i, `WHERE teacher_id = ${teacherId} AND`);
  } else if (lowerSQL.includes('from')) {
    // Add WHERE clause after FROM table
    return sql.replace(/from\s+(\w+)/i, `FROM $1 WHERE teacher_id = ${teacherId}`);
  }
  
  return sql;
};

/**
 * Sanitize SQL to prevent injection
 */
const sanitizeSQL = (sql) => {
  // Remove multiple statements (no semicolons except at end)
  const statements = sql.split(';').filter(s => s.trim());
  if (statements.length > 1) {
    return statements[0]; // Only allow first statement
  }
  
  return sql.trim();
};

/**
 * Main validation function - use this one
 */
const validateAndPrepareSQL = (sql, teacherId) => {
  // Sanitize first
  let cleanSQL = sanitizeSQL(sql);
  
  // Validate
  const validation = validateSQL(cleanSQL, teacherId);
  if (!validation.valid) {
    return {
      success: false,
      error: validation.error,
      sql: null
    };
  }
  
  // Inject teacher filter for extra security
  cleanSQL = injectTeacherFilter(cleanSQL, teacherId);
  
  return {
    success: true,
    error: null,
    sql: cleanSQL
  };
};

module.exports = {
  validateSQL,
  injectTeacherFilter,
  sanitizeSQL,
  validateAndPrepareSQL
};
