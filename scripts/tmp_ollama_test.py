import os
import json
import httpx
from dotenv import load_dotenv
load_dotenv()

base_url = os.getenv("LLM_BASE_URL")
model = os.getenv("LLM_MODEL_NAME")
payload = {
    "model": model,
    "messages": [{"role":"user","content":"hello"}],
    "temperature":0.1
}
with httpx.Client(timeout=120, proxy=None) as c:
    r = c.post(f"{base_url}/chat/completions", json=payload)
    print(r.status_code)
    print(r.text)
