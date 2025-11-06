// backend/controllers/rickController.js

const ollamaService = require('../services/ollamaService');
const memoryService = require('../services/memoryService');
const queryService = require('../services/queryService');
const { buildSchemaDescription, formatMemories, formatConversationHistory } = require('../utils/contextBuilder');
const { parseCommand, COMMANDS } = require('../utils/commandParser');

/**
 * Main chat handler
 */
const handleChat = async (req, res) => {
  try {
    const { message, conversation_history = [] } = req.body;
    const teacherId = req.teacherId;
    const teacherName = req.teacherName;

    if (!message || message.trim() === '') {
      return res.status(400).json({
        success: false,
        error: 'Message is required'
      });
    }

    // Parse for commands
    const parsed = parseCommand(message);
    
    if (parsed.isCommand) {
      return handleCommand(req, res, parsed);
    }

    // Check if this is a pre-defined query
    const quickQueryMatch = matchQuickQuery(message);
    if (quickQueryMatch) {
      return handleQuickQuery(req, res, quickQueryMatch);
    }

    // Get relevant memories
    const memoriesResult = await memoryService.getRelevantMemories(teacherId, message);
    const memories = memoriesResult.success ? memoriesResult.memories : [];

    // Build context
    const context = {
      teacherId,
      teacherName,
      userMessage: message,
      conversationHistory: formatConversationHistory(conversation_history),
      memories: formatMemories(memories),
      schema: buildSchemaDescription()
    };

    // Determine if we need to query the database
    const needsData = requiresDataQuery(message);

    if (needsData) {
      // Generate SQL query
      const sqlResult = await ollamaService.generateSQL(context);
      
      if (!sqlResult.success) {
        return res.json({
          success: true,
          response: "I had trouble understanding that query. Could you rephrase it?",
          needsData: false
        });
      }

      // Execute query
      const queryResult = await queryService.executeDynamicQuery(sqlResult.sql, teacherId);
      
      if (!queryResult.success) {
        return res.json({
          success: true,
          response: "I couldn't execute that query. Let me try to help another way.",
          error: queryResult.error
        });
      }

      // Format response with query results
      context.queryResults = queryResult.results;
      const formatted = await ollamaService.formatResponse(context);

      return res.json({
        success: true,
        response: formatted.response,
        data: queryResult.results,
        needsData: true
      });
    } else {
      // Simple chat response (no data needed)
      const chatResult = await ollamaService.chatResponse(context);
      
      return res.json({
        success: true,
        response: chatResult.response,
        needsData: false
      });
    }
  } catch (error) {
    console.error('Error in handleChat:', error);
    return res.status(500).json({
      success: false,
      error: 'An error occurred while processing your message'
    });
  }
};

/**
 * Handle command execution
 */
const handleCommand = async (req, res, parsed) => {
  const teacherId = req.teacherId;
  
  switch (parsed.command) {
    case COMMANDS.REMEMBER:
      if (!parsed.args) {
        return res.status(400).json({
          success: false,
          error: 'Please provide something to remember. Example: /remember Joe struggled with fractions'
        });
      }
      
      const saveResult = await memoryService.saveMemory(teacherId, parsed.args);
      
      return res.json({
        success: saveResult.success,
        response: saveResult.success 
          ? `Got it! I'll remember: "${parsed.args}"`
          : 'Sorry, I had trouble saving that memory.',
        isCommand: true
      });
    
    case COMMANDS.MEMORIES:
      const studentName = parsed.args || null;
      const memoriesResult = await memoryService.getMemories(teacherId, studentName);
      
      if (!memoriesResult.success || memoriesResult.memories.length === 0) {
        return res.json({
          success: true,
          response: studentName 
            ? `I don't have any memories about ${studentName}.`
            : "I don't have any saved memories yet.",
          memories: [],
          isCommand: true
        });
      }
      
      return res.json({
        success: true,
        response: formatMemoriesForDisplay(memoriesResult.memories, studentName),
        memories: memoriesResult.memories,
        isCommand: true
      });
    
    case COMMANDS.FORGET:
      const memoryId = parseInt(parsed.args);
      
      if (!memoryId || isNaN(memoryId)) {
        return res.status(400).json({
          success: false,
          error: 'Please provide a memory ID. Example: /forget 5'
        });
      }
      
      const deleteResult = await memoryService.deleteMemory(teacherId, memoryId);
      
      return res.json({
        success: deleteResult.success,
        response: deleteResult.success 
          ? 'Memory deleted successfully.'
          : deleteResult.error,
        isCommand: true
      });
    
    case COMMANDS.HELP:
      return res.json({
        success: true,
        response: getHelpText(),
        isCommand: true
      });
    
    default:
      return res.status(400).json({
        success: false,
        error: `Unknown command: /${parsed.command}. Type /help for available commands.`
      });
  }
};

