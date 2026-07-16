import re
import time
from typing import Tuple, Dict, List
from database.db import execute_query

FORBIDDEN_KEYWORDS = [
    'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER',
    'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE'
]

ALLOWED_STATEMENTS = ['SELECT', 'WITH']


def validate_sql_query(sql: str) -> Tuple[bool, str]:
    """
    Validate SQL query for security and correctness.
    Single authoritative function - no wrapper aliases.
    """
    sql_upper = sql.upper().strip()

    print(f"[SQL] Validating query...")

    if not sql_upper:
        return False, "Empty SQL query"

    # Check for forbidden keywords using word boundaries
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + keyword + r'\b', sql_upper):
            print(f"[SQL] BLOCKED: Forbidden keyword '{keyword}'")
            return False, f"Forbidden keyword detected: {keyword}"

    # Must start with SELECT or WITH
    starts_with_allowed = any(
        sql_upper.startswith(stmt) for stmt in ALLOWED_STATEMENTS
    )
    if not starts_with_allowed:
        return False, f"Query must start with one of: {ALLOWED_STATEMENTS}"

    # Prevent multiple statements
    if sql_upper.count(';') > 1:
        return False, "Multiple statements not allowed"

    print(f"[SQL] Validation passed")
    return True, "Valid"


def execute_sql_query(sql: str) -> Dict:
    """Validate and execute a SQL query, returning structured result."""
    print(f"[SQL] Executing query...")
    start_time = time.time()

    try:
        is_valid, message = validate_sql_query(sql)
        if not is_valid:
            return {
                "success": False,
                "error": message,
                "data": [],
                "rows_returned": 0,
                "execution_time": 0
            }

        success, data, rows_returned = execute_query(sql)
        execution_time = time.time() - start_time

        if success:
            print(f"[SQL] Execution successful: {rows_returned} rows in {execution_time:.3f}s")
            return {
                "success": True,
                "data": data,
                "rows_returned": rows_returned,
                "execution_time": round(execution_time, 3)
            }
        else:
            print(f"[SQL] Execution failed")
            return {
                "success": False,
                "error": "Query execution failed",
                "data": [],
                "rows_returned": 0,
                "execution_time": 0
            }

    except Exception as e:
        execution_time = time.time() - start_time
        print(f"[SQL] Error: {str(e)}")
        return {
            "success": False,
            "error": f"Execution Error: {str(e)}",
            "data": [],
            "rows_returned": 0,
            "execution_time": round(execution_time, 3)
        }