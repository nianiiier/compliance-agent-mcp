import hashlib
from collections import defaultdict
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from mcp_server.config import settings

def get_embedding_func():
    return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

def get_compliance_vector_store():
    return Chroma(
        persist_directory=settings.CHROMA_PERSIST_PATH,
        embedding_function=get_embedding_func(),
        collection_name=settings.COLLECTION_COMPLIANCE_RULES
    )

def rrf_fusion(doc_lists, k=60):
    """RRF倒数排名融合"""
    fused_score = defaultdict(float)
    for docs in doc_lists:
        for rank, d in enumerate(docs):
            h = hashlib.md5(d.page_content.encode("utf‑8")).hexdigest()
            fused_score[h] += 1.0 / (k + rank + 1)
    sorted_items = sorted(fused_score.items(), key=lambda x:x[1], reverse=True)
    return sorted_items

def retrieve_compliance_clauses(query: str, top_k: int = None) -> dict:
    """
    MCP工具：向量+BM25 RRF混合检索合规法规条款；返回结果自动去重
    """
    try:
        if top_k is None:
            top_k = settings.RETRIEVE_TOP_K
        vector_store = get_compliance_vector_store()

        # 向量检索，多取候选
        vector_docs = vector_store.similarity_search(query, k=settings.HYBRID_RETRIEVE_K)
        # BM25内存检索（从向量库读出全部文档用于BM25初始化；小规模知识库够用）
        all_docs = vector_store.get(include=["documents", "metadatas"])
        doc_objs = []
        for idx, txt in enumerate(all_docs["documents"]):
            meta = all_docs["metadatas"][idx]
            from langchain_core.documents import Document
            doc_objs.append(Document(page_content=txt, metadata=meta))

        if len(doc_objs) == 0:
            return {
                "ok": True,
                "query": query,
                "hit_count": 0,
                "clauses": [],
                "msg":"知识库为空"
            }

        bm25_retriever = BM25Retriever.from_documents(doc_objs)
        bm25_retriever.k = settings.HYBRID_RETRIEVE_K
        bm25_docs = bm25_retriever.invoke(query)

        # RRF融合
        fused = rrf_fusion([vector_docs, bm25_docs], k=settings.RRF_CONST)
        # hash → document映射
        hash2doc = {}
        for d in vector_docs + bm25_docs:
            h = hashlib.md5(d.page_content.encode("utf‑8")).hexdigest()
            hash2doc[h] = d

        final_docs = []
        for h,_ in fused:
            if h in hash2doc:
                final_docs.append(hash2doc[h])
            if len(final_docs) >= top_k:
                break

        clauses = []
        for d in final_docs:
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
    except Exception as e:
        return {"ok":False, "query":query, "hit_count":0, "clauses":[], "msg":f"检索异常:{str(e)}"}
