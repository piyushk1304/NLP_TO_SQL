from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from models.schemas import UploadResponse, AskRequest, AskResponse, ErrorResponse
from utils.file import save_uploaded_file, load_file_to_dataframe, validate_file
from database.db import store_dataframe, get_table_schema, execute_query, get_sample_data, get_column_stats
from core.engine import KPIService
from core.sql import execute_sql_query
import config
import os
import time
import math
import threading
import pandas as pd
import io
from typing import Any, Dict, Optional
from collections import OrderedDict
import numpy as np

# ─────────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────────
upload_router   = APIRouter(tags=["1. File Upload"])
schema_router   = APIRouter(tags=["2. Schema Explorer"])
ask_router      = APIRouter(tags=["3. Ask Question"])
download_router = APIRouter(tags=["4. Download Results"])
cache_router    = APIRouter(tags=["5. Cache Management"])
info_router     = APIRouter(tags=["6. System Info"])

kpi_service = KPIService()

# ─────────────────────────────────────────────────────────────
# THREAD-SAFE LAST QUERY RESULT STORE
# ─────────────────────────────────────────────────────────────
_result_lock = threading.Lock()
LAST_QUERY_RESULT: Dict = {"data": [], "columns": [], "timestamp": 0}


def _set_last_result(data: list, columns: list) -> None:
    """Thread-safe setter for last query result."""
    global LAST_QUERY_RESULT
    with _result_lock:
        LAST_QUERY_RESULT = {
            "data": data,
            "columns": columns,
            "timestamp": time.time()
        }


def _get_last_result() -> Dict:
    """Thread-safe getter for last query result."""
    with _result_lock:
        return dict(LAST_QUERY_RESULT)


# ─────────────────────────────────────────────────────────────
# THREAD-SAFE LRU CACHE WITH TTL
# ─────────────────────────────────────────────────────────────
class TTLCache:
    """Thread-safe LRU cache with TTL expiration."""

    def __init__(self, maxsize: int = 100, ttl: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key) -> Optional[Dict]:
        """Return cached value or None if missing/expired."""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() - entry["timestamp"] > self.ttl:
                del self._cache[key]
                print(f"[CACHE] Entry expired and removed")
                return None

            # Move to end = most recently used
            self._cache.move_to_end(key)
            return entry["data"]

    def set(self, key, value: Dict) -> None:
        """Store value in cache, evicting oldest entry if at capacity."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)

            self._cache[key] = {
                "data": value,
                "timestamp": time.time()
            }

            # Evict oldest entries if over capacity
            while len(self._cache) > self.maxsize:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                print(f"[CACHE] Evicted oldest entry (capacity={self.maxsize})")

    def clear(self) -> int:
        """Clear all entries, return count of cleared items."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def stats(self) -> Dict:
        """Return cache statistics."""
        with self._lock:
            current_time = time.time()
            active = sum(
                1 for v in self._cache.values()
                if current_time - v["timestamp"] < self.ttl
            )
            expired = len(self._cache) - active
            return {
                "total_entries": len(self._cache),
                "active_entries": active,
                "expired_entries": expired,
                "ttl_seconds": self.ttl,
                "max_size": self.maxsize
            }


QUERY_CACHE = TTLCache(maxsize=100, ttl=300)


# ─────────────────────────────────────────────────────────────
# JSON SERIALIZATION HELPERS
# ─────────────────────────────────────────────────────────────
def clean_value(value: Any) -> Any:
    """Clean values for JSON serialization."""
    if value is None:
        return None

    try:
        if isinstance(value, (float, np.floating)):
            if math.isnan(value) or math.isinf(value):
                return None
            return float(value)
    except (TypeError, ValueError):
        pass

    try:
        if isinstance(value, (int, np.integer)):
            return int(value)
    except (TypeError, ValueError):
        pass

    if hasattr(value, 'to_pydatetime'):
        try:
            return str(value)
        except Exception:
            return None

    if type(value).__name__ == 'NaT':
        return None

    if hasattr(value, 'item'):
        try:
            cleaned = value.item()
            if cleaned is None or (
                isinstance(cleaned, float) and (math.isnan(cleaned) or math.isinf(cleaned))
            ):
                return None
            return cleaned
        except Exception:
            return None

    if isinstance(value, str):
        if value.lower() in ['nan', 'na', 'n/a', 'null', 'none', '']:
            return None
        return value

    if isinstance(value, bool):
        return value

    if isinstance(value, (list, dict)):
        return value

    try:
        # NaN != NaN is True in Python
        if value == value:
            return str(value) if value is not None else None
        else:
            return None
    except Exception:
        return None


def clean_dataframe_for_json(df: pd.DataFrame) -> list:
    """Convert DataFrame to JSON-safe list of dicts."""
    df_clean = df.replace([np.inf, -np.inf], np.nan)
    records = df_clean.to_dict(orient="records")

    cleaned_records = []
    for record in records:
        cleaned_record = {key: clean_value(val) for key, val in record.items()}
        cleaned_records.append(cleaned_record)

    return cleaned_records


def clean_sql_results_for_json(data: list) -> list:
    """Clean raw SQL result rows for JSON serialization."""
    return [
        {key: clean_value(val) for key, val in row.items()}
        for row in data
    ]


# ─────────────────────────────────────────────────────────────
# 1. FILE UPLOAD
# ─────────────────────────────────────────────────────────────
@upload_router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a CSV or Excel file to be analyzed."""
    print(f"\n{'='*60}")
    print("[UPLOAD] File received")
    print(f"{'='*60}")

    is_valid, message = validate_file(file, config.MAX_FILE_SIZE_MB)
    if not is_valid:
        print(f"[UPLOAD] Validation failed: {message}")
        raise HTTPException(status_code=400, detail=message)

    file_path = None
    try:
        file_path = save_uploaded_file(file, file.filename or "uploaded_data.csv")
        df = load_file_to_dataframe(file_path)

        if df.empty:
            print("[UPLOAD] Empty file")
            raise HTTPException(status_code=400, detail="Uploaded file contains no data")

        df_clean = df.replace([np.inf, -np.inf], np.nan)
        row_count = store_dataframe(df_clean, "uploaded_data")
        schema = get_table_schema("uploaded_data")
        columns = [col["name"] for col in schema["columns"]]
        sample_rows = clean_dataframe_for_json(df.head(5))

        print(f"[UPLOAD] Success: {len(columns)} columns, {row_count} rows")

        return UploadResponse(
            table_name="uploaded_data",
            rows=row_count,
            columns=columns,
            sample_rows=sample_rows,
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPLOAD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        # Always remove temp file from disk
        if file_path is not None and file_path.exists():
            try:
                file_path.unlink()
                print(f"[UPLOAD] Temp file removed: {file_path}")
            except Exception as cleanup_err:
                print(f"[UPLOAD] Cleanup warning: {cleanup_err}")


# ─────────────────────────────────────────────────────────────
# 2. SCHEMA EXPLORER
# ─────────────────────────────────────────────────────────────
@schema_router.get("/schema")
async def get_schema():
    """Get database schema information (available columns, stats, sample data)."""
    print(f"\n{'='*60}")
    print("[SCHEMA] Schema request received")
    print(f"{'='*60}")

    try:
        schema = get_table_schema("uploaded_data")

        if not schema.get("columns"):
            raise HTTPException(
                status_code=404,
                detail="No data uploaded. Please upload a file first."
            )

        sample_data = get_sample_data(limit=3)
        column_stats = get_column_stats()

        print(f"[SCHEMA] Returning {len(schema['columns'])} columns")

        return {
            "table_name": schema["table_name"],
            "row_count": schema["row_count"],
            "columns": schema["columns"],
            "column_names": [col["name"] for col in schema["columns"]],
            "sample_data": sample_data,
            "column_stats": column_stats
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SCHEMA] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema fetch failed: {str(e)}")


# ─────────────────────────────────────────────────────────────
# 3. ASK QUESTION
# ─────────────────────────────────────────────────────────────
@ask_router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a natural language question about your data."""
    print(f"\n{'='*60}")
    print(f"[ASK] Question: {request.question}")
    print(f"{'='*60}")

    start_time = time.time()
    cache_key = hash(request.question)

    # ── Cache hit ──────────────────────────────────────────────────────────────
    cached = QUERY_CACHE.get(cache_key)
    if cached is not None:
        print(f"[CACHE] Hit! Returning cached result")
        cached_copy = dict(cached)
        cached_copy["cached"] = True
        return AskResponse(**cached_copy)

    print(f"[CACHE] Miss. Processing question...")

    try:
        schema = get_table_schema("uploaded_data")
        if not schema.get("columns"):
            raise HTTPException(
                status_code=400,
                detail="No data uploaded. Please upload a file first."
            )

        # ── KPI detection + SQL generation ────────────────────────────────────
        engine_result = kpi_service.process_question(request.question, schema)

        if not engine_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {engine_result.get('error', 'Unknown error')}"
            )

        sql_query = engine_result["sql_query"]

        # ── SQL execution ──────────────────────────────────────────────────────
        execution_result = execute_sql_query(sql_query)

        if not execution_result["success"]:
            print(f"[ASK] Execution failed: {execution_result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=400,
                detail=f"SQL Execution failed: {execution_result.get('error', 'Unknown error')}"
            )

        cleaned_data = clean_sql_results_for_json(execution_result["data"])

        # ── Store last result (thread-safe) ────────────────────────────────────
        _set_last_result(
            data=cleaned_data,
            columns=list(cleaned_data[0].keys()) if cleaned_data else []
        )

        execution_time = round(time.time() - start_time, 3)

        print(f"[ASK] Execution time: {execution_time}s")
        print(f"[ASK] Rows returned: {execution_result['rows_returned']}")
        print(f"{'='*60}\n")

        # ── Build response dict ────────────────────────────────────────────────
        response_data = {
            "question":         request.question,
            "kpi_detected":     engine_result["kpi_info"]["kpi_type"],
            "sql_query":        sql_query,
            "rationale":        engine_result["rationale"],
            "confidence_score": engine_result["confidence_score"],
            "execution_time":   execution_time,
            "rows_returned":    execution_result["rows_returned"],
            "data":             cleaned_data,
            "status":           "success",
            "cached":           False
        }

        # ── Store in cache ─────────────────────────────────────────────────────
        QUERY_CACHE.set(cache_key, response_data)
        print(f"[CACHE] Stored in cache (TTL: {QUERY_CACHE.ttl}s)")

        return AskResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ASK] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ─────────────────────────────────────────────────────────────
