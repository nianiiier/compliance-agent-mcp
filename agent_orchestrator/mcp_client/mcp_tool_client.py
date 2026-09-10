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
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from mcp import ClientSession, Tool

# Windows事件循环补丁
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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
        logger.info("等待initialize握手...")
        await asyncio.wait_for(self._session.initialize(), timeout=20.0)
        logger.info("MCP initialize握手完成")
        resp = await self._session.list_tools()
        self._tools_cache = resp.tools
        logger.info(f"MCP连接成功，工具列表: {[t.name for t in self._tools_cache]}")

    async def close(self):
        if self._session:
            await self._session.close()
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
                resp = await asyncio.wait_for(
                    self._session.call_tool(tool_name, arguments),
                    timeout=self.timeout
                )
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


# SSE占位接口，当前Fast‑MCP传统SSE存在502bug，暂不可用
async def create_mcp_sse_client(host: str, port: int):
    raise NotImplementedError("SSE模式受Fast‑MCP SDK bug限制，暂未启用；后续迁移Streamable‑HTTP再实现")
