pip install uv
---
uv venv

uv pip install -r requirements.txt

---
# Windows cmd
.venv\Scripts\activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Mac / Linux
source .venv/bin/activate

---
python -m mcp_server.main


# 本地测试 stdio（兼容旧test_mcp_client.py）
uv run python mcp_server/main.py --transport stdio

# SSE常驻网络服务（给LangGraph远程调用）
uv run python mcp_server/main.py --transport sse --port 8005

uv run python mcp_server/main.py --transport sse --port 8005

阶段1：

uv run python mcp_server/main.py --transport stdio

uv run python scripts/test_mcp_stdio_client.py

阶段2：
uv run python scripts/test_agent_base_demo.py