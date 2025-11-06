// backend/middleware/rickAuth.js

/**
 * Middleware to verify teacher authentication for Rick AI routes
 * Assumes you have existing authentication that sets req.user or req.session
 */

const rickAuth = (req, res, next) => {
  // Check if user is authenticated
  // Adjust this based on your existing auth system
  
  // Option 1: If you're using JWT
  if (req.user && req.user.teacher_id) {
    req.teacherId = req.user.teacher_id;
    req.teacherName = req.user.name || req.user.username;
    return next();
  }
  
  // Option 2: If you're using sessions
  if (req.session && req.session.teacher_id) {
    req.teacherId = req.session.teacher_id;
    req.teacherName = req.session.teacher_name;
    return next();
  }
  
  // Not authenticated
  return res.status(401).json({
    success: false,
    error: 'Authentication required to use Rick AI'
  });
};

/**
 * Optional: Verify teacher has access to specific student
 */
const verifyStudentAccess = async (req, res, next) => {
  const { student_id } = req.body;
  const teacherId = req.teacherId;
  
  if (!student_id) {
    return next(); // No student specified, continue
  }
  
  // TODO: Query database to verify teacher teaches this student
  // This is a placeholder - you'll need to implement this based on your schema
  
  try {
    // Example query (adjust to your schema):
    // const result = await db.query(
    //   'SELECT 1 FROM students WHERE id = ? AND teacher_id = ?',
    //   [student_id, teacherId]
    // );
    
    // if (result.length === 0) {
    //   return res.status(403).json({
    //     success: false,
    //     error: 'You do not have access to this student'
    //   });
    // }
    
    next();
  } catch (error) {
    console.error('Error verifying student access:', error);
    return res.status(500).json({
      success: false,
      error: 'Error verifying access'
    });
  }
};

module.exports = {
  rickAuth,
  verifyStudentAccess
};
