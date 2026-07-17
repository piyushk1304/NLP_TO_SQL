import os
import json
import requests
import re
from typing import Dict, Optional
import config


class LLMService:
    def __init__(self):
        self.api_url = config.LLM_API_URL
        self.model = config.LLM_MODEL
        print(f"[LLM] Using LOCAL model: {self.model} at {self.api_url}")

    def generate_sql(
        self,
        question: str,
        schema: Dict,
        semantic_mapping: Dict,
        kpi_info: Dict
    ) -> Dict:
        """Generate SQL query using local LLM."""

        kpi_type = kpi_info.get("kpi_type", "none")
        kpi_def = kpi_info.get("definition", {})

        # Build KPI instruction block
        if kpi_type != "none":
            kpi_block = f"""
--- KPI INSTRUCTION BLOCK ---
**Detected Intent:** {kpi_type.upper()}
**Definition:** {kpi_def.get('logic_hint', 'Standard calculation')}
**Requirement:**
1. You MUST implement the logic described above.
2. Map generic columns to the actual schema provided below.
3. Use Window Functions (LAG, SUM OVER) or CTEs as required.
4. Ensure numerical correctness (handle division by zero).
-----------------------------
"""
        else:
            kpi_block = """
--- KPI INSTRUCTION BLOCK ---
No special KPI logic detected. Standard SQL aggregation applies.
-----------------------------
"""

        system_prompt = f"""
You are an expert SQL Data Analyst specializing in SQLite.
Your task is to generate a single SQL query based on the user question and database schema.

{kpi_block}

**Database Schema:**
Table: uploaded_data
Columns: {schema.get('columns', [])}
Row Count: {schema.get('row_count', 0)}

**Semantic Mapping:**
{json.dumps(semantic_mapping, indent=2)}

**Rules:**
1. Use ONLY the columns from the schema provided
2. Do NOT hallucinate columns or tables
3. Use CTEs (WITH clauses) for multi-step logic
4. Use window functions for analytics (LAG, SUM OVER, etc.)
5. Use subqueries when needed
6. ONLY SELECT queries allowed (no INSERT, UPDATE, DELETE, DROP)
7. Handle NULL values appropriately
8. Use proper date functions for SQLite (strftime, date, etc.)
9. Output ONLY valid JSON with sql_query and rationale fields
10. Do not include markdown code blocks, just raw JSON

**User Question:** {question}

**Output Format (JSON ONLY):**
{{
    "sql_query": "SELECT ...",
    "rationale": "Explanation of the SQL logic used"
}}
"""

        print(f"[LLM] Sending request to local server...")

        try:
            result = self._call_local_llm(system_prompt)
            return result
        except Exception as e:
            print(f"[LLM] Error: {str(e)}")
            return {
                "success": False,
                "sql_query": "",
                "rationale": f"Error generating SQL: {str(e)}",
                "error": str(e)
            }

    def _call_local_llm(self, prompt: str) -> Dict:
        """Call local llama.cpp server."""

        url = f"{self.api_url}/completion"

        headers = {
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "n_predict": 2000,
            "temperature": 0.1,
            "top_p": 0.9,
            "stop": ["</s>", "```", "User:", "Assistant:"],
            "stream": False
        }

        print(f"[LLM] Calling: {url}")

        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()

        result = response.json()
        content = result.get("content", "")

        print(f"[LLM] Raw response length: {len(content)} chars")

        # Extract JSON from response
        json_data = self._extract_json(content)

        if json_data:
            sql_query = json_data.get("sql_query", "").strip()
            rationale = json_data.get("rationale", "").strip()

            if not sql_query:
                print("[LLM] Parsed JSON but sql_query field is empty")
                return {
                    "success": False,
                    "sql_query": "",
                    "rationale": "LLM returned empty sql_query field",
                    "raw_response": content
                }

            print(f"[LLM] SQL generated successfully")
            return {
                "success": True,
                "sql_query": sql_query,
                "rationale": rationale,
                "model_used": self.model
            }
        else:
            print(f"[LLM] Failed to parse JSON. Raw response: {content[:500]}...")
            return {
                "success": False,
                "sql_query": "",
                "rationale": "Failed to parse JSON from LLM response",
                "raw_response": content
            }

    def _extract_json(self, text: str) -> Optional[Dict]:
        """
        Extract JSON from LLM response text.
        Uses multiple strategies from most to least reliable.
        """

        # Clean common LLM artifacts first
        text = text.strip()

        # ── Strategy 1: Direct parse (cleanest case) ──────────────────────────
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "sql_query" in parsed:
                print("[LLM] JSON extracted via direct parse")
                return parsed
        except json.JSONDecodeError:
            pass

        # ── Strategy 2: Brace-matching to find complete JSON object ───────────
        json_str = self._find_json_object(text)
        if json_str:
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    print("[LLM] JSON extracted via brace-matching")
                    return parsed
            except json.JSONDecodeError as e:
                print(f"[LLM] Brace-matched JSON parse error: {e}")

        # ── Strategy 3: Extract from markdown code block ──────────────────────
        code_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(code_pattern, text)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if isinstance(parsed, dict):
                    print("[LLM] JSON extracted via markdown block")
                    return parsed
            except json.JSONDecodeError as e:
                print(f"[LLM] Markdown block JSON parse error: {e}")

        # ── Strategy 4: Manual field extraction as last resort ────────────────
        # Handles cases where JSON is malformed but fields are readable
        sql_match = re.search(
            r'"sql_query"\s*:\s*"((?:[^"\\]|\\.)*)"',
            text,
            re.DOTALL
        )
        rationale_match = re.search(
            r'"rationale"\s*:\s*"((?:[^"\\]|\\.)*)"',
            text,
            re.DOTALL
        )

        if sql_match:
            print("[LLM] JSON extracted via manual field extraction (fallback)")
            return {
                "sql_query": sql_match.group(1).replace('\\"', '"'),
                "rationale": (
                    rationale_match.group(1).replace('\\"', '"')
                    if rationale_match
                    else "Extracted from malformed response"
                )
            }

        print(f"[LLM] All extraction strategies failed. Text sample: {text[:200]}")
        return None

    def _find_json_object(self, text: str) -> Optional[str]:
        """
        Find the first complete JSON object using brace matching.
        Correctly handles nested braces, strings, and escape sequences.
        """
        start = text.find('{')
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue

            if char == '\\' and in_string:
                escape_next = True
                continue

            if char == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

        return None