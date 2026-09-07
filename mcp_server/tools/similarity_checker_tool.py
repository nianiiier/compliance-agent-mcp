import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
from mcp_server.config import settings

_model = None

def get_sim_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model

def calc_similarity_check(input_text: str, case_dir: str = None) -> dict:
    """
    MCP工具：计算输入文本与历史违规案例的相似度
    """
    if case_dir is None:
        case_dir = settings.VIOLATION_CASE_DIR
    case_path = Path(case_dir)
    case_files = list(case_path.glob("*.txt"))
    if len(case_files) == 0:
        return {"ok":True,"msg":"无历史违规案例","similar_result":[]}

    model = get_sim_model()
    input_emb = model.encode(input_text)
    results = []
    for f in case_files:
        case_text = f.read_text(encoding="utf‑8")
        case_emb = model.encode(case_text)
        sim = float(np.dot(input_emb, case_emb)/(np.linalg.norm(input_emb)*np.linalg.norm(case_emb)))
        results.append({
            "case_file": f.name,
            "similarity": round(sim,4)
        })
    results.sort(key=lambda x:x["similarity"],reverse=True)
    return {
        "ok":True,
        "similar_result":results
    }
