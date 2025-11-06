// backend/services/ollamaService.js

const axios = require('axios');
const config = require('../config/rickConfig');

/**
 * Call Ollama API to generate a response
 */
const generateResponse = async (prompt, options = {}) => {
  try {
    const response = await axios.post(
      `${config.ollama.url}/api/generate`,
      {
        model: config.ollama.model,
        prompt: prompt,
        stream: false,
        options: {
          temperature: options.temperature || 0.7,
          top_p: options.top_p || 0.9,
          ...options
        }
      },
      {
        timeout: config.ollama.timeout
      }
    );

    return {
      success: true,
      response: response.data.response,
      model: response.data.model
    };
  } catch (error) {
    console.error('Ollama API Error:', error.message);
    return {
      success: false,
      error: error.message,
      response: null
    };
  }
};

/**
 * Generate SQL query from natural language
 */
const generateSQL = async (context) => {
  const { schema, userMessage, memories, conversationHistory } = context;
  
  const prompt = `You are Rick, an AI assistant for teachers analyzing student data.

DATABASE SCHEMA:
${schema}

RELEVANT MEMORIES:
${memories || 'None'}

CONVERSATION HISTORY:
${conversationHistory || 'None'}

TEACHER'S QUESTION: "${userMessage}"

Generate a valid MySQL SELECT query to answer this question.
Rules:
- ONLY return the SQL query, nothing else
- Query must filter by teacher_id
- Use proper MySQL syntax
- Do not include explanations or markdown
- Query should return relevant data to answer the question

SQL Query:`;

  const result = await generateResponse(prompt, { temperature: 0.3 });
  
  if (!result.success) {
    return {
      success: false,
      sql: null,
      error: result.error
    };
  }

  // Extract SQL from response (remove any extra text)
  let sql = result.response.trim();
  
  // Remove markdown code blocks if present
  sql = sql.replace(/```sql/gi, '').replace(/```/g, '').trim();
  
  // Remove any explanatory text before/after the query
  const lines = sql.split('\n');
  sql = lines.find(line => line.trim().toUpperCase().startsWith('SELECT')) || sql;

  return {
    success: true,
    sql: sql.trim(),
    error: null
  };
};

/**
 * Format query results into natural language response
 */
const formatResponse = async (context) => {
  const { userMessage, queryResults, memories, conversationHistory } = context;
  
  const prompt = `You are Rick, a friendly AI assistant helping teachers analyze student data.

TEACHER'S QUESTION: "${userMessage}"

QUERY RESULTS:
${JSON.stringify(queryResults, null, 2)}

RELEVANT MEMORIES:
${memories || 'None'}

CONVERSATION HISTORY:
${conversationHistory || 'None'}

Generate a clear, conversational response to answer the teacher's question.
Rules:
- Be concise but friendly
- Reference specific data from the results
- If there are memories, weave them naturally into your response
- Use the teacher's language style
- If results are empty, say so politely
- Keep response under 200 words

Response:`;

  const result = await generateResponse(prompt, { temperature: 0.7 });
  
  if (!result.success) {
    return {
      success: false,
      response: 'Sorry, I had trouble formatting that response.',
      error: result.error
    };
  }

  return {
    success: true,
    response: result.response.trim(),
    error: null
  };
};

/**
 * Simple chat response (no SQL needed)
 */
const chatResponse = async (context) => {
  const { userMessage, memories, conversationHistory, teacherName } = context;
  
  const prompt = `You are Rick, a friendly AI assistant helping ${teacherName} with their class.

CONVERSATION HISTORY:
${conversationHistory || 'This is the start of the conversation'}

RELEVANT MEMORIES:
${memories || 'None'}

TEACHER: "${userMessage}"

Respond naturally and helpfully. Keep it conversational and brief (under 150 words).

Rick:`;

  const result = await generateResponse(prompt, { temperature: 0.8 });
  
  if (!result.success) {
    return {
      success: false,
      response: 'Sorry, I seem to be having trouble right now.',
      error: result.error
    };
  }

  return {
    success: true,
    response: result.response.trim(),
    error: null
  };
};

/**
 * Check if Ollama is running and model is available
 */
const healthCheck = async () => {
  try {
    const response = await axios.get(`${config.ollama.url}/api/tags`, {
      timeout: 5000
    });
    
    const modelExists = response.data.models.some(
      m => m.name === config.ollama.model
    );
    
    return {
      success: true,
      modelAvailable: modelExists,
      models: response.data.models.map(m => m.name)
    };
  } catch (error) {
    return {
      success: false,
      error: 'Ollama is not running or not accessible'
    };
  }
};

module.exports = {
  generateResponse,
  generateSQL,
  formatResponse,
  chatResponse,
  healthCheck
};
