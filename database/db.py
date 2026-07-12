import sqlite3
import re
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Dict, List, Tuple, Optional
import config

DB_PATH = Path(config.DATABASE_PATH)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

ALLOWED_TABLES = {"uploaded_data"}


def _validate_table_name(table_name: str) -> str:
    """Whitelist validation for table names."""
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: '{table_name}'. Allowed: {ALLOWED_TABLES}")
    return table_name


def _validate_column_name(col_name: str) -> bool:
    """Allow only safe column names."""
    return bool(re.match(r'^[a-zA-Z0-9_\s\-\.]+$', col_name))


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
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
    table_name = _validate_table_name(table_name)

    with get_db_connection() as conn:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        df.to_sql(table_name, conn, index=False, if_exists="replace")
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]

    print(f"[DATABASE] Stored {count} rows in '{table_name}'")
    return count


def get_table_schema(table_name: str = "uploaded_data") -> dict:
    table_name = _validate_table_name(table_name)

    with get_db_connection() as conn:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        if not columns:
            return {"table_name": table_name, "columns": [], "row_count": 0}

        schema = {
            "table_name": table_name,
            "columns": [
                {
                    "name": col[1],
                    "type": col[2],
                    "not_null": bool(col[3]),
                    "default": col[4],
                    "primary_key": bool(col[5])
                }
                for col in columns
            ],
            "row_count": 0
        }

        try:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            schema["row_count"] = cursor.fetchone()[0]
        except Exception as e:
            print(f"[DATABASE] Row count failed: {e}")

        return schema


def execute_query(sql: str) -> Tuple[bool, List[Dict], int]:
    """Execute a validated SQL query."""
    with get_db_connection() as conn:
        cursor = conn.execute(sql)

        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            return True, data, len(data)
        else:
            return True, [], 0


def get_sample_data(
    table_name: str = "uploaded_data",
    limit: int = 5
) -> List[Dict]:
    """Get sample rows from table."""
    table_name = _validate_table_name(table_name)
    limit = max(1, min(int(limit), 100))  # Clamp to [1, 100]

    with get_db_connection() as conn:
        cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))

        if not cursor.description:
            return []

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def get_column_stats(table_name: str = "uploaded_data") -> Dict:
    """Get per-column statistics."""
    table_name = _validate_table_name(table_name)

    with get_db_connection() as conn:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        all_columns = [col[1] for col in cursor.fetchall()]

        stats = {}
        for col in all_columns:
            if not _validate_column_name(col):
                print(f"[DATABASE] Skipping unsafe column name: '{col}'")
                continue

            try:
                # COUNT(*) - COUNT(col) correctly counts NULLs
                # because COUNT(col) ignores NULL values
                cursor = conn.execute(f"""
                    SELECT 
                        COUNT(*) AS total,
                        COUNT(DISTINCT "{col}") AS unique_count,
                        COUNT(*) - COUNT("{col}") AS null_count
                    FROM {table_name}
                """)
                row = cursor.fetchone()
                stats[col] = {
                    "total": row[0],
                    "unique_count": row[1],
                    "null_count": row[2]
                }
            except Exception as e:
                print(f"[DATABASE] Stats failed for column '{col}': {e}")
                stats[col] = {"total": 0, "unique_count": 0, "null_count": 0}

        return stats