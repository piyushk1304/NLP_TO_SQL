from dotenv import load_dotenv
import os

load_dotenv()

# LLM Configuration (Local Only)
LLM_PROVIDER = "local"
LLM_API_URL = os.environ.get("LLM_API_URL", "http://127.0.0.1:8080")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-3.5")

# Database & Upload
DATABASE_PATH = os.environ.get("DATABASE_PATH", "./nl2sql.db")
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "./uploads")
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "50"))