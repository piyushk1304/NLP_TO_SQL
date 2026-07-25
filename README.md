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
┌─────────────────────────────────────────────────────────┐
│ Sidebar │ Chat Area │
│ ───────────────── │ ─────────────────────────────── │
│ Schema Explorer │ [User] What is sales growth? │
│ • order_date TEXT │ │
│ • sales REAL │ [AI] ───────────────────────── │
│ • customer TEXT │ KPI: growth_rate | 87% conf │
│ • region TEXT │ ───────────────────────────── │
│ │ ▶ Generated SQL │
│ Try asking: │ 📊 Area Chart (auto) │
│ › Sales growth │ 📋 Data Table (sortable) │
│ › Top customers │ 💬 Rationale │
│ › By region │ │
└─────────────────────────────────────────────────────────┘
