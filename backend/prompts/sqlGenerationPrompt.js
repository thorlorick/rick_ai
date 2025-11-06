// backend/prompts/sqlGenerationPrompt.js

/**
 * Generate a detailed prompt for SQL generation
 */
const buildSQLPrompt = (context) => {
  const { schema, userMessage, memories, conversationHistory, teacherId } = context;
  
  return `You are Rick, an AI assistant for teachers. Your job is to convert natural language questions into MySQL queries.

DATABASE SCHEMA:
${schema}

IMPORTANT RULES:
1. Generate ONLY a valid MySQL SELECT query
2. Do NOT include any explanations, comments, or markdown
3. Query MUST include: WHERE teacher_id = ${teacherId}
4. Use proper MySQL syntax
5. Return only the SQL statement, nothing else
6. Use appropriate JOINs when querying multiple tables
7. Use aggregate functions (COUNT, AVG, SUM) when appropriate
8. Limit results to 50 rows unless specifically asked for more

${memories ? `RELEVANT CONTEXT FROM PAST CONVERSATIONS:\n${memories}\n` : ''}

${conversationHistory ? `RECENT CONVERSATION:\n${conversationHistory}\n` : ''}

TEACHER'S QUESTION: "${userMessage}"

Generate the SQL query now:`;
};

/**
 * Generate a simpler prompt for basic queries
 */
const buildSimpleSQLPrompt = (userMessage, teacherId) => {
  return `Convert this question to a MySQL SELECT query:
"${userMessage}"

Rules:
- Must filter by teacher_id = ${teacherId}
- Return only the SQL, no explanations
- Use proper MySQL syntax

Query:`;
};

module.exports = {
  buildSQLPrompt,
  buildSimpleSQLPrompt
};
