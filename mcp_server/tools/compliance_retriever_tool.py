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

def retrieve_compliance_clauses(query: str, top_k: int = None) -> dict:
    """
    MCP工具：根据用户查询，检索合规知识库条款
    """
    if top_k is None:
        top_k = settings.RETRIEVE_TOP_K
    vector_store = get_chroma_vector_store()
    retriever = vector_store.as_retriever(k=top_k)
    docs = retriever.invoke(query)

    clauses = []
    for d in docs:
        clauses.append({
            "content": d.page_content,
            "source": d.metadata.get("source", ""),
            "page": d.metadata.get("page", 0)
        })
    return {
        "ok": True,
        "query": query,
        "hit_count": len(clauses),
        "clauses": clauses
    }
