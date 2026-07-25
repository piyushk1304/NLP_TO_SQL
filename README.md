# ⚡ NL2SQL — AI Data Analyst

> Ask questions about your data in plain English.  
> Get SQL, charts, and tables — powered by a local LLM. No cloud. No API keys.

![NL2SQL](https://img.shields.io/badge/NL2SQL-AI%20Data%20Analyst-3b82f6?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react&logoColor=black)
![SQLite](https://img.shields.io/badge/SQLite-WAL-003b57?style=for-the-badge&logo=sqlite&logoColor=white)
![Local LLM](https://img.shields.io/badge/LLM-Local%20Only-10b981?style=for-the-badge)

---

## What It Does

Upload any CSV or Excel file and start asking questions in plain English:

- *"What is the month-over-month sales growth rate?"*
- *"Which product category generates the most revenue?"*
- *"Show me the top 10 customers by total order value"*
- *"What is the average order value by region?"*

The system automatically:
1. Detects the KPI intent (growth rate, retention, churn, AOV, etc.)
2. Generates the correct SQL using a local LLM
3. Executes it safely against your data
4. Renders charts, tables, and an explanation

---
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                          NL2SQL — SYSTEM ARCHITECTURE                               ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND  (React 18)                                   │
│                           http://localhost:3000                                     │
│                                                                                     │
│  ┌──────────────┐    ┌────────────────────────────────────────────────────────┐    │
│  │   Sidebar    │    │                    Chat Area                           │    │
│  │              │    │                                                        │    │
│  │ ┌──────────┐ │    │  ┌─────────────┐  ┌──────────┐  ┌─────────────────┐  │    │
│  │ │  Schema  │ │    │  │ MessageBubble│  │SQL Viewer│  │  ChartRenderer  │  │    │
│  │ │ Explorer │ │    │  │             │  │          │  │                 │  │    │
│  │ └──────────┘ │    │  │ ┌─────────┐ │  │ Syntax   │  │ Bar/Line/Area   │  │    │
│  │              │    │  │ │Metrics  │ │  │ Highlight│  │ Pie/Scatter     │  │    │
│  │ ┌──────────┐ │    │  │ │Bar      │ │  │          │  │                 │  │    │
│  │ │ Sample   │ │    │  │ └─────────┘ │  └──────────┘  │ Zoom + JPEG     │  │    │
│  │ │Questions │ │    │  └─────────────┘                │ Export          │  │    │
│  │ └──────────┘ │    │                                  └─────────────────┘  │    │
│  │              │    │  ┌──────────────────────────────────────────────────┐  │    │
│  │ ┌──────────┐ │    │  │                  DataTable                      │  │    │
│  │ │ Actions  │ │    │  │     Sort · Paginate · CSV · Excel Download      │  │    │
│  │ │Clear/    │ │    │  └──────────────────────────────────────────────────┘  │    │
│  │ │Remove    │ │    │                                                        │    │
│  │ └──────────┘ │    │  ┌──────────────────────────────────────────────────┐  │    │
│  └──────────────┘    │  │                   InputBar                      │  │    │
│                       │  │         Auto-resize · Enter to Send             │  │    │
│  ┌──────────────┐    │  └──────────────────────────────────────────────────┘  │    │
│  │UploadModal   │    └────────────────────────────────────────────────────────┘    │
│  │Drag & Drop   │                                                                   │
│  │Progress Bar  │         State: useChat()  ←→  services/api.js  (Axios)           │
│  └──────────────┘                                                                   │
└──────────────────────────────────────────┬──────────────────────────────────────────┘
                                           │  HTTP / REST
                                           │  POST /api/ask
                                           │  POST /api/upload
                                           │  GET  /api/schema
                                           │  GET  /api/download/csv
                                           │  DELETE /api/data/clear
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                             BACKEND  (FastAPI)                                      │
│                           http://localhost:8000                                     │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                          API Layer  (router.py)                               │  │
│  │                                                                               │  │
│  │   upload_router   schema_router   ask_router   download_router   data_router  │  │
│  │      /upload         /schema        /ask         /download/*      /data/clear │  │
│  └───────────────────────────────┬───────────────────────────────────────────────┘  │
│                                  │                                                   │
│              ┌───────────────────┼───────────────────┐                              │
│              │                   │                   │                              │
│              ▼                   ▼                   ▼                              │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐              │
│  │   TTL + LRU       │  │   KPI Engine      │  │   File Handler    │              │
│  │   Cache           │  │   (engine.py)     │  │   (utils/file.py) │              │
│  │                   │  │                   │  │                   │              │
│  │ 100 entries       │  │ ┌───────────────┐ │  │ CSV / XLSX / XLS  │              │
│  │ 5 min TTL         │  │ │ KPI Detection │ │  │ Max 50 MB         │              │
│  │ Thread-safe       │  │ │               │ │  │ Column normalize  │              │
│  │ MD5 cache key     │  │ │ growth_rate   │ │  └───────────────────┘              │
│  │                   │  │ │ retention     │ │                                      │
│  │ HIT ──► return    │  │ │ churn         │ │                                      │
│  │ MISS──► process   │  │ │ aov           │ │                                      │
│  └───────────────────┘  │ │ running_total │ │                                      │
│                          │ └───────────────┘ │                                      │
│                          │                   │                                      │
│                          │ ┌───────────────┐ │                                      │
│                          │ │  Confidence   │ │                                      │
│                          │ │  Scoring      │ │                                      │
│                          │ │               │ │                                      │
│                          │ │ schema   25%  │ │                                      │
│                          │ │ semantic 20%  │ │                                      │
│                          │ │ kpi      25%  │ │                                      │
│                          │ │ sql      20%  │ │                                      │
│                          │ │ complex  10%  │ │                                      │
│                          │ └───────────────┘ │                                      │
│                          └────────┬──────────┘                                      │
│                                   │                                                  │
│                                   ▼                                                  │
│                          ┌───────────────────┐                                      │
│                          │   LLM Service     │                                      │
│                          │   (llm.py)        │                                      │
│                          │                   │                                      │
│                          │ Prompt Builder    │                                      │
│                          │ KPI Block inject  │                                      │
│                          │ Schema injection  │                                      │
│                          │                   │                                      │
│                          │ JSON Extraction:  │                                      │
│                          │ 1. Direct parse   │                                      │
│                          │ 2. Brace-match    │                                      │
│                          │ 3. Markdown block │                                      │
│                          │ 4. Regex fallback │                                      │
│                          └────────┬──────────┘                                      │
│                                   │  HTTP POST /completion                           │
│                                   │  timeout: 120s                                   │
│                                   ▼                                                  │
│                 ┌──────────────────────────────────────┐                            │
│                 │         SQL Layer  (sql.py)           │                            │
│                 │                                       │                            │
│                 │  validate_sql_query()                 │                            │
│                 │  ┌─────────────────────────────────┐ │                            │
│                 │  │ ✗ DROP / DELETE / INSERT        │ │                            │
│                 │  │ ✗ UPDATE / ALTER / TRUNCATE     │ │                            │
│                 │  │ ✓ SELECT only                   │ │                            │
│                 │  │ ✓ WITH (CTEs allowed)           │ │                            │
│                 │  └─────────────────────────────────┘ │                            │
│                 │                                       │                            │
│                 │  execute_sql_query()                  │                            │
│                 │  NaN / Inf → None cleaning            │                            │
│                 └──────────────┬────────────────────────┘                            │
│                                │                                                     │
│                                ▼                                                     │
│                 ┌──────────────────────────────────────┐                            │
│                 │         Database  (db.py)             │                            │
│                 │                                       │                            │
│                 │  SQLite — WAL mode                    │                            │
│                 │  ┌─────────────────────────────────┐ │                            │
│                 │  │  uploaded_data table            │ │                            │
│                 │  │                                 │ │                            │
│                 │  │  id   INTEGER PK                │ │                            │
│                 │  │  col1 TEXT/REAL/INTEGER         │ │                            │
│                 │  │  col2 TEXT/REAL/INTEGER         │ │                            │
│                 │  │  ...  (dynamic from CSV)        │ │                            │
│                 │  └─────────────────────────────────┘ │                            │
│                 │                                       │                            │
│                 │  Table whitelist validation           │                            │
│                 │  Column name sanitization             │                            │
│                 │  Fresh reset on every restart         │                            │
│                 └───────────────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │  HTTP POST /completion
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        LOCAL LLM  (llama.cpp server)                                │
│                           http://localhost:8080                                     │
│                                                                                     │
│   Model: Qwen / Mistral / LLaMA / Phi  (GGUF format)                               │
│                                                                                     │
│   Input : System prompt + schema + KPI block + user question                       │
│   Output: { "sql_query": "SELECT ...", "rationale": "..." }                        │
│                                                                                     │
│   temperature: 0.1   top_p: 0.9   n_predict: 2000   timeout: 120s                  │
└─────────────────────────────────────────────────────────────────────────────────────┘


╔══════════════════════════════════════════════════════════════════════════════════════╗
║                           REQUEST LIFECYCLE                                         ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

  User types question
        │
        ▼
  useChat.sendMessage()
        │
        ├── Add user bubble to chat
        ├── Add loading placeholder bubble
        │
        ▼
  POST /api/ask  { question: "..." }
        │
        ├──► Check TTL cache (MD5 key)
        │         │
        │    HIT  └──► return cached AskResponse  { cached: true }
        │
        │    MISS
        │         │
        │         ▼
        │    _require_data() — block if no file uploaded
        │         │
        │         ▼
        │    KPIService.detect_kpi_intent()
        │         │
        │         ▼
        │    LLMService.generate_sql()
        │         │
        │         └──► POST http://localhost:8080/completion
        │                   │
        │                   ▼
        │              Raw LLM text
        │                   │
        │                   ▼
        │         _extract_json() — 4 strategies
        │                   │
        │                   ▼
        │              sql_query + rationale
        │         │
        │         ▼
        │    validate_sql_query() — security check
        │         │
        │         ▼
        │    execute_sql_query() — run on SQLite
        │         │
        │         ▼
        │    clean_sql_results_for_json() — NaN/Inf safe
        │         │
        │         ▼
        │    calculate_confidence() — 0–100 score
        │         │
        │         ▼
        │    TTLCache.set() — store for 5 min
        │
        ▼
  AskResponse JSON
  {
    question, kpi_detected, sql_query,
    rationale, confidence_score,
    execution_time, rows_returned,
    data: [...], cached: false
  }
        │
        ▼
  MessageBubble renders
        │
        ├── MetricsBar   (KPI · confidence · rows · time · cached badge)
        ├── SQLViewer    (collapsible · syntax highlighted · copy button)
        ├── ChartRenderer(auto type · zoom · JPEG download)
        ├── DataTable    (sort · paginate · CSV/Excel export)
        └── Rationale    (LLM explanation text)
---

## Tech Stack

### Backend
| Component     | Technology                    |
|---------------|-------------------------------|
| API Framework | FastAPI                       |
| Database      | SQLite (WAL mode)             |
| LLM           | llama.cpp local HTTP server   |
| Data Layer    | Pandas + SQLAlchemy           |
| Caching       | Thread-safe TTL + LRU cache   |
| Validation    | Pydantic v2                   |

### Frontend
| Component     | Technology                    |
|---------------|-------------------------------|
| Framework     | React 18                      |
| Charts        | Recharts                      |
| HTTP Client   | Axios                         |
| Styling       | Pure CSS (design tokens)      |
| File Upload   | react-dropzone                |
| Notifications | react-hot-toast               |
| SQL Highlight | react-syntax-highlighter      |
| Chart Export  | html2canvas                   |

---
