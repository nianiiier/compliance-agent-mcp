"""
直接httpx调用Ollama；Windows asyncio内部执行同步httpx会出现代理读取异常，用to_thread隔离
"""
import os
import json
import httpx
from dotenv import load_dotenv
import asyncio

load_dotenv()

def ollama_invoke(system_prompt: str, user_prompt: str) -> str:
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL_NAME")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    # trust_env=False：禁止读取Windows系统环境/注册表代理配置，根治localhost被代理劫持502
    with httpx.Client(timeout=120.0, proxy=None, trust_env=False) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            json=payload
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def ollama_invoke_async(system_prompt: str, user_prompt: str) -> str:
    """在线程池运行同步httpx，脱离asyncio事件循环上下文，规避Windows代理坑"""
    return await asyncio.to_thread(ollama_invoke, system_prompt, user_prompt)