# 4. DOWNLOAD RESULTS
# ─────────────────────────────────────────────────────────────
@download_router.get("/download/csv")
async def download_csv():
    """Download the last query result as CSV."""
    print(f"\n{'='*60}")
    print("[DOWNLOAD] CSV download requested")
    print(f"{'='*60}")

    try:
        result = _get_last_result()

        if not result["data"]:
            raise HTTPException(
                status_code=404,
                detail="No query results available. Please run a query first."
            )

        df = pd.DataFrame(result["data"])

        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)

        csv_bytes = stream.getvalue().encode('utf-8')

        print(f"[DOWNLOAD] CSV generated in memory — {len(df)} rows")

        return Response(
            content=csv_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=query_result.csv",
                "Content-Length": str(len(csv_bytes)),
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOWNLOAD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"CSV download failed: {str(e)}")


@download_router.get("/download/excel")
async def download_excel():
    """Download the last query result as Excel."""
    print(f"\n{'='*60}")
    print("[DOWNLOAD] Excel download requested")
    print(f"{'='*60}")

    try:
        result = _get_last_result()

        if not result["data"]:
            raise HTTPException(
                status_code=404,
                detail="No query results available. Please run a query first."
            )

        df = pd.DataFrame(result["data"])

        stream = io.BytesIO()
        df.to_excel(stream, index=False, engine='openpyxl')
        stream.seek(0)

        excel_bytes = stream.getvalue()

        print(f"[DOWNLOAD] Excel generated in memory — {len(df)} rows")

        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=query_result.xlsx",
                "Content-Length": str(len(excel_bytes)),
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[DOWNLOAD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Excel download failed: {str(e)}")


# ─────────────────────────────────────────────────────────────
# 5. CACHE MANAGEMENT
# ─────────────────────────────────────────────────────────────
@cache_router.get("/cache/stats")
async def get_cache_stats():
    """Get query cache statistics."""
    return QUERY_CACHE.stats()


@cache_router.delete("/cache/clear")
async def clear_cache():
    """Clear all query cache entries."""
    count = QUERY_CACHE.clear()
    print(f"[CACHE] Cleared {count} entries")
    return {"message": "Cache cleared successfully", "cleared_count": count}


# ─────────────────────────────────────────────────────────────
# 6. SYSTEM INFO
# ─────────────────────────────────────────────────────────────
@info_router.get("/")
async def root():
    """System information and available endpoints."""
    return {
        "message": "NLP → SQL Backend System",
        "version": "1.0.0",
        "docs": "/docs",
        "workflow": [
            "Step 1: POST /api/upload  — Upload your CSV/Excel file",
            "Step 2: GET  /api/schema  — View available columns",
            "Step 3: POST /api/ask     — Ask questions about your data",
            "Step 4: GET  /api/download/csv   — Download results as CSV",
            "Step 5: GET  /api/download/excel — Download results as Excel"
        ],
        "endpoints": [
            "POST   /api/upload          — Upload CSV/Excel file",
            "GET    /api/schema          — Get database schema",
            "POST   /api/ask             — Ask natural language question",
            "GET    /api/download/csv    — Download results as CSV",
            "GET    /api/download/excel  — Download results as Excel",
            "GET    /api/cache/stats     — Get cache statistics",
            "DELETE /api/cache/clear     — Clear query cache",
            "GET    /health              — Health check"
        ]
    }


@info_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}