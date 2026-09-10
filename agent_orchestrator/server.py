"""
Agent服务封装层：管理graph、thread会话；只做业务封装，不写web接口
后续FastAPI网关调用本层对外暴露的方法
注意：Windows开发阶段USE_MOCK_MCP=True使用mock隔离SSE 502问题；上线改为False
"""
import os
from dotenv import load_dotenv
# 导入mock客户端 + 真实sse客户端
from agent_orchestrator.mcp_client.mcp_tool_client import create_mcp_sse_client, create_mcp_mock_client
from agent_orchestrator.graph.build_graph import build_agent_graph
from agent_orchestrator.graph.state import ComplianceAgentState

load_dotenv()
# 开发调试开关：True=MockMCP；False=真实SSE MCP
USE_MOCK_MCP = True

class ComplianceAgentService:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._mcp_client = None
        self._mcp_ctx = None
        self.graph = None

    async def init(self):
        """初始化MCP连接与graph实例"""
        if USE_MOCK_MCP:
            self._mcp_ctx = create_mcp_mock_client()
        else:
            self._mcp_ctx = create_mcp_sse_client(host=self.host, port=self.port)

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
        """中断后恢复工作流，传入人工审批结果"""
        config = {"configurable": {"thread_id": thread_id}}
        return await self.graph.ainvoke(
            input={"human_approval": human_approval},
            config=config
        )




    async def get_thread_state(self, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        return await self.graph.aget_state(config=config)
