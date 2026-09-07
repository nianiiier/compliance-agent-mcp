import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from mcp_server.tools.doc_parser_tool import parse_and_ingest_document
from mcp_server.tools.compliance_retriever_tool import retrieve_compliance_clauses
from mcp_server.tools.similarity_checker_tool import calc_similarity_check

# 创建MCP服务实例
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
def retrieve_compliance(query: str, top_k: int=4) -> dict:
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

if __name__ == "__main__":
    # stdio模式，供本地客户端调用
    mcp.run(transport="stdio")
