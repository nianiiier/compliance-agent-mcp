from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    CHROMA_PERSIST_PATH: str = os.getenv("CHROMA_PERSIST_PATH", "./vector_db")
    UPLOAD_DOC_DIR: str = "./data/upload_docs"
    VIOLATION_CASE_DIR: str = "./data/violation_case"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    RETRIEVE_TOP_K: int = 4

settings = Settings()
