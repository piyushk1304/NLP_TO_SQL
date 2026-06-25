import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
import config

DB_PATH = Path(config.DATABASE_PATH)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_database() -> None:
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
        """)
    print("[DATABASE] SQLite initialized successfully")

def store_dataframe(df, table_name: str = "uploaded_data") -> int:
    with get_db_connection() as conn:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        df.to_sql(table_name, conn, index=False, if_exists="replace")
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
    return count

def get_table_schema(table_name: str = "uploaded_data") -> dict:
    with get_db_connection() as conn:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            return {"columns": [], "row_count": 0}
        
        schema = {
            "table_name": table_name,
            "columns": [
                {"name": col[1], "type": col[2], "not_null": bool(col[3])}
                for col in columns
            ],
            "row_count": 0
        }
        
        try:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            schema["row_count"] = cursor.fetchone()[0]
        except:
            pass
        
        return schema

def execute_query(sql: str) -> tuple:
    with get_db_connection() as conn:
        cursor = conn.execute(sql)
        
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            return True, data, len(data)
        else:
            return True, [], 0