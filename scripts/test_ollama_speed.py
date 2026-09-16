import time
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("LLM_BASE_URL")
model = os.getenv("LLM_MODEL_NAME")

print(f"base_url = {base_url}")
print(f"model    = {model}")
print()

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "你是一个合规审查助手，简洁回答。"},
        {"role": "user", "content": "用一句话解释：什么是增值税进项抵扣？"}
    ],
    "temperature": 0.1,
    "stream": False
}

t0 = time.time()
with httpx.Client(timeout=300.0, proxy=None, trust_env=False) as client:
    resp = client.post(f"{base_url}/chat/completions", json=payload)
    resp.raise_for_status()
    data = resp.json()
    answer = data["choices"][0]["message"]["content"]

t1 = time.time()
print(f"⏱ 耗时: {t1-t0:.1f} 秒")
print(f"📝 回答: {answer}")
print(f"📊 usage: {data.get('usage')}")