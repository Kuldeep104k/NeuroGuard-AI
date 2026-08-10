from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

from backend.config import GUIDELINE_SOURCES_PATH, GUIDELINES_PATH, RAG_TOP_K


class RAGEngine:
    def __init__(
        self,
        guidelines_path: Path = GUIDELINES_PATH,
        sources_path: Path = GUIDELINE_SOURCES_PATH,
        llm=None,
    ) -> None:
        self.guidelines_path = guidelines_path
        self.sources_path = sources_path
        self.documents = self._load_documents()
        self.chunks = [document["text"] for document in self.documents]
        self._index = None
        self._vectors = None
        self.mode = "local"
        self._build_faiss_index()

    def _load_documents(self) -> list[dict[str, str]]:
        documents: list[dict[str, str]] = []
        if self.guidelines_path.exists():
            text = self.guidelines_path.read_text(encoding="utf-8")
            documents.extend(
                {
                    "id": "local-guidelines",
                    "text": line.strip("- "),
                    "title": "Project guideline summary",
                    "url": "local://guidelines",
                }
                for line in text.splitlines()
                if line.strip()
            )
        if self.sources_path.exists():
            for source in json.loads(self.sources_path.read_text(encoding="utf-8")):
                for claim in source.get("claims", []):
                    documents.append(
                        {
                            "id": source["id"],
                            "text": claim,
                            "title": source["title"],
                            "url": source["url"],
                        }
                    )
        return documents

    @staticmethod
    def _vector(text: str, dimensions: int = 256):
        import numpy as np

        vector = np.zeros(dimensions, dtype="float32")
        for token in re.findall(r"[a-z]+", text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % dimensions] += 1.0
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
            faiss.normalize_L2(self._vectors)
            self._index.add(self._vectors)
        except Exception:
            self._index = None
            self.mode = "local"

    def retrieve(self, query: str, top_k: int = RAG_TOP_K) -> list[str]:
        return [self.format_citation(document) for document in self.retrieve_documents(query, top_k)]

    def retrieve_documents(self, query: str, top_k: int = RAG_TOP_K) -> list[dict[str, str]]:
        if not self.documents:
            return []
        if self._index is not None:
            import faiss
            import numpy as np

            query_vector = np.asarray([self._vector(query)])
            faiss.normalize_L2(query_vector)
            _, indices = self._index.search(query_vector, min(top_k, len(self.documents)))
            return [self.documents[index] for index in indices[0] if index >= 0]
        return self._lexical_retrieve(query, top_k)

    def _lexical_retrieve(self, query: str, top_k: int) -> list[dict[str, str]]:
        query_terms = set(re.findall(r"[a-z]+", query.lower()))
        ranked = sorted(
            self.documents,
            key=lambda document: len(query_terms.intersection(re.findall(r"[a-z]+", document["text"].lower()))),
            reverse=True,
        )
        return ranked[:top_k]

    @staticmethod
    def format_citation(document: dict[str, str]) -> str:
        return f"[{document['title']}] {document['text']} Source: {document['url']}"
