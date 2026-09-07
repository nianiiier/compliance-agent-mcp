import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from mcp_server.config import settings

def get_embedding_func():
    return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

def get_chroma_vector_store():
    return Chroma(
        persist_directory=settings.CHROMA_PERSIST_PATH,
        embedding_function=get_embedding_func(),
        collection_name="compliance_rules"
    )

def parse_and_ingest_document(file_path: str) -> dict:
    """
    MCP工具：解析本地文档，切片存入向量库
    :param file_path: 本地文件路径，pdf/txt
    :return: 处理结果统计
    """
    fp = Path(file_path)
    if not fp.exists():
        return {"ok": False, "msg": f"文件不存在 {file_path}"}

    # 加载文档
    if fp.suffix.lower() == ".pdf":
        loader = PyPDFLoader(str(fp))
    elif fp.suffix.lower() == ".txt":
        loader = TextLoader(str(fp), encoding="utf‑8")
    else:
        return {"ok": False, "msg": f"不支持文件类型 {fp.suffix}"}

    raw_docs = loader.load()
    # 切分
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )
    split_docs = splitter.split_documents(raw_docs)

    vector_store = get_chroma_vector_store()
    vector_store.add_documents(split_docs)

    return {
        "ok": True,
        "file_name": fp.name,
        "raw_page_count": len(raw_docs),
        "chunk_count": len(split_docs),
        "msg": "文档成功入库向量数据库"
    }
