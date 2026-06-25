import pandas as pd
from pathlib import Path
from typing import Tuple
import config

UPLOAD_FOLDER = Path(config.UPLOAD_FOLDER)
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

def save_uploaded_file(file, filename: str) -> Path:
    file_path = UPLOAD_FOLDER / filename
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())  # Use file.file.read() instead of file.read()
    print(f"[UPLOAD] File saved: {file_path}")
    return file_path

def load_file_to_dataframe(file_path: Path) -> pd.DataFrame:
    print(f"[UPLOAD] Loading file: {file_path}")
    
    if file_path.suffix.lower() == '.csv':
        df = pd.read_csv(file_path)
    elif file_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")
    
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    print(f"[UPLOAD] Loaded {len(df)} rows, {len(df.columns)} columns")
    return df

def validate_file(file, max_size_mb: int = None) -> Tuple[bool, str]:
    if max_size_mb is None:
        max_size_mb = config.MAX_FILE_SIZE_MB
    
    filename = file.filename or ""
    ext = filename.split(".")[-1].lower()
    
    allowed_extensions = ['csv', 'xlsx', 'xls']
    if ext not in allowed_extensions:
        return False, f"File type {ext} not allowed. Allowed: {allowed_extensions}"
    
    # Fix: Use file.file.seek() for UploadFile object
    try:
        file.file.seek(0, 2)  # Seek to end
        size_bytes = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        size_mb = size_bytes / (1024 * 1024)
        
        if size_mb > max_size_mb:
            return False, f"File size {size_mb:.2f}MB exceeds limit {max_size_mb}MB"
    except Exception as e:
        print(f"[UPLOAD] Size check error: {str(e)}")
        # Continue without size validation if seek fails
    
    return True, "Valid"