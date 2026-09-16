from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# ✅ 强制使用国内镜像，必须放在任何 huggingface/transformers import 之前
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

load_dotenv()

_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
_LOCAL_MODEL = _PROJECT_ROOT / "models" / "all-MiniLM-L6-v2"

class Settings(BaseSettings):
    # 向量库路径
    CHROMA_PERSIST_PATH: str = os.getenv("CHROMA_PERSIST_PATH", "./vector_db")
    # 文件目录
    UPLOAD_DOC_DIR: str = "./data/upload_docs"
    VIOLATION_CASE_DIR: str = "./data/violation_case"

    # 向量集合名称：法规库 / 违规案例库分开
    COLLECTION_COMPLIANCE_RULES: str = "compliance_rules"
    COLLECTION_VIOLATION_CASES: str = "violation_cases"

    # Embedding & 切分
    EMBEDDING_MODEL: str = str(_LOCAL_MODEL) if _LOCAL_MODEL.exists() else "sentence-transformers/all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150

    # 检索配置
    RETRIEVE_TOP_K: int = 4
    HYBRID_RETRIEVE_K: int = 8   # 混合检索内部多取，融合后再截断top_k
    RRF_CONST: int = 60

    # MCP SSE服务配置
    MCP_HOST: str = os.getenv("MCP_HOST", "127.0.0.1")
    MCP_PORT: int = int(os.getenv("MCP_PORT", 8005))

settings = Settings()
