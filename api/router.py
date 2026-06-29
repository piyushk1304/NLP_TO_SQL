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
import pandas as pd
import io
from typing import Any
import numpy as np

# Create separate routers for each section (in order)
upload_router = APIRouter(tags=["1. File Upload"])
schema_router = APIRouter(tags=["2. Schema Explorer"])
ask_router = APIRouter(tags=["3. Ask Question"])
download_router = APIRouter(tags=["4. Download Results"])
cache_router = APIRouter(tags=["5. Cache Management"])
info_router = APIRouter(tags=["6. System Info"])

kpi_service = KPIService()

# Global variable to store last query results in memory (NOT on disk)
LAST_QUERY_RESULT = {"data": [], "columns": []}

# Query Cache (in-memory)
QUERY_CACHE = {}
CACHE_TTL = 300  # 5 minutes cache

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
        except:
            return None
    
    if type(value).__name__ == 'NaT':
        return None
    
    if hasattr(value, 'item'):
        try:
            cleaned = value.item()
            if cleaned is None or (isinstance(cleaned, float) and (math.isnan(cleaned) or math.isinf(cleaned))):
                return None
            return cleaned
        except:
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
        if value == value:
            return str(value) if value is not None else None
        else:
            return None
    except:
        return None

def clean_dataframe_for_json(df: pd.DataFrame) -> list:
    df_clean = df.replace([np.inf, -np.inf], np.nan)
    records = df_clean.to_dict(orient="records")
    
    cleaned_records = []
    for record in records:
        cleaned_record = {}
        for key, value in record.items():
            cleaned_record[key] = clean_value(value)
        cleaned_records.append(cleaned_record)
    
    return cleaned_records

def clean_sql_results_for_json(data: list) -> list:
    cleaned_data = []
    for row in data:
        cleaned_row = {}
        for key, value in row.items():
            cleaned_row[key] = clean_value(value)
        cleaned_data.append(cleaned_row)
    return cleaned_data

# ─────────────────────────────────────────────────────────────
# 1. FILE UPLOAD SECTION
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
    
    try:
        file_path = save_uploaded_file(file, file.filename or "uploaded_data.csv")
        df = load_file_to_dataframe(file_path)
        
        if df.empty:
            print("[UPLOAD] Empty file")
            raise HTTPException(status_code=400, detail="Empty file")
        
        df_clean = df.replace([np.inf, -np.inf], np.nan)
        
        row_count = store_dataframe(df_clean, "uploaded_data")
        schema = get_table_schema("uploaded_data")
        columns = [col["name"] for col in schema["columns"]]
        
        sample_rows = clean_dataframe_for_json(df.head(5))
        
        print(f"[SCHEMA] Generated successfully: {len(columns)} columns, {row_count} rows")
        
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

