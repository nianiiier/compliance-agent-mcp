"""
Agent服务封装层：管理graph、thread会话；只做业务封装，不写web接口
transport模式: mock | stdio(推荐，无SSE) | sse(备用)
"""
import os
from dotenv import load_dotenv
# 导入三种客户端
from agent_orchestrator.mcp_client.mcp_tool_client import (
    create_mcp_sse_client,
    create_mcp_mock_client,
    create_mcp_stdio_client
)
from agent_orchestrator.graph.build_graph import build_agent_graph
from agent_orchestrator.graph.state import ComplianceAgentState
from langgraph.types import Command

load_dotenv()

# ============ MCP传输模式配置 ============
MCP_TRANSPORT = "mock"      # 调试，不启动子进程
# MCP_TRANSPORT = "stdio"        # ✅ 本机优先使用stdio，完全不用SSE
# MCP_TRANSPORT = "sse"       # 备用，SSE模式

# stdio配置：mcp‑server脚本路径
from pathlib import Path
# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
MCP_SERVER_SCRIPT = str(PROJECT_ROOT / "mcp_server" / "main.py")
# sse备用配置，只有transport=sse才生效
MCP_SSE_HOST = "127.0.0.1"
MCP_SSE_PORT = 8005


class ComplianceAgentService:
    def __init__(self):
        # ✅ 移除host,port参数，不再强依赖SSE
        self._mcp_client = None
        self._mcp_ctx = None
        self.graph = None

    async def init(self):
        """初始化MCP连接与graph实例"""
        if MCP_TRANSPORT == "mock":
            self._mcp_ctx = create_mcp_mock_client()
        elif MCP_TRANSPORT == "stdio":
            self._mcp_ctx = create_mcp_stdio_client(MCP_SERVER_SCRIPT)
        elif MCP_TRANSPORT == "sse":
            self._mcp_ctx = create_mcp_sse_client(host=MCP_SSE_HOST, port=MCP_SSE_PORT)
        else:
            raise ValueError(f"非法MCP_TRANSPORT: {MCP_TRANSPORT}，可选 mock / stdio / sse")

        self._mcp_client = await self._mcp_ctx.__aenter__()
        self.graph = build_agent_graph(self._mcp_client)

    async def close(self):
        if self._mcp_ctx:
            await self._mcp_ctx.__aexit__(None, None, None)

    async def invoke_review(self, user_input: str, thread_id: str):
        init_state = ComplianceAgentState(
            user_input=user_input,
            compliance_clauses=[],
            violation_points=[]
        )
        # ✅新版LangGraph标准config格式
        config = {"configurable": {"thread_id": thread_id}}
        return await self.graph.ainvoke(init_state, config=config)

    async def resume_review(self, thread_id: str, human_approval: bool):
        config = {"configurable": {"thread_id": thread_id}}
        return await self.graph.ainvoke(
            input=Command(resume=human_approval),
            config=config
        )




    async def get_thread_state(self, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        return await self.graph.aget_state(config=config)
