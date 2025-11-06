// backend/utils/contextBuilder.js

/**
 * Build context object for Ollama prompts
 * Combines: schema, memories, conversation history, teacher info
 */

const buildContext = (options) => {
  const {
    teacherId,
    teacherName,
    conversationHistory = [],
    memories = [],
    databaseSchema = null,
    userMessage = ''
  } = options;

  return {
    teacher: {
      id: teacherId,
      name: teacherName
    },
    conversation: conversationHistory,
    memories: memories,
    schema: databaseSchema,
    currentMessage: userMessage,
    timestamp: new Date().toISOString()
  };
};

/**
 * Format memories for inclusion in prompt
 */
const formatMemories = (memories) => {
  if (!memories || memories.length === 0) {
    return 'No previous memories about this topic.';
  }

  return memories.map((memory, index) => {
    const date = new Date(memory.created_at).toLocaleDateString();
    return `Memory ${index + 1} (${date}): ${memory.memory_content}`;
  }).join('\n');
};

/**
 * Format conversation history for prompt
 */
const formatConversationHistory = (history) => {
  if (!history || history.length === 0) {
    return '';
  }

  return history.map(msg => {
    const role = msg.role === 'user' ? 'Teacher' : 'Rick';
    return `${role}: ${msg.content}`;
  }).join('\n');
};

/**
 * Build database schema description for prompt
 */
const buildSchemaDescription = () => {
  return `
Available Tables:
- students: id, name, email, teacher_id
- grades: id, student_id, assignment_id, grade, teacher_id
- assignments: id, name, due_date, total_points, teacher_id
- attendance: id, student_id, date, status, teacher_id

You can query these tables to answer questions about students, grades, assignments, and attendance.
Always filter by teacher_id to ensure data privacy.
`;
};

/**
 * Extract student names from message
 */
const extractStudentNames = (message) => {
  // Basic extraction - looks for capitalized words
  // You might want to improve this with a list of known student names
  const words = message.split(/\s+/);
  const potentialNames = words.filter(word => {
    return word.length > 2 && /^[A-Z][a-z]+$/.test(word);
  });
  
  return potentialNames;
};

module.exports = {
  buildContext,
  formatMemories,
  formatConversationHistory,
  buildSchemaDescription,
  extractStudentNames
};
