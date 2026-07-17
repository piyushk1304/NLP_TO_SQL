from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class UploadResponse(BaseModel):
    table_name: str
    rows: int
    columns: List[str]
    sample_rows: List[Dict[str, Any]]
    status: str = "success"

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

class AskResponse(BaseModel):
    question: str
    kpi_detected: str
    sql_query: str
    rationale: str
    confidence_score: float
    execution_time: float
    rows_returned: int
    data: List[Dict[str, Any]]
    status: str = "success"

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    detail: Optional[str] = None