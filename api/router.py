from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response 
from fastapi.responses import StreamingResponse
from models.schemas import UploadResponse, AskRequest, AskResponse, ErrorResponse
from utils.file import save_uploaded_file, load_file_to_dataframe, validate_file
from database.db import store_dataframe, get_table_schema, execute_query
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

# Create separate routers for each section
upload_router = APIRouter(tags=["File Upload"])
ask_router = APIRouter(tags=["Ask Question"])
download_router = APIRouter(tags=["Download Results"])
info_router = APIRouter(tags=["System Info"])

kpi_service = KPIService()
LAST_QUERY_RESULT = {"data": [], "columns": []}

# Global variable to store last query results in memory (NOT on disk)
LAST_QUERY_RESULT = {"data": [], "columns": []}

def clean_value(value: Any) -> Any:
    """
    Clean values for JSON serialization.
    Handles: NaN, NaT, Inf, -Inf, None, and other non-serializable types
    """
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
# FILE UPLOAD SECTION
# ─────────────────────────────────────────────────────────────
@upload_router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a CSV or Excel file to be analyzed.
    
    - **File Types**: CSV, XLSX, XLS
    - **Max Size**: 50 MB
    - **Storage**: SQLite database (uploaded_data table)
    """
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
# ASK QUESTION SECTION
# ─────────────────────────────────────────────────────────────
@ask_router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Ask a natural language question about your data.
    
    - **Input**: Natural language question
    - **Output**: SQL query + results + confidence score
    - **KPI Support**: Growth Rate, Retention, Churn, AOV, Running Total
    """
    print(f"\n{'='*60}")
    print(f"[ASK] Question received: {request.question}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
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
        
        return AskResponse(
            question=request.question,
            kpi_detected=engine_result["kpi_info"]["kpi_type"],
            sql_query=sql_query,
            rationale=engine_result["rationale"],
            confidence_score=engine_result["confidence_score"],
            execution_time=round(execution_time, 3),
            rows_returned=execution_result["rows_returned"],
            data=cleaned_data,
            status="success"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ASK] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# ─────────────────────────────────────────────────────────────
# DOWNLOAD RESULTS SECTION
# ─────────────────────────────────────────────────────────────
@download_router.get("/download/csv")
async def download_csv():
    """Download the last query result as CSV."""
    print(f"\n{'='*60}")
    print("[DOWNLOAD] CSV download requested")
    print(f"{'='*60}")
    
    try:
        if not LAST_QUERY_RESULT["data"]:
            raise HTTPException(status_code=404, detail="No query results available. Please run a query first.")
        
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
            raise HTTPException(status_code=404, detail="No query results available. Please run a query first.")
        
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
# SYSTEM INFO SECTION
# ─────────────────────────────────────────────────────────────
@info_router.get("/")
async def root():
    """
    System information and available endpoints.
    """
    return {
        "message": "NLP → SQL Backend System",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "POST /api/upload - Upload CSV/Excel file",
            "POST /api/ask - Ask natural language question",
            "GET /api/download/csv - Download results as CSV",
            "GET /api/download/excel - Download results as Excel"
        ]
    }

@info_router.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy", "timestamp": time.time()}