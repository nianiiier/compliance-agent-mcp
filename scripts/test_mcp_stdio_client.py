"""
阶段1验收测试脚本：MCP‑Server stdio测试
本脚本仅测试MCP服务工具逻辑，不引入任何Agent/LangGraph代码
验证：doc_parse_and_ingest / retrieve_compliance / check_text_similarity
"""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Windows修复stdio管道握手卡死bug
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    print("=== 开始启动MCP客户端 ===", file=sys.stderr)
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "mcp_server/main.py", "--transport", "stdio"]
    )
    async with stdio_client(server_params) as (read, write):
        print("=== 子进程已拉起，准备initialize ===", file=sys.stderr)
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ initialize握手成功！", file=sys.stderr)

            tools = await session.list_tools()
            print(f"✅ 获取工具列表：{[t.name for t in tools.tools]}", file=sys.stderr)

            # 1 文档解析入库，改成你本地真实存在的文档路径
            ingest_ret = await session.call_tool(
                "doc_parse_and_ingest",
                arguments={"file_path": r"./data/upload_docs/增值税法实施条例.txt"}
            )
            print("\n====1.文档入库返回====", file=sys.stderr)
            print(ingest_ret.content[0].text)

            # 2 RRF混合检索
            ret_ret = await session.call_tool(
                "retrieve_compliance",
                arguments={"query": "增值税进项抵扣条件", "top_k": 3}
            )
            print("\n====2.混合RRF检索返回====", file=sys.stderr)
            print(ret_ret.content[0].text)

            #3 违规案例相似度检测
            sim_ret = await session.call_tool(
                "check_text_similarity",
                arguments={"input_text": "虚开发票进行增值税抵扣"}
            )
            print("\n====3.违规案例相似度检测返回====", file=sys.stderr)
            print(sim_ret.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
