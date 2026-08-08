from __future__ import annotations

import re
from pathlib import Path

from backend.config import GUIDELINES_PATH, RAG_TOP_K


class RAGEngine:
    def __init__(self, guidelines_path: Path = GUIDELINES_PATH) -> None:
        self.guidelines_path = guidelines_path
        self.chunks = self._load_chunks()
        self._index = None
        self._vectors = None
        self._build_faiss_index()

    def _load_chunks(self) -> list[str]:
        if not self.guidelines_path.exists():
            return []
        text = self.guidelines_path.read_text(encoding="utf-8")
        return [line.strip("- ") for line in text.splitlines() if line.strip()]

    @staticmethod
    def _vector(text: str, dimensions: int = 256):
        import numpy as np

        vector = np.zeros(dimensions, dtype="float32")
        for token in re.findall(r"[a-z]+", text.lower()):
            vector[hash(token) % dimensions] += 1.0
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector

    def _build_faiss_index(self) -> None:
        if not self.chunks:
            return
        try:
            import faiss
            import numpy as np

            self._vectors = np.vstack([self._vector(chunk) for chunk in self.chunks]).astype("float32")
            self._index = faiss.IndexFlatIP(self._vectors.shape[1])
            self._index.add(self._vectors)
        except Exception:
            self._index = None

    def retrieve(self, query: str, top_k: int = RAG_TOP_K) -> list[str]:
        if self._index is not None:
            import numpy as np

            _, indices = self._index.search(np.asarray([self._vector(query)]), min(top_k, len(self.chunks)))
            return [self.chunks[index] for index in indices[0] if index >= 0]
        query_terms = set(re.findall(r"[a-z]+", query.lower()))
        ranked = sorted(
            self.chunks,
            key=lambda chunk: len(query_terms.intersection(re.findall(r"[a-z]+", chunk.lower()))),
            reverse=True,
        )
        return ranked[:top_k]
