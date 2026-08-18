from __future__ import annotations

import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
BASE_DIR = ROOT_DIR / "base"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "documentos"
MANIFEST_PATH = BASE_DIR / "vector_sync_manifest.json"
SUPPORTED_EXTENSIONS: Set[str] = {".txt", ".pdf"}
CHUNK_MAX_CHARS = 800
OCR_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
VECTOR_DB_PATH = "./data/chroma"
MODEL_GROQ = os.getenv("MODEL_GROQ", "openai/gpt-oss-20b")
TEMPERATURE = 1.5
MAX_QUESTION_CHARS = 900



#RAG_CONTEXT_NEIGHBORS = 2
#MAX_TOKENS = 2048
#RAG_TOP_K = 10


# Después (aprox. 1/3 del contexto)
#RAG_CONTEXT_NEIGHBORS = 1
#MAX_TOKENS = 800
#RAG_TOP_K = 5


CHUNK_SIZE = 130
CHUNK_OVERLAP = 15

RAG_TOP_K = 4
RAG_CONTEXT_NEIGHBORS = 0

MAX_TOKENS = 800