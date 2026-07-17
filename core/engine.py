import json
import re
from typing import Dict, List
from core.llm import LLMService
from core.sql import validate_sql_query

# KPI Registry
KPI_REGISTRY = {
    "growth_rate": {
        "keywords": ["growth", "increase", "change over time", "mom", "yoy", "trend", "rate"],
        "logic_hint": "Use LAG() window function to compare current period vs previous period. Formula: (Current - Previous) / Previous * 100. Group by time period (month/year).",
        "sql_pattern": "WITH period_data AS (...) SELECT ..., (val - LAG(val) OVER (...)) / LAG(val) OVER (...) * 100 AS growth_rate"
    },
    "retention_rate": {
        "keywords": ["retention", "returning customers", "returned", "repeat"],
        "logic_hint": "Identify first purchase date per customer. Count customers who purchased again after that date. Formula: Returning Customers / Total Customers * 100.",
        "sql_pattern": "WITH first_purchase AS (...), repeat_customers AS (...) SELECT COUNT(*) FROM repeat_customers / COUNT(*) FROM total"
    },
    "churn_rate": {
        "keywords": ["churn", "lost customers", "attrition", "inactive"],
        "logic_hint": "Identify active customers vs those who haven't purchased in specific timeframe. Formula: (1 - Returning/Active) * 100.",
        "sql_pattern": "WITH active AS (...), inactive AS (...) SELECT (1 - COUNT(inactive)/COUNT(active)) * 100"
    },
    "aov": {
        "keywords": ["average order value", "aov", "avg basket", "average transaction"],
        "logic_hint": "Total Revenue divided by Count of Distinct Orders. Formula: SUM(sales) / COUNT(DISTINCT order_id).",
        "sql_pattern": "SELECT SUM(sales_amount) / COUNT(DISTINCT order_id) AS aov"
    },
    "running_total": {
        "keywords": ["running total", "cumulative", "running sum", "cumulative sum"],
        "logic_hint": "Use SUM() OVER (ORDER BY date) window function for cumulative calculations.",
        "sql_pattern": "SELECT date, amount, SUM(amount) OVER (ORDER BY date) AS running_total"
    },
    "none": {
        "keywords": [],
        "logic_hint": "Standard SQL aggregation. No special KPI logic required.",
        "sql_pattern": "SELECT ..."
    }
}

# Semantic Mapping
SEMANTIC_MAPPING = {
    "sales": ["revenue", "turnover", "income", "amount", "sales_amount", "total"],
    "customer": ["client", "buyer", "user", "customer_name", "customer_id"],
    "order": ["purchase", "transaction", "order_id", "order_number"],
    "date": ["time", "period", "order_date", "created_at", "timestamp"],
    "product": ["item", "goods", "product_name", "product_id"],
    "quantity": ["qty", "count", "units", "amount"],
    "price": ["cost", "unit_price", "price_per_unit"],
    "region": ["area", "location", "country", "state", "city"],
    "category": ["type", "class", "product_category", "segment"]
}

