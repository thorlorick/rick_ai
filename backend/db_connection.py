"""
GradeInsight Database Connection
Read-only MySQL connection with safe query methods
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class GradeInsightDB:
    """Read-only database connection for Rick AI"""
    
    def __init__(self):
        # Get credentials from environment
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '8090'),
            'user': os.getenv('DB_USER_READONLY', 'RICK'),
            'password': os.getenv('DB_PASSWORD_READONLY'),
            'database': os.getenv('DB_NAME', 'grade_insight')
        }
        
        if not db_config['password']:
            raise ValueError("DB_PASSWORD_READONLY not set in environment")
        
        # Create read-only connection string
        connection_string = (
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        
        self.engine = create_engine(
            connection_string,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=False  # Set True for SQL debugging
        )
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        print(f"✓ Connected to database: {db_config['database']} (read-only)")
    
    def execute_safe_query(self, query: str, params: dict = None) -> List[Dict]:
        """Execute a read-only query safely"""
        # Validate it's a SELECT query
        if not query.strip().upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries allowed")
        
        try:
            with self.SessionLocal() as session:
                result = session.execute(text(query), params or {})
                return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"❌ Database query error: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            query = "SELECT 1 as test"
            result = self.execute_safe_query(query)
            return len(result) > 0
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    # ========================================================================
    # Pre-defined Safe Queries
    # ========================================================================
    
    def get_struggling_students(self, teacher_id: int, threshold: float = 70.0) -> List[Dict]:
        """Get students below grade threshold with details"""
        query = """
            SELECT 
                s.id,
                s.first_name,
                s.last_name,
                s.email,
                ROUND(AVG(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    THEN (g.grade / a.max_points * 100) 
                END), 1) as avg_grade,
                COUNT(CASE WHEN g.grade IS NULL THEN 1 END) as missing_count,
                COUNT(a.id) as total_assignments,
                tn.note as teacher_note
            FROM students s
            LEFT JOIN grades g ON s.id = g.student_id AND g.teacher_id = :teacher_id
            LEFT JOIN assignments a ON g.assignment_id = a.id AND a.teacher_id = :teacher_id
            LEFT JOIN teacher_notes tn ON s.id = tn.student_id AND tn.teacher_id = :teacher_id
            WHERE EXISTS (
                SELECT 1 FROM grades g2 
                WHERE g2.student_id = s.id AND g2.teacher_id = :teacher_id
            )
            GROUP BY s.id, s.first_name, s.last_name, s.email, tn.note
            HAVING avg_grade < :threshold OR missing_count > 3
            ORDER BY avg_grade ASC, missing_count DESC
            LIMIT 50
        """
        return self.execute_safe_query(query, {
            "teacher_id": teacher_id, 
            "threshold": threshold
        })
    
    def get_student_detail(self, teacher_id: int, student_id: int) -> Optional[Dict]:
        """Get detailed grades for a specific student"""
        query = """
            SELECT 
                s.id as student_id,
                s.first_name,
                s.last_name,
                s.email,
                a.id as assignment_id,
                a.name as assignment_name,
                a.due_date,
                a.max_points,
                g.grade,
                CASE 
                    WHEN g.grade IS NULL THEN NULL
                    WHEN a.max_points > 0 THEN ROUND(g.grade / a.max_points * 100, 1)
                    ELSE NULL
                END as percentage,
                tn.note as teacher_note,
                tn.updated_at as note_updated
            FROM students s
            LEFT JOIN grades g ON s.id = g.student_id AND g.teacher_id = :teacher_id
            LEFT JOIN assignments a ON g.assignment_id = a.id
            LEFT JOIN teacher_notes tn ON s.id = tn.student_id AND tn.teacher_id = :teacher_id
            WHERE s.id = :student_id
            ORDER BY a.due_date DESC
        """
        
        results = self.execute_safe_query(query, {
            "teacher_id": teacher_id,
            "student_id": student_id
        })
        
        if not results:
            return None
        
        # Format response with student info and assignments
        first_row = results[0]
        student_info = {
            "student_id": first_row['student_id'],
            "name": f"{first_row['first_name']} {first_row['last_name']}",
            "first_name": first_row['first_name'],
            "last_name": first_row['last_name'],
            "email": first_row['email'],
            "teacher_note": first_row.get('teacher_note'),
            "note_updated": str(first_row.get('note_updated')) if first_row.get('note_updated') else None,
            "assignments": []
        }
        
        # Calculate overall stats
        completed = []
        missing = []
        
        for row in results:
            if row['assignment_name']:
                assignment = {
                    "assignment_id": row['assignment_id'],
                    "name": row['assignment_name'],
                    "due_date": str(row['due_date']) if row['due_date'] else None,
                    "grade": row['grade'],
                    "max_points": row['max_points'],
                    "percentage": row['percentage'],
                    "status": "missing" if row['grade'] is None else "completed"
                }
                student_info["assignments"].append(assignment)
                
                if row['percentage'] is not None:
                    completed.append(row['percentage'])
                elif row['grade'] is None:
                    missing.append(row['assignment_name'])
        
        # Add summary statistics
        student_info["summary"] = {
            "total_assignments": len(student_info["assignments"]),
            "completed": len(completed),
            "missing": len(missing),
            "average_grade": round(sum(completed) / len(completed), 1) if completed else None,
            "lowest_grade": min(completed) if completed else None,
            "highest_grade": max(completed) if completed else None
        }
        
        return student_info
    
    def get_assignment_analysis(self, teacher_id: int) -> List[Dict]:
        """Analyze which assignments were hardest/easiest"""
        query = """
            SELECT 
                a.id as assignment_id,
                a.name as assignment_name,
                a.due_date,
                a.max_points,
                COUNT(g.id) as total_submissions,
                COUNT(CASE WHEN g.grade IS NOT NULL THEN 1 END) as completed,
                COUNT(CASE WHEN g.grade IS NULL THEN 1 END) as missing,
                ROUND(AVG(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    THEN (g.grade / a.max_points * 100)
                END), 1) as avg_percentage,
                ROUND(MIN(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    THEN (g.grade / a.max_points * 100)
                END), 1) as min_percentage,
                ROUND(MAX(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    THEN (g.grade / a.max_points * 100)
                END), 1) as max_percentage,
                ROUND(STDDEV(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    THEN (g.grade / a.max_points * 100)
                END), 1) as std_deviation
            FROM assignments a
            LEFT JOIN grades g ON a.id = g.assignment_id
            WHERE a.teacher_id = :teacher_id
            GROUP BY a.id, a.name, a.due_date, a.max_points
            HAVING total_submissions > 0
            ORDER BY avg_percentage ASC, missing DESC
            LIMIT 50
        """
        return self.execute_safe_query(query, {"teacher_id": teacher_id})
    
    def get_students_with_missing_work(self, teacher_id: int, min_missing: int = 1) -> List[Dict]:
        """Get students with missing assignments"""
        query = """
            SELECT 
                s.id,
                s.first_name,
                s.last_name,
                s.email,
                COUNT(CASE WHEN g.grade IS NULL THEN 1 END) as missing_count,
                COUNT(a.id) as total_assignments,
                ROUND(COUNT(CASE WHEN g.grade IS NULL THEN 1 END) / COUNT(a.id) * 100, 1) as missing_percentage,
                GROUP_CONCAT(
                    CASE WHEN g.grade IS NULL THEN a.name END 
                    ORDER BY a.due_date 
                    SEPARATOR ', '
                ) as missing_assignments,
                tn.note as teacher_note
            FROM students s
            LEFT JOIN grades g ON s.id = g.student_id AND g.teacher_id = :teacher_id
            LEFT JOIN assignments a ON g.assignment_id = a.id
            LEFT JOIN teacher_notes tn ON s.id = tn.student_id AND tn.teacher_id = :teacher_id
            WHERE EXISTS (
                SELECT 1 FROM grades g2 
                WHERE g2.student_id = s.id AND g2.teacher_id = :teacher_id
            )
            GROUP BY s.id, s.first_name, s.last_name, s.email, tn.note
            HAVING missing_count >= :min_missing
            ORDER BY missing_count DESC
            LIMIT 50
        """
        return self.execute_safe_query(query, {
            "teacher_id": teacher_id,
            "min_missing": min_missing
        })
    
    def get_class_overview(self, teacher_id: int) -> Dict:
        """Get overall class statistics"""
        query = """
            SELECT 
                COUNT(DISTINCT s.id) as total_students,
                COUNT(DISTINCT a.id) as total_assignments,
                ROUND(AVG(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    THEN (g.grade / a.max_points * 100)
                END), 1) as class_average,
                COUNT(CASE WHEN g.grade IS NULL THEN 1 END) as total_missing,
                COUNT(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    AND (g.grade / a.max_points * 100) >= 90 
                    THEN 1 
                END) as a_grades,
                COUNT(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    AND (g.grade / a.max_points * 100) >= 80 
                    AND (g.grade / a.max_points * 100) < 90 
                    THEN 1 
                END) as b_grades,
                COUNT(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    AND (g.grade / a.max_points * 100) >= 70 
                    AND (g.grade / a.max_points * 100) < 80 
                    THEN 1 
                END) as c_grades,
                COUNT(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    AND (g.grade / a.max_points * 100) >= 60 
                    AND (g.grade / a.max_points * 100) < 70 
                    THEN 1 
                END) as d_grades,
                COUNT(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    AND (g.grade / a.max_points * 100) < 60 
                    THEN 1 
                END) as f_grades
            FROM assignments a
            LEFT JOIN grades g ON a.id = g.assignment_id
            LEFT JOIN students s ON g.student_id = s.id
            WHERE a.teacher_id = :teacher_id
        """
        
        results = self.execute_safe_query(query, {"teacher_id": teacher_id})
        
        if results:
            return results[0]
        return {}
    
    def get_recent_grade_trends(self, teacher_id: int, days: int = 30) -> List[Dict]:
        """Get grade trends over time"""
        query = """
            SELECT 
                DATE(a.due_date) as date,
                a.name as assignment_name,
                ROUND(AVG(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    THEN (g.grade / a.max_points * 100)
                END), 1) as avg_score,
                COUNT(g.id) as submissions
            FROM assignments a
            LEFT JOIN grades g ON a.id = g.assignment_id
            WHERE a.teacher_id = :teacher_id
                AND a.due_date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                AND a.due_date <= CURDATE()
            GROUP BY DATE(a.due_date), a.name
            ORDER BY a.due_date DESC
        """
        return self.execute_safe_query(query, {
            "teacher_id": teacher_id,
            "days": days
        })
    
    def search_student_by_name(self, teacher_id: int, name_query: str) -> List[Dict]:
        """Search for students by name"""
        query = """
            SELECT DISTINCT
                s.id,
                s.first_name,
                s.last_name,
                s.email,
                ROUND(AVG(CASE 
                    WHEN g.grade IS NOT NULL AND a.max_points > 0 
                    THEN (g.grade / a.max_points * 100)
                END), 1) as avg_grade
            FROM students s
            JOIN grades g ON s.id = g.student_id
            JOIN assignments a ON g.assignment_id = a.id
            WHERE g.teacher_id = :teacher_id
                AND (
                    LOWER(s.first_name) LIKE LOWER(:name_query)
                    OR LOWER(s.last_name) LIKE LOWER(:name_query)
                    OR LOWER(CONCAT(s.first_name, ' ', s.last_name)) LIKE LOWER(:name_query)
                )
            GROUP BY s.id, s.first_name, s.last_name, s.email
            LIMIT 20
        """
        return self.execute_safe_query(query, {
            "teacher_id": teacher_id,
            "name_query": f"%{name_query}%"
        })
    
    def get_teacher_notes(self, teacher_id: int) -> List[Dict]:
        """Get all teacher notes"""
        query = """
            SELECT 
                tn.id,
                s.id as student_id,
                s.first_name,
                s.last_name,
                tn.note,
                tn.created_at,
                tn.updated_at
            FROM teacher_notes tn
            JOIN students s ON tn.student_id = s.id
            WHERE tn.teacher_id = :teacher_id
            ORDER BY tn.updated_at DESC
        """
        return self.execute_safe_query(query, {"teacher_id": teacher_id})
    
    def get_upload_history(self, teacher_id: int, limit: int = 10) -> List[Dict]:
        """Get recent upload history"""
        query = """
            SELECT 
                u.id,
                u.filename,
                u.uploaded_at,
                COUNT(DISTINCT a.id) as assignments_count,
                COUNT(DISTINCT g.id) as grades_count
            FROM uploads u
            LEFT JOIN assignments a ON u.id = a.upload_id
            LEFT JOIN grades g ON u.id = g.upload_id
            WHERE u.teacher_id = :teacher_id
            GROUP BY u.id, u.filename, u.uploaded_at
            ORDER BY u.uploaded_at DESC
            LIMIT :limit
        """
        return self.execute_safe_query(query, {
            "teacher_id": teacher_id,
            "limit": limit
        })

# ============================================================================
# Standalone testing
# ============================================================================
if __name__ == "__main__":
    print("Testing GradeInsight Database Connection...")
    
    try:
        db = GradeInsightDB()
        
        if db.test_connection():
            print("✓ Database connection successful!")
            
            # Test a query (use a valid teacher_id)
            teacher_id = int(input("Enter teacher ID to test: "))
            
            print(f"\n--- Testing struggling students query ---")
            struggling = db.get_struggling_students(teacher_id)
            print(f"Found {len(struggling)} struggling students")
            
            if struggling:
                print("\nFirst result:")
                print(json.dumps(struggling[0], indent=2, default=str))
            
            print(f"\n--- Testing class overview ---")
            overview = db.get_class_overview(teacher_id)
            print(json.dumps(overview, indent=2, default=str))
            
        else:
            print("✗ Connection test failed")
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
