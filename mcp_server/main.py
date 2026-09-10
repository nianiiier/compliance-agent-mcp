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

# 创建MCP实例
mcp = FastMCP("compliance‑mcp‑server")


@mcp.tool()
def doc_parse_and_ingest(file_path: str) -> dict:
    """
    文档解析并向量化入库
    Args:
        file_path: 本地文档完整路径，支持pdf/txt
    """
    return parse_and_ingest_document(file_path)


@mcp.tool()
def retrieve_compliance(query: str, top_k: int = 4) -> dict:
    """
    检索合规知识库，返回匹配的法规条款片段
    Args:
        query: 用户检索查询语句
        top_k: 返回最大片段数量
    """
    return retrieve_compliance_clauses(query, top_k)


@mcp.tool()
def check_text_similarity(input_text: str) -> dict:
    """
    将输入文本与历史违规案例做相似度比对
    Args:
        input_text: 需要检测的待审查文本
    """
    return calc_similarity_check(input_text)


@mcp.tool()
def ingest_violation_case(file_path: str) -> dict:
    """导入违规案例文档到案例向量库
    Args:
        file_path:本地txt案例路径
    """
    from mcp_server.tools.similarity_checker_tool import ingest_violation_case

    return ingest_violation_case(file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="合规MCP服务")
    # 恢复支持 stdio / sse 两种transport
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=8005, help="SSE服务端口")
    args = parser.parse_args()

    # ✅关键修复：日志输出到 stderr，不要污染stdout
    print(f"[MCP‑Server] transport={args.transport}", file=sys.stderr)

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
