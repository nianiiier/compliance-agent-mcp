from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from mcp_server.config import settings

def get_embedding_func():
    return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

def get_violation_case_vector_store():
    return Chroma(
        persist_directory=settings.CHROMA_PERSIST_PATH,
        embedding_function=get_embedding_func(),
        collection_name=settings.COLLECTION_VIOLATION_CASES
    )

def ingest_violation_case(file_path: str) -> dict:
    """导入单个违规案例txt到独立向量集合；供脚本调用"""
    try:
        fp = Path(file_path)
        if not fp.exists():
            return {"ok":False, "msg":f"案例文件不存在 {file_path}"}
        loader = TextLoader(str(fp), encoding="utf‑8")
        raw_docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        split_docs = splitter.split_documents(raw_docs)
        vs = get_violation_case_vector_store()
        vs.add_documents(split_docs)
        return {"ok":True, "file_name":fp.name, "chunk_count":len(split_docs), "msg":"违规案例入库完成"}
    except Exception as e:
        return {"ok":False, "msg":f"违规案例入库异常:{str(e)}"}


def calc_similarity_check(input_text: str, top_k:int=3) -> dict:
    """
    MCP工具：输入文本 和【违规案例向量库】做相似度检索
    """
    try:
        vs = get_violation_case_vector_store()
        cnt = vs._collection.count()
        if cnt <= 0:
            return {"ok":True,"msg":"无历史违规案例","similar_result":[]}

        docs = vs.similarity_search(input_text, k=top_k)
        results = []
        for d in docs:
            results.append({
                "content_snippet": d.page_content[:200],
                "source": d.metadata.get("source","")
            })
        return {
            "ok":True,
            "similar_result": results
        }
    except Exception as e:
        return {"ok":False, "similar_result":[], "msg":f"相似度检测异常:{str(e)}"}
