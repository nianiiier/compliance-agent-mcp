import sys
from contextlib import asynccontextmanager
from pathlib import Path
# 将项目根目录加入python搜索路径
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend_gateway.routes import upload, compliance, hitl
from backend_gateway.clients.langgraph_client import shutdown_agent_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: 什么也不做（MCP 连接是懒加载的，第一次请求时才初始化）
    yield
    # shutdown: 关闭 MCP 连接
    await shutdown_agent_service()

app = FastAPI(
    title="合规Agent‑Gateway",
    description="阶段4 FastAPI网关，对接LangGraph Agent编排层",
    version="1.0.0",
    lifespan=lifespan
)

# CORS跨域，给前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常捕获
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": str(exc)}
    )

# 注册路由
app.include_router(upload.router)
app.include_router(compliance.router)
app.include_router(hitl.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