class KPIService:
    def __init__(self):
        self.llm_service = LLMService()
        print("[ENGINE] KPI Engine initialized")
    
    def detect_kpi_intent(self, question: str) -> Dict:
        q_lower = question.lower()
        
        for kpi, data in KPI_REGISTRY.items():
            if kpi == "none":
                continue
            if any(kw in q_lower for kw in data["keywords"]):
                print(f"[KPI] {kpi} detected")
                return {
                    "kpi_type": kpi,
                    "confidence": 80,
                    "reasoning": "Keyword match",
                    "definition": data
                }
        
        print(f"[KPI] No KPI detected (standard query)")
        return {
            "kpi_type": "none",
            "confidence": 90,
            "reasoning": "No KPI keywords found",
            "definition": KPI_REGISTRY["none"]
        }
    
    def get_semantic_mapping(self) -> Dict:
        return SEMANTIC_MAPPING
    
    def calculate_confidence(self, question: str, sql_query: str, schema: Dict, 
                             kpi_info: Dict) -> float:
        scores = {
            "schema_match": 0,
            "semantic_mapping": 0,
            "kpi_accuracy": 0,
            "sql_validity": 0,
            "complexity_handling": 0
        }
        
        weights = {
            "schema_match": 0.25,
            "semantic_mapping": 0.20,
            "kpi_accuracy": 0.25,
            "sql_validity": 0.20,
            "complexity_handling": 0.10
        }
        
        schema_columns = [col["name"].lower() for col in schema.get("columns", [])]
        
        scores["schema_match"] = self._check_schema_match(sql_query, schema_columns)
        scores["semantic_mapping"] = self._check_semantic_mapping(question)
        scores["kpi_accuracy"] = self._check_kpi_accuracy(kpi_info, sql_query)
        scores["sql_validity"] = self._check_sql_validity(sql_query)
        scores["complexity_handling"] = self._check_complexity(sql_query)
        
        total_score = sum(scores[key] * weights[key] for key in scores)
        
        print(f"[CONFIDENCE] Score: {total_score:.2f}")
        return round(min(100, max(0, total_score)), 2)
    
    def _check_schema_match(self, sql_query: str, schema_columns: List[str]) -> float:
        sql_lower = sql_query.lower()
        matches = sum(1 for col in schema_columns if col in sql_lower)
        return (matches / max(len(schema_columns), 1)) * 100
    
    def _check_semantic_mapping(self, question: str) -> float:
        q_lower = question.lower()
        matches = 0
        for key, aliases in SEMANTIC_MAPPING.items():
            if key in q_lower or any(alias in q_lower for alias in aliases):
                matches += 1
        return (matches / max(len(SEMANTIC_MAPPING), 1)) * 100
    
    def _check_kpi_accuracy(self, kpi_info: Dict, sql_query: str) -> float:
        kpi_type = kpi_info.get("kpi_type", "none")
        if kpi_type == "none":
            return 80
        
        sql_upper = sql_query.upper()
        kpi_indicators = {
            "growth_rate": ["LAG", "OVER", "ORDER BY"],
            "retention_rate": ["JOIN", "DISTINCT", "MIN"],
            "churn_rate": ["DATE", "WHERE", "COUNT"],
            "aov": ["SUM", "COUNT", "DISTINCT"],
            "running_total": ["SUM", "OVER", "ORDER BY"]
        }
        
        indicators = kpi_indicators.get(kpi_type, [])
        matches = sum(1 for ind in indicators if ind in sql_upper)
        return (matches / max(len(indicators), 1)) * 100
    
    def _check_sql_validity(self, sql_query: str) -> float:
        is_valid, _ = validate_sql_query(sql_query)
        return 100 if is_valid else 0
    
    def _check_complexity(self, sql_query: str) -> float:
        sql_upper = sql_query.upper()
        complexity_indicators = {"WITH": 20, "JOIN": 20, "OVER": 20, "GROUP BY": 20, "HAVING": 20}
        score = sum(points for indicator, points in complexity_indicators.items() if indicator in sql_upper)
        return min(100, score)
    
    def process_question(self, question: str, schema: Dict) -> Dict:
        print(f"\n{'='*60}")
        print(f"[ENGINE] Processing question: {question}")
        print(f"{'='*60}")
        
        kpi_info = self.detect_kpi_intent(question)
        semantic_mapping = self.get_semantic_mapping()
        
        llm_result = self.llm_service.generate_sql(
            question=question,
            schema=schema,
            semantic_mapping=semantic_mapping,
            kpi_info=kpi_info
        )
        
        if not llm_result["success"]:
            return {
                "success": False,
                "error": llm_result.get("rationale", "SQL generation failed")
            }
        
        sql_query = llm_result["sql_query"]
        print(f"[SQL] {sql_query}")
        
        confidence_score = self.calculate_confidence(
            question=question,
            sql_query=sql_query,
            schema=schema,
            kpi_info=kpi_info
        )
        
        return {
            "success": True,
            "kpi_info": kpi_info,
            "sql_query": sql_query,
            "rationale": llm_result["rationale"],
            "confidence_score": confidence_score
        }