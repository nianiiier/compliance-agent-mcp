"""一键导入 data/upload_docs/ 下所有 txt/pdf 到向量库"""
import sys
import asyncio
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.client.sse import sse_client
from mcp import ClientSession

DOCS_DIR = PROJECT_ROOT / "data" / "upload_docs"


async def main():
    files = list(DOCS_DIR.glob("*.txt")) + list(DOCS_DIR.glob("*.pdf"))
    if not files:
        print(f"❌ {DOCS_DIR} 下没有文档")
        return

    async with sse_client("http://127.0.0.1:8005/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for f in files:
                print(f"📄 导入 {f.name}...")
                r = await session.call_tool(
                    "doc_parse_and_ingest",
                    arguments={"file_path": str(f)},
                )
                print(f"   → {r.content[0].text[:100]}")


if __name__ == "__main__":
    asyncio.run(main())