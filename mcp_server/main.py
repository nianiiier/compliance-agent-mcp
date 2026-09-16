import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import asyncio
import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from mcp_server.tools.doc_parser_tool import parse_and_ingest_document
from mcp_server.tools.compliance_retriever_tool import retrieve_compliance_clauses
from mcp_server.tools.similarity_checker_tool import calc_similarity_check
from mcp_server.config import settings

# 先解析参数，再创建 FastMCP，让 host/port 生效
_parser = argparse.ArgumentParser()
_parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
_parser.add_argument("--port", type=int, default=8005)
_parser.add_argument("--host", default="127.0.0.1")
_args = _parser.parse_args()

# 创建MCP实例
mcp = FastMCP(
    "compliance-mcp-server",
    host=_args.host,
    port=_args.port,
)

@mcp.tool()
async def doc_parse_and_ingest(file_path: str) -> dict:
    """
    文档解析并向量化入库
    Args:
        file_path: 本地文档完整路径，支持pdf/txt
    """
    return await asyncio.to_thread(parse_and_ingest_document, file_path)


@mcp.tool()
async def retrieve_compliance(query: str, top_k: int = 4) -> dict:
    """
    检索合规知识库，返回匹配的法规条款片段
    Args:
        query: 用户检索查询语句
        top_k: 返回最大片段数量
    """
    return await asyncio.to_thread(retrieve_compliance_clauses, query, top_k)


@mcp.tool()
async def check_text_similarity(input_text: str) -> dict:
    """
    将输入文本与历史违规案例做相似度比对
    Args:
        input_text: 需要检测的待审查文本
    """
    return await asyncio.to_thread(calc_similarity_check, input_text)


@mcp.tool()
async def ingest_violation_case(file_path: str) -> dict:
    """导入违规案例文档到案例向量库"""
    from mcp_server.tools.similarity_checker_tool import ingest_violation_case as _ingest
    return await asyncio.to_thread(_ingest, file_path)


if __name__ == "__main__":
    transport = _args.transport
    if transport == "sse":
        print(f"[MCP-Server] SSE mode → http://{_args.host}:{_args.port}/sse")

        # ✅ 启动前预热 embedding 模型，避免首次调用慢到超时
        print("[MCP-Server] 预热 embedding 模型（首次可能较慢）...")
        from mcp_server.tools.compliance_retriever_tool import get_embedding_func
        _emb = get_embedding_func()
        # 触发一次 encode，把 sentence-transformers 的懒加载配置全部下载完
        _emb.embed_query("预热")
        print("[MCP-Server] 模型预热完成")

        mcp.run(transport="sse")
    else:
        print(f"[MCP-Server] STDIO mode")
        mcp.run(transport="stdio")