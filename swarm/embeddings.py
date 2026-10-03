"""Embedding backend: sentence-transformers if installed, else a deterministic hashing fallback."""
import hashlib
import math
import re


class Embedder:
    def __init__(self) -> None:
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.dim = 384
            self.kind = "sentence-transformers/all-MiniLM-L6-v2"
        except Exception:  # offline / not installed
            self.dim = 256
            self.kind = "hashing-fallback"

    def embed(self, text: str) -> list:
        if self.model is not None:
            return self.model.encode(text, normalize_embeddings=True).tolist()
        return self._hash_embed(text)

    def _hash_embed(self, text: str) -> list:
        vec = [0.0] * self.dim
        for tok in re.findall(r"[A-Za-z_]+", text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
