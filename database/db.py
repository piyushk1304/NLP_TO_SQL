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
        raise ValueError(
            f"Invalid table name: '{table_name}'. "
            f"Allowed: {ALLOWED_TABLES}"
        )
    return table_name


def _validate_column_name(col_name: str) -> bool:
    """Allow only safe column names."""
    return bool(re.match(r'^[a-zA-Z0-9_\s\-\.]+$', col_name))


def _is_skeleton_table(col_names: list) -> bool:
    """
    Returns True if the table only has the auto-created 'id' column,
    meaning no real data has been uploaded yet.
    """
    return not col_names or col_names == ["id"]


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
    """
    Initialize DB on every startup — always starts fresh.
    Drops any existing uploaded data so each server start is clean.
    Users must re-upload their file after restarting the server.
    """
    with get_db_connection() as conn:
        # ── Always drop and recreate skeleton ────────────────────────
        conn.execute("DROP TABLE IF EXISTS uploaded_data")
        conn.execute("""
            CREATE TABLE uploaded_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            )
        """)
    print("[DATABASE] SQLite initialized — fresh start (previous data cleared)")


def store_dataframe(df, table_name: str = "uploaded_data") -> int:
    """Drop existing table and store new dataframe."""
    table_name = _validate_table_name(table_name)

    with get_db_connection() as conn:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        df.to_sql(table_name, conn, index=False, if_exists="replace")
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        count  = cursor.fetchone()[0]

    print(f"[DATABASE] Stored {count} rows in '{table_name}'")
    return count


def get_table_schema(table_name: str = "uploaded_data") -> dict:
    """
    Return schema for the given table.
    Returns empty columns list if table is skeleton (no real data).
    """
    table_name = _validate_table_name(table_name)

    with get_db_connection() as conn:
        cursor  = conn.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        # Table does not exist at all
        if not columns:
            return {
                "table_name": table_name,
                "columns":    [],
                "row_count":  0
            }

        col_list = [
            {
                "name":        col[1],
                "type":        col[2],
                "not_null":    bool(col[3]),
                "default":     col[4],
                "primary_key": bool(col[5])
            }
            for col in columns
        ]

        col_names = [c["name"] for c in col_list]

        # ── Skeleton table — only id column, no real data ─────────────
        if _is_skeleton_table(col_names):
            print("[DATABASE] Skeleton table — no real data uploaded yet")
            return {
                "table_name": table_name,
                "columns":    [],
                "row_count":  0
            }

        # ── Real data — get row count ──────────────────────────────────
        row_count = 0
        try:
            cursor    = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
        except Exception as e:
            print(f"[DATABASE] Row count failed: {e}")

        return {
            "table_name": table_name,
            "columns":    col_list,
            "row_count":  row_count
        }


def execute_query(sql: str) -> Tuple[bool, List[Dict], int]:
    """Execute a validated SQL query and return results."""
    with get_db_connection() as conn:
        cursor = conn.execute(sql)

        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows    = cursor.fetchall()
            data    = [dict(zip(columns, row)) for row in rows]
            return True, data, len(data)
        else:
            return True, [], 0


def get_sample_data(
    table_name: str = "uploaded_data",
    limit: int = 5
) -> List[Dict]:
    """
    Get sample rows from table.
    Returns empty list for skeleton table.
    """
    table_name = _validate_table_name(table_name)
    limit      = max(1, min(int(limit), 100))

    with get_db_connection() as conn:
        # Check for skeleton table first
        cursor       = conn.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        col_names    = [col[1] for col in columns_info]

        if _is_skeleton_table(col_names):
            return []

        cursor = conn.execute(
            f"SELECT * FROM {table_name} LIMIT ?", (limit,)
        )

        if not cursor.description:
            return []

        columns = [desc[0] for desc in cursor.description]
        rows    = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def get_column_stats(table_name: str = "uploaded_data") -> Dict:
    """
    Get per-column statistics (total, unique_count, null_count).
    Returns empty dict for skeleton table.
    """
    table_name = _validate_table_name(table_name)

    with get_db_connection() as conn:
        cursor      = conn.execute(f"PRAGMA table_info({table_name})")
        all_columns = cursor.fetchall()
        col_names   = [col[1] for col in all_columns]

        # Skip skeleton table
        if _is_skeleton_table(col_names):
            return {}

        stats = {}
        for col in col_names:
            if not _validate_column_name(col):
                print(f"[DATABASE] Skipping unsafe column: '{col}'")
                continue

            try:
                cursor = conn.execute(f"""
                    SELECT
                        COUNT(*)                  AS total,
                        COUNT(DISTINCT "{col}")   AS unique_count,
                        COUNT(*) - COUNT("{col}") AS null_count
                    FROM {table_name}
                """)
                row        = cursor.fetchone()
                stats[col] = {
                    "total":        row[0],
                    "unique_count": row[1],
                    "null_count":   row[2]
                }
            except Exception as e:
                print(f"[DATABASE] Stats failed for '{col}': {e}")
                stats[col] = {
                    "total":        0,
                    "unique_count": 0,
                    "null_count":   0
                }

        return stats