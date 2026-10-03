"""Qdrant-backed memory of historical error signatures -> fixes."""
import hashlib
import time
from pathlib import Path
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .config import QDRANT_PATH, QDRANT_URL
from .embeddings import Embedder

COLLECTION = "historical_fixes"


class FixMemory:
    def __init__(self, url: Optional[str] = None, path: Optional[Path] = None) -> None:
        self.embedder = Embedder()
        url = QDRANT_URL if url is None else url
        if url:
            self.client = QdrantClient(url=url)
        else:
            self.client = QdrantClient(path=str(path or QDRANT_PATH))
        existing = [c.name for c in self.client.get_collections().collections]
        if COLLECTION not in existing:
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE),
            )

    def add_fix(self, signature: str, diff: str, explanation: str, source: str = "autonomous") -> None:
        point_id = int(hashlib.md5(signature.encode()).hexdigest()[:15], 16)
        self.client.upsert(
            collection_name=COLLECTION,
            points=[
                PointStruct(
                    id=point_id,
                    vector=self.embedder.embed(signature),
                    payload={
                        "signature": signature,
                        "diff": diff,
                        "explanation": explanation,
                        "source": source,
                        "stored_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
            ],
        )

    def search(self, signature: str, k: int = 3, min_score: float = 0.35) -> list:
        res = self.client.query_points(
            collection_name=COLLECTION, query=self.embedder.embed(signature), limit=k
        ).points
        return [{"score": round(p.score, 3), **p.payload} for p in res if p.score >= min_score]
