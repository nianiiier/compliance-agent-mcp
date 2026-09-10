from fastapi import APIRouter, UploadFile, File
from backend_gateway.schemas.response_schema import UploadResp
from backend_gateway.clients.langgraph_client import get_agent_service

router = APIRouter(prefix="/upload", tags=["文档上传"])


@router.post("/document", response_model=UploadResp)
async def upload_document(file: UploadFile = File(...)):
    svc = await get_agent_service()
    mcp_client = svc._mcp_client
    content = await file.read()
    # 调用MCP上传文档工具
    res = await mcp_client.call_tool(
        "upload_document",
        arguments={
            "filename": file.filename,
            "content": content.decode("utf‑8", errors="ignore")
        }
    )
    if res.get("ok"):
        return UploadResp(ok=True, msg="文档上传解析成功", doc_id=res.get("doc_id"))
    return UploadResp(ok=False, msg="文档上传失败", doc_id=None)
