// backend/prompts/responseFormattingPrompt.js

/**
 * Generate a prompt for formatting query results into natural language
 */
const buildResponsePrompt = (context) => {
  const { userMessage, queryResults, memories, conversationHistory, teacherName } = context;
  
  // Handle empty results
  if (!queryResults || queryResults.length === 0) {
    return buildEmptyResultsPrompt(userMessage, teacherName);
  }
  
  return `You are Rick, a friendly and helpful AI assistant for ${teacherName}.

TEACHER'S QUESTION: "${userMessage}"

QUERY RESULTS:
${formatResultsForPrompt(queryResults)}

${memories ? `RELEVANT MEMORIES:\n${memories}\n` : ''}

${conversationHistory ? `CONVERSATION CONTEXT:\n${conversationHistory}\n` : ''}

YOUR TASK:
Write a clear, conversational response that answers the teacher's question using the data above.

GUIDELINES:
- Be friendly and natural (you're Rick, not a robot)
- Reference specific data points from the results
- If you have relevant memories, mention them naturally
- Keep it concise (under 200 words)
- Use the teacher's name occasionally
- If the data shows concerning patterns, mention them
- End with an offer to help further if appropriate

Response:`;
};

/**
 * Generate a prompt for empty results
 */
const buildEmptyResultsPrompt = (userMessage, teacherName) => {
  return `You are Rick, an AI assistant for ${teacherName}.

The teacher asked: "${userMessage}"

However, the query returned no results.

Generate a friendly response explaining that there's no data matching their question. 
Suggest they might want to:
- Rephrase the question
- Check if they're looking at the right time period
- Or ask something else

Keep it brief and helpful (under 100 words).

Response:`;
};

/**
 * Format query results for the prompt
 */
const formatResultsForPrompt = (results) => {
  if (!Array.isArray(results) || results.length === 0) {
    return 'No data found';
  }
  
  // Limit to first 20 results to avoid token limits
  const limitedResults = results.slice(0, 20);
  
  // Format as a readable table
  const headers = Object.keys(limitedResults[0]);
  let formatted = `Found ${results.length} result(s):\n\n`;
  
  limitedResults.forEach((row, index) => {
    formatted += `Result ${index + 1}:\n`;
    headers.forEach(header => {
      formatted += `  ${header}: ${row[header]}\n`;
    });
    formatted += '\n';
  });
  
  if (results.length > 20) {
    formatted += `(Showing first 20 of ${results.length} results)\n`;
  }
  
  return formatted;
};

/**
 * Generate a prompt for simple chat (no data)
 */
const buildChatPrompt = (context) => {
  const { userMessage, memories, conversationHistory, teacherName } = context;
  
  return `You are Rick, a friendly AI assistant helping ${teacherName} with their teaching.

${conversationHistory ? `CONVERSATION SO FAR:\n${conversationHistory}\n` : ''}

${memories ? `RELEVANT MEMORIES:\n${memories}\n` : ''}

TEACHER: "${userMessage}"

Respond naturally and helpfully. You can:
- Answer questions about teaching strategies
- Discuss student engagement
- Provide general advice
- Have a friendly conversation
- Reference memories if relevant

Keep your response conversational and under 150 words.

Rick:`;
};

module.exports = {
  buildResponsePrompt,
  buildEmptyResultsPrompt,
  buildChatPrompt,
  formatResultsForPrompt
};