# ─────────────────────────────────────────────────────────────
# 2. SCHEMA EXPLORER SECTION
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
# 3. ASK QUESTION SECTION
# ─────────────────────────────────────────────────────────────
@ask_router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a natural language question about your data."""
    print(f"\n{'='*60}")
    print(f"[ASK] Question received: {request.question}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # CHECK CACHE FIRST
    cache_key = hash(request.question)
    current_time = time.time()
    
    if cache_key in QUERY_CACHE:
        cached_result = QUERY_CACHE[cache_key]
        if current_time - cached_result["timestamp"] < CACHE_TTL:
            print(f"[CACHE] Hit! Returning cached result")
            cached_result["cached"] = True
            return AskResponse(**cached_result["data"])
        else:
            print(f"[CACHE] Expired. Removing from cache")
            del QUERY_CACHE[cache_key]
    
    try:
        schema = get_table_schema("uploaded_data")
        if not schema.get("columns"):
            print("[ASK] No data uploaded")
            raise HTTPException(
                status_code=400, 
                detail="No data uploaded. Please upload a file first."
            )
        
        engine_result = kpi_service.process_question(request.question, schema)
        
        if not engine_result["success"]:
            raise HTTPException(
                status_code=500, 
                detail=f"Processing failed: {engine_result.get('error', 'Unknown error')}"
            )
        
        sql_query = engine_result["sql_query"]
        
        execution_result = execute_sql_query(sql_query)
        
        if not execution_result["success"]:
            print(f"[ASK] Execution failed: {execution_result.get('error', 'Unknown error')}")
            raise HTTPException(
                status_code=400, 
                detail=f"SQL Execution failed: {execution_result.get('error', 'Unknown error')}"
            )
        
        cleaned_data = clean_sql_results_for_json(execution_result["data"])
        
        global LAST_QUERY_RESULT
        LAST_QUERY_RESULT = {
            "data": cleaned_data,
            "columns": list(cleaned_data[0].keys()) if cleaned_data else [],
            "timestamp": time.time()
        }
        
        execution_time = time.time() - start_time
        
        print(f"[EXECUTION TIME] {execution_time:.3f}s")
        print(f"[ROWS RETURNED] {execution_result['rows_returned']}")
        print(f"{'='*60}\n")
        
        # STORE IN CACHE
        response_data = {
            "question": request.question,
            "kpi_detected": engine_result["kpi_info"]["kpi_type"],
            "sql_query": sql_query,
            "rationale": engine_result["rationale"],
            "confidence_score": engine_result["confidence_score"],
            "execution_time": round(execution_time, 3),
            "rows_returned": execution_result["rows_returned"],
            "data": cleaned_data,
            "status": "success",
            "cached": False
        }
        
        QUERY_CACHE[cache_key] = {
            "data": response_data,
            "timestamp": current_time
        }
        
        print(f"[CACHE] Stored in cache (TTL: {CACHE_TTL}s)")
        
        return AskResponse(**response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ASK] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# ─────────────────────────────────────────────────────────────
# 4. DOWNLOAD RESULTS SECTION
# ─────────────────────────────────────────────────────────────
@download_router.get("/download/csv")
async def download_csv():
    """Download the last query result as CSV."""
    print(f"\n{'='*60}")
    print("[DOWNLOAD] CSV download requested")
    print(f"{'='*60}")
    
    try:
        if not LAST_QUERY_RESULT["data"]:
            raise HTTPException(
                status_code=404, 
                detail="No query results available. Please run a query first."
            )
        
        df = pd.DataFrame(LAST_QUERY_RESULT["data"])
        
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        
        csv_content = stream.getvalue()
        csv_bytes = csv_content.encode('utf-8')
        
        print(f"[DOWNLOAD] CSV generated in memory")
        print(f"[DOWNLOAD] Rows: {len(df)}")
        
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
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@download_router.get("/download/excel")
async def download_excel():
    """Download the last query result as Excel."""
    print(f"\n{'='*60}")
    print("[DOWNLOAD] Excel download requested")
    print(f"{'='*60}")
    
    try:
        if not LAST_QUERY_RESULT["data"]:
            raise HTTPException(
                status_code=404, 
                detail="No query results available. Please run a query first."
            )
        
        df = pd.DataFrame(LAST_QUERY_RESULT["data"])
        
        stream = io.BytesIO()
        df.to_excel(stream, index=False, engine='openpyxl')
        stream.seek(0)
        
        excel_bytes = stream.getvalue()
        
        print(f"[DOWNLOAD] Excel generated in memory")
        print(f"[DOWNLOAD] Rows: {len(df)}")
        
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
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

# ─────────────────────────────────────────────────────────────
# 5. CACHE MANAGEMENT SECTION
# ─────────────────────────────────────────────────────────────
@cache_router.get("/cache/stats")
async def get_cache_stats():
    """Get query cache statistics."""
    current_time = time.time()
    active_cache = {k: v for k, v in QUERY_CACHE.items() 
                    if current_time - v["timestamp"] < CACHE_TTL}
    
    return {
        "total_cached_queries": len(active_cache),
        "cache_ttl_seconds": CACHE_TTL,
        "max_cache_size": len(QUERY_CACHE)
    }

@cache_router.delete("/cache/clear")
async def clear_cache():
    """Clear all query cache."""
    global QUERY_CACHE
    QUERY_CACHE = {}
    print("[CACHE] Cache cleared")
    return {"message": "Cache cleared successfully", "cleared_count": 0}

# ─────────────────────────────────────────────────────────────
# 6. SYSTEM INFO SECTION
# ─────────────────────────────────────────────────────────────
@info_router.get("/")
async def root():
    """System information and available endpoints."""
    return {
        "message": "NLP → SQL Backend System",
        "version": "1.0.0",
        "docs": "/docs",
        "workflow": [
            "Step 1: POST /api/upload - Upload your CSV/Excel file",
            "Step 2: GET /api/schema - View available columns",
            "Step 3: POST /api/ask - Ask questions about your data",
            "Step 4: GET /api/download/csv - Download results as CSV",
            "Step 5: GET /api/download/excel - Download results as Excel"
        ],
        "endpoints": [
            "POST /api/upload - Upload CSV/Excel file",
            "GET /api/schema - Get database schema",
            "POST /api/ask - Ask natural language question",
            "GET /api/download/csv - Download results as CSV",
            "GET /api/download/excel - Download results as Excel",
            "GET /api/cache/stats - Get cache statistics",
            "DELETE /api/cache/clear - Clear query cache",
            "GET /health - Health check"
        ]
    }

@info_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}