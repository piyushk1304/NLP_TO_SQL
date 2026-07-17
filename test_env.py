# test_llm.py
import requests

url = "http://127.0.0.1:8080/completion"
payload = {
    "prompt": "Hello, are you working?",
    "n_predict": 50,
    "temperature": 0.1,
    "stream": False
}

try:
    response = requests.post(url, json=payload, timeout=30)
    result = response.json()
    print("✅ Local LLM is working!")
    print(f"Response: {result.get('content', '')}")
except Exception as e:
    print(f"❌ Error: {str(e)}")