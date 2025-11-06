// backend/services/memoryService.js

const mysql = require('mysql2/promise');
const config = require('../config/rickConfig');
const { extractStudentNames } = require('../utils/contextBuilder');

// Create connection pool
const pool = mysql.createPool({
  host: config.database.host,
  user: config.database.user,
  password: config.database.password,
  database: config.database.database,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

/**
 * Save a new memory
 */
const saveMemory = async (teacherId, memoryContent, studentId = null) => {
  try {
    // Extract tags (student names, keywords)
    const tags = extractStudentNames(memoryContent);
    
    const [result] = await pool.execute(
      `INSERT INTO rick_memory 
       (teacher_id, student_id, memory_content, tags, created_at) 
       VALUES (?, ?, ?, ?, NOW())`,
      [
        teacherId,
        studentId,
        memoryContent,
        JSON.stringify(tags)
      ]
    );

    return {
      success: true,
      memoryId: result.insertId,
      message: 'Memory saved successfully'
    };
  } catch (error) {
    console.error('Error saving memory:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Get memories for a teacher (optionally filtered by student)
 */
const getMemories = async (teacherId, studentName = null, limit = 20) => {
  try {
    let query = `
      SELECT m.*, s.name as student_name
      FROM rick_memory m
      LEFT JOIN students s ON m.student_id = s.id
      WHERE m.teacher_id = ?
    `;
    
    const params = [teacherId];
    
    // Filter by student name if provided
    if (studentName) {
      query += ` AND (s.name LIKE ? OR m.memory_content LIKE ?)`;
      params.push(`%${studentName}%`, `%${studentName}%`);
    }
    
    query += ` ORDER BY m.created_at DESC LIMIT ?`;
    params.push(limit);

    const [memories] = await pool.execute(query, params);

    return {
      success: true,
      memories: memories.map(m => ({
        id: m.id,
        content: m.memory_content,
        studentName: m.student_name,
        tags: JSON.parse(m.tags || '[]'),
        createdAt: m.created_at
      }))
    };
  } catch (error) {
    console.error('Error fetching memories:', error);
    return {
      success: false,
      memories: [],
      error: error.message
    };
  }
};

/**
 * Get relevant memories based on current message context
 */
const getRelevantMemories = async (teacherId, message, limit = 5) => {
  try {
    // Extract potential student names from message
    const studentNames = extractStudentNames(message);
    
    if (studentNames.length === 0) {
      // No student names found, return recent general memories
      return getMemories(teacherId, null, limit);
    }
    
    // Search for memories mentioning these students
    const namePlaceholders = studentNames.map(() => 'memory_content LIKE ?').join(' OR ');
    const nameParams = studentNames.map(name => `%${name}%`);
    
    const query = `
      SELECT m.*, s.name as student_name
      FROM rick_memory m
      LEFT JOIN students s ON m.student_id = s.id
      WHERE m.teacher_id = ? AND (${namePlaceholders})
      ORDER BY m.created_at DESC
      LIMIT ?
    `;
    
    const [memories] = await pool.execute(
      query,
      [teacherId, ...nameParams, limit]
    );

    return {
      success: true,
      memories: memories.map(m => ({
        id: m.id,
        content: m.memory_content,
        studentName: m.student_name,
        tags: JSON.parse(m.tags || '[]'),
        createdAt: m.created_at
      }))
    };
  } catch (error) {
    console.error('Error fetching relevant memories:', error);
    return {
      success: false,
      memories: [],
      error: error.message
    };
  }
};

/**
 * Delete a memory
 */
const deleteMemory = async (teacherId, memoryId) => {
  try {
    const [result] = await pool.execute(
      'DELETE FROM rick_memory WHERE id = ? AND teacher_id = ?',
      [memoryId, teacherId]
    );

    if (result.affectedRows === 0) {
      return {
        success: false,
        error: 'Memory not found or you do not have permission to delete it'
      };
    }

    return {
      success: true,
      message: 'Memory deleted successfully'
    };
  } catch (error) {
    console.error('Error deleting memory:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Update a memory
 */
const updateMemory = async (teacherId, memoryId, newContent) => {
  try {
    const tags = extractStudentNames(newContent);
    
    const [result] = await pool.execute(
      `UPDATE rick_memory 
       SET memory_content = ?, tags = ?, updated_at = NOW()
       WHERE id = ? AND teacher_id = ?`,
      [newContent, JSON.stringify(tags), memoryId, teacherId]
    );

    if (result.affectedRows === 0) {
      return {
        success: false,
        error: 'Memory not found or you do not have permission to update it'
      };
    }

    return {
      success: true,
      message: 'Memory updated successfully'
    };
  } catch (error) {
    console.error('Error updating memory:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Get memory count for a teacher
 */
const getMemoryCount = async (teacherId) => {
  try {
    const [result] = await pool.execute(
      'SELECT COUNT(*) as count FROM rick_memory WHERE teacher_id = ?',
      [teacherId]
    );

    return {
      success: true,
      count: result[0].count
    };
  } catch (error) {
    console.error('Error counting memories:', error);
    return {
      success: false,
      count: 0,
      error: error.message
    };
  }
};

module.exports = {
  saveMemory,
  getMemories,
  getRelevantMemories,
  deleteMemory,
  updateMemory,
  getMemoryCount
};
