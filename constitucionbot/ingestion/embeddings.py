from __future__ import annotations

from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL


def load_embedding_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def create_embeddings(texts: List[str], model_name: str = EMBEDDING_MODEL) -> np.ndarray:
    model = load_embedding_model(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    return embeddings