/**
 * Handle quick query execution
 */
const handleQuickQuery = async (req, res, queryType) => {
  const teacherId = req.teacherId;
  
  const result = await queryService.executePredefinedQuery(queryType, teacherId);
  
  if (!result.success) {
    return res.json({
      success: true,
      response: 'I had trouble running that query. Please try again.',
      data: []
    });
  }
  
  // Format the results naturally
  const context = {
    userMessage: `Show me ${queryType.replace(/_/g, ' ')}`,
    queryResults: result.results
  };
  
  const formatted = await ollamaService.formatResponse(context);
  
  return res.json({
    success: true,
    response: formatted.response,
    data: result.results,
    queryType: queryType
  });
};

/**
 * Get available quick queries
 */
const getQuickQueries = async (req, res) => {
  try {
    const queries = queryService.getAvailableQueries();
    
    return res.json({
      success: true,
      queries: queries
    });
  } catch (error) {
    console.error('Error fetching quick queries:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to fetch quick queries'
    });
  }
};

/**
 * Health check endpoint
 */
const healthCheck = async (req, res) => {
  try {
    const ollamaHealth = await ollamaService.healthCheck();
    const dbHealth = await queryService.testConnection();
    
    return res.json({
      success: true,
      ollama: ollamaHealth,
      database: dbHealth,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    return res.status(500).json({
      success: false,
      error: 'Health check failed'
    });
  }
};

/**
 * Helper: Check if message requires data query
 */
const requiresDataQuery = (message) => {
  const dataKeywords = [
    'who', 'what', 'how many', 'list', 'show', 'find',
    'student', 'grade', 'assignment', 'average', 'score',
    'missing', 'struggling', 'attendance', 'absent'
  ];
  
  const lowerMessage = message.toLowerCase();
  return dataKeywords.some(keyword => lowerMessage.includes(keyword));
};

/**
 * Helper: Match message to quick query
 */
const matchQuickQuery = (message) => {
  const lowerMessage = message.toLowerCase();
  
  const patterns = {
    struggling_students: ['struggling', 'failing', 'below 60', 'low grade'],
    missing_assignments: ['missing', 'incomplete', 'not submitted', 'haven\'t done'],
    attendance_issues: ['attendance', 'absent', 'skipping', 'missing class'],
    class_average: ['class average', 'overall performance', 'how is my class'],
    recent_improvements: ['improved', 'getting better', 'progress'],
    assignment_completion: ['completion rate', 'who completed', 'assignment status']
  };
  
  for (const [queryType, keywords] of Object.entries(patterns)) {
    if (keywords.some(keyword => lowerMessage.includes(keyword))) {
      return queryType;
    }
  }
  
  return null;
};

/**
 * Helper: Format memories for display
 */
const formatMemoriesForDisplay = (memories, studentName) => {
  const header = studentName 
    ? `Here are my memories about ${studentName}:\n\n`
    : 'Here are my saved memories:\n\n';
  
  const memoryList = memories.map((m, index) => {
    const date = new Date(m.createdAt).toLocaleDateString();
    return `${index + 1}. [ID: ${m.id}] ${m.content} (${date})`;
  }).join('\n');
  
  return header + memoryList + '\n\nUse /forget [ID] to delete a memory.';
};

/**
 * Helper: Get help text
 */
const getHelpText = () => {
  return `Available commands:

/remember [note] - Save a note to my memory
Example: /remember Joe was struggling with quadratic equations

/memories [student name] - View saved memories
Example: /memories Joe

/forget [memory ID] - Delete a memory
Example: /forget 5

/help - Show this help message

You can also ask me questions about your students, grades, and assignments!`;
};

module.exports = {
  handleChat,
  getQuickQueries,
  healthCheck
};
