import os
import json
import requests
import re
from typing import Dict
import config

class LLMService:
    def __init__(self):
        self.api_url = config.LLM_API_URL
        self.model = config.LLM_MODEL
        print(f"[LLM] Using LOCAL model: {self.model} at {self.api_url}")
    
    def generate_sql(self, question: str, schema: Dict, semantic_mapping: Dict, 
                     kpi_info: Dict) -> Dict:
        """Generate SQL query using local LLM"""
        
        kpi_type = kpi_info.get("kpi_type", "none")
        kpi_def = kpi_info.get("definition", {})
        
        # Build KPI instruction block
        kpi_block = ""
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
            kpi_block = "\n--- KPI INSTRUCTION BLOCK ---\nNo special KPI logic detected. Standard SQL aggregation applies.\n-----------------------------\n"
        
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
        """Call local llama.cpp server"""
        
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
            print(f"[LLM] SQL generated successfully")
            return {
                "success": True,
                "sql_query": json_data.get("sql_query", ""),
                "rationale": json_data.get("rationale", ""),
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
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from LLM response text"""
        
        # Try to find JSON object with sql_query field
        json_pattern = r'\{[^{}]*"sql_query"[^{}]*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group())
            except Exception as e:
                print(f"[LLM] JSON parse error (pattern 1): {str(e)}")
        
        # Try to find code block with JSON
        code_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
        match = re.search(code_pattern, text)
        
        if match:
            try:
                return json.loads(match.group(1))
            except Exception as e:
                print(f"[LLM] JSON parse error (pattern 2): {str(e)}")
        
        # Try to find any JSON object
        brace_pattern = r'\{[\s\S]*\}'
        match = re.search(brace_pattern, text)
        
        if match:
            try:
                return json.loads(match.group())
            except Exception as e:
                print(f"[LLM] JSON parse error (pattern 3): {str(e)}")
        
        # Last resort: try to parse entire text
        try:
            return json.loads(text)
        except:
            return None