import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client

async def main():
    # 连接SSE MCP服务，确保已经启动：uv run python mcp_server/main.py --transport sse --port 8005
    async with sse_client("http://127.0.0.1:8005/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ SSE MCP Client会话初始化成功")

            # 1.文档入库
            ingest_ret = await session.call_tool("doc_parse_and_ingest",
                arguments={"file_path": r"./data/upload_docs/增值税法实施条例.txt"})
            print("\n====文档入库====")
            print(ingest_ret.content[0].text)

            #2.检索
            ret_ret = await session.call_tool("retrieve_compliance",
                arguments={"query":"增值税进项抵扣条件","top_k":3})
            print("\n====混合检索返回====")
            print(ret_ret.content[0].text)

            #3.查重
            sim_ret = await session.call_tool("check_text_similarity",
                arguments={"input_text":"虚开发票进行增值税抵扣"})
            print("\n====相似度查重====")
            print(sim_ret.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
