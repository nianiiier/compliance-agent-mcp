"""
MCP薄封装客户端
注意：Windows下不要把stdio_client嵌套进本模块内部asynccontextmanager，会触发anyio BrokenResourceError
底层stdio_client交给调用方脚本管理（复用阶段1验证过的原始写法）
架构约束：不直接import mcp_server业务代码，全部走MCP协议调用
"""
import asyncio
import json
import logging
import os
import sys
import anyio
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from mcp import ClientSession, Tool
from contextlib import asynccontextmanager
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

load_dotenv()
logger = logging.getLogger("mcp_client")


class MCPToolClient:
    """
    薄封装MCP客户端
    ※注意：read, write流由外部 stdio_client / sse_client 提供，不在本类内部创建子进程
    """
    def __init__(
        self,
        read_stream,
        write_stream,
        retry_times: int = int(os.getenv("MCP_RETRY_TIMES", "2")),
        timeout: int = int(os.getenv("MCP_TIMEOUT", "30")),
    ):
        self.read_stream = read_stream
        self.write_stream = write_stream
        self.retry_times = retry_times
        self.timeout = timeout
        self._session: Optional[ClientSession] = None
        self._tools_cache: List[Tool] = []

    async def connect(self):
        """初始化session握手，外部传入read/write流"""
        self._session = ClientSession(self.read_stream, self.write_stream)
        await self._session.__aenter__()

        try:
            logger.info("等待initialize握手...")
            with anyio.fail_after(30):
                await self._session.initialize()
            logger.info("MCP initialize握手完成")

            resp = await self._session.list_tools()
            self._tools_cache = resp.tools
            logger.info(f"MCP连接成功，工具列表: {[t.name for t in self._tools_cache]}")
        except BaseException:
            # 初始化失败，清理 session 再抛出
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
            raise

    async def close(self):
        if self._session is not None:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"关闭MCP session时异常: {e}")
            finally:
                self._session = None
        self._tools_cache.clear()
        logger.info("MCP会话已关闭")

    async def list_tools(self) -> List[Tool]:
        if not self._session:
            raise RuntimeError("未建立MCP会话，请先调用 connect()")
        return self._tools_cache

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self._session is None:
            return {"ok": False, "msg": "MCP客户端未建立会话", "data": None}

        last_err: Optional[Exception] = None
        for attempt in range(self.retry_times + 1):
            try:
                logger.info(f"调用工具 {tool_name}, args摘要 {str(arguments)[:200]}")
                with anyio.fail_after(self.timeout):
                    resp = await self._session.call_tool(tool_name, arguments)
                payload = json.loads(resp.content[0].text)
                logger.info(f"工具 {tool_name} 调用成功")
                return payload

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                last_err = e
                if attempt < self.retry_times:
                    sleep_t = 0.5 * (attempt + 1)
                    logger.warning(f"[{attempt+1}/{self.retry_times}]连接异常重试: {str(e)}, sleep {sleep_t}s")
                    await asyncio.sleep(sleep_t)
                    continue
            except json.JSONDecodeError:
                logger.exception(f"工具 {tool_name} 返回非合法JSON")
                return {"ok": False, "msg": "MCP返回数据解析失败", "data": None}
            except Exception as e:
                logger.exception(f"工具 {tool_name} 业务异常，不重试")
                return {"ok": False, "msg": f"调用异常: {str(e)}", "data": None}

        return {"ok": False, "msg": f"全部重试失败: {str(last_err)}", "data": None}


@asynccontextmanager
async def create_mcp_sse_client(host: str, port: int):
    """
    SSE模式上下文管理器
    注意：Fast‑MCP传统SSE存在偶发502异常风险，生产后续迁移Streamable‑HTTP
    MCP服务需要预先独立启动：uv run python mcp_server/main.py --transport sse --port 8005
    """
    url = f"http://{host}:{port}/sse"
    async with sse_client(url) as (read, write):
        client = MCPToolClient(read_stream=read, write_stream=write)
        await client.connect()
        try:
            yield client
        finally:
            await client.close()


# ==================== Mock客户端：用于阶段3调试LangGraph，规避SSE 502 / stdio Windows bug ====================
class MockMCPToolClient:
    """模拟MCP客户端，返回固定样例数据，格式和真实MCP返回完全一致；业务节点不需要做任何修改"""
    def __init__(self):
        pass

    async def connect(self):
        pass

    async def close(self):
        pass

    async def list_tools(self):
        from mcp import Tool
        return [Tool(name="retrieve_compliance", description="", inputSchema={})]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name == "retrieve_compliance":
            # 模拟法规检索返回，和真实MCP输出json结构完全对齐
            return {
                "ok": True,
                "query": arguments.get("query",""),
                "hit_count":3,
                "clauses":[
                    {
                        "content":"虚开增值税发票属于违法行为，纳税人不得虚开发票用于进项税额抵扣。",
                        "source":"data/upload_docs/增值税法实施条例.txt",
                        "page":0
                    },
                    {
                        "content":"进项税额抵扣应当取得合法有效的增值税扣税凭证。",
                        "source":"data/upload_docs/增值税法实施条例.txt",
                        "page":0
                    }
                ]
            }
        elif tool_name == "check_text_similarity":
            return {"ok":True,"similar_result":[{"case_text":"虚开发票抵扣增值税","score":0.92}]}
        else:
            return {"ok":False,"msg":"mock未实现该工具","data":None}


@asynccontextmanager
async def create_mcp_mock_client():
    """mock上下文管理器，替换create_mcp_sse_client使用"""
    client = MockMCPToolClient()
    await client.connect()
    try:
        yield client
    finally:
        await client.close()

@asynccontextmanager
async def create_mcp_stdio_client(server_script: str):
    """
    stdio传输，Windows：不要嵌套uv run，直接使用当前进程的python解释器
    """
    # ✅ 取当前虚拟环境python.exe路径，避免uv run双层子进程造成stdio流劫持
    python_exe = sys.executable
    params = StdioServerParameters(
        command=python_exe,
        args=[server_script, "--transport", "stdio"],
        env=dict(os.environ)
    )
    async with stdio_client(params) as (read, write):
        client = MCPToolClient(read_stream=read, write_stream=write)
        await client.connect()
        try:
            yield client
        finally:
            await client.close()
