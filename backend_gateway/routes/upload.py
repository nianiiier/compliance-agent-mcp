from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend_gateway.schemas.response_schema import UploadResp
from backend_gateway.clients.langgraph_client import get_agent_service

router = APIRouter(prefix="/upload", tags=["文档上传"])

# 上传文件落到这个目录；MCP server 和 gateway 都用项目根作 CWD
UPLOAD_DIR = Path("./data/upload_docs")


@router.post("/document", response_model=UploadResp)
async def upload_document(file: UploadFile = File(...)):
    svc = await get_agent_service()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # 落盘（用绝对路径，防止 MCP 子进程 CWD 不一致）
    target = (UPLOAD_DIR / file.filename).resolve()
    content = await file.read()
    target.write_bytes(content)

    # ✅ 调真实存在的工具名 + 真实参数名
    res = await svc.call_mcp_tool(
        "doc_parse_and_ingest",
        arguments={"file_path": str(target)},
    )

    if res.get("ok"):
        return UploadResp(
            ok=True,
            msg=res.get("msg", "文档上传解析成功"),
            doc_id=res.get("file_name"),
        )
    return UploadResp(ok=False, msg=res.get("msg", "文档上传失败"), doc_id=None)