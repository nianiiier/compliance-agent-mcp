import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["mcp_server/main.py"],
    env=None,
    stderr=1
)

async def main():
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ MCP Client会话初始化成功")

                ingest_result = await session.call_tool(
                    "doc_parse_and_ingest",
                    arguments={"file_path": r"./data/upload_docs/增值税法实施条例.txt"}
                )
                print("\n=====文档入库返回=====")
                print(ingest_result.content[0].text)

                ret_result = await session.call_tool(
                    "retrieve_compliance",
                    arguments={"query":"增值税进项抵扣条件","top_k":3}
                )
                print("\n=====检索返回条款=====")
                print(ret_result.content[0].text)

                sim_result = await session.call_tool(
                    "check_text_similarity",
                    arguments={"input_text":"虚开发票进行增值税抵扣"}
                )
                print("\n=====相似度查重返回=====")
                print(sim_result.content[0].text)
    except Exception as e:
        print(f"\n❌客户端异常：{e}")

if __name__ == "__main__":
    asyncio.run(main())
