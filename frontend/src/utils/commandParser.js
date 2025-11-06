// frontend/src/utils/commandParser.js

/**
 * Parse user input for commands
 * Returns: { isCommand: boolean, command: string, args: string }
 */
export const parseCommand = (message) => {
  const trimmed = message.trim();
  
  // Check if message starts with /
  if (!trimmed.startsWith('/')) {
    return {
      isCommand: false,
      command: null,
      args: null,
      original: message
    };
  }

  // Split command and arguments
  const parts = trimmed.slice(1).split(' ');
  const command = parts[0].toLowerCase();
  const args = parts.slice(1).join(' ').trim();

  return {
    isCommand: true,
    command,
    args,
    original: message
  };
};

/**
 * Available commands
 */
export const COMMANDS = {
  REMEMBER: 'remember',
  MEMORIES: 'memories',
  FORGET: 'forget',
  HELP: 'help'
};

/**
 * Validate command
 */
export const isValidCommand = (command) => {
  return Object.values(COMMANDS).includes(command);
};

/**
 * Get command help text
 */
export const getCommandHelp = (command) => {
  const helpText = {
    remember: '/remember [note] - Save a note to Rick\'s memory',
    memories: '/memories [optional: student name] - View saved memories',
    forget: '/forget [memory id] - Delete a memory',
    help: '/help - Show available commands'
  };

  return command ? helpText[command] : Object.values(helpText).join('\n');
};
