"""Layer 1 — AI 모델: RAG(Retrieval-Augmented Generation) 파이프라인
특허·논문·R&D·시장·지원정보 지식베이스를 벡터화하여 컨텍스트 검색 후 LLM 생성.
외부 의존 없이 동작: numpy 기반 코사인 유사도 (chromadb/faiss 선택 설치 시 자동 전환)
"""
from __future__ import annotations
import json
import math
import os
import hashlib
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
CACHE_DIR     = Path(__file__).parent.parent / ".rag_cache"


# ─────────────────────────────────────────────
# 청크 분할기
# ─────────────────────────────────────────────
def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return chunks


# ─────────────────────────────────────────────
# 임베딩: sentence-transformers → numpy TF-IDF 폴백
# ─────────────────────────────────────────────
class _SentenceEmbedder:
    """sentence-transformers 기반 의미검색 임베더 (설치 시 자동 사용)"""

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self._cache: dict[str, list[float]] = {}

    def fit(self, docs: list[str]) -> None:
        pass  # sentence-transformers는 사전학습 모델 사용, fit 불필요

    def embed(self, text: str) -> list[float]:
        if text not in self._cache:
            vec = self._model.encode(text, normalize_embeddings=True)
            self._cache[text] = vec.tolist()
        return self._cache[text]

    def cosine(self, a: list[float], b: list[float]) -> float:
        # 이미 normalize된 벡터이므로 내적 = 코사인 유사도
        return sum(x * y for x, y in zip(a, b))


class _NumpyEmbedder:
    """sentence-transformers 미설치 시 TF-IDF 기반 폴백 임베더"""

    def __init__(self):
        self._vocab: dict[str, int] = {}
        self._idf:   list[float]    = []

    def _tokenize(self, text: str) -> list[str]:
        import re
        return re.findall(r"[가-힣a-zA-Z0-9]+", text.lower())

    def fit(self, docs: list[str]) -> None:
        from collections import Counter
        N = len(docs)
        df: dict[str, int] = {}
        for doc in docs:
            for tok in set(self._tokenize(doc)):
                df[tok] = df.get(tok, 0) + 1
        self._vocab = {tok: i for i, tok in enumerate(sorted(df))}
        self._idf   = [math.log((N + 1) / (df.get(tok, 0) + 1)) + 1 for tok in sorted(df)]

    def _tf_idf(self, text: str) -> list[float]:
        from collections import Counter
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        v = [0.0] * len(self._vocab)
        for tok, cnt in tf.items():
            if tok in self._vocab:
                v[self._vocab[tok]] = (cnt / max(len(tokens), 1)) * self._idf[self._vocab[tok]]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed(self, text: str) -> list[float]:
        return self._tf_idf(text)

    def cosine(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))


def _make_embedder():
    """sentence-transformers 설치 여부에 따라 적절한 임베더 반환"""
    try:
        return _SentenceEmbedder()
    except Exception:
        return _NumpyEmbedder()


# ─────────────────────────────────────────────
# 지식베이스 로더 — knowledge/*.json → 청크
# ─────────────────────────────────────────────
class KnowledgeBaseLoader:
    """knowledge/ 디렉터리의 JSON 파일을 텍스트 청크로 변환"""

    @staticmethod
    def load_all() -> list[dict]:
        """Returns: [{"id": str, "text": str, "source": str, "meta": dict}]"""
        docs = []
        for json_file in sorted(KNOWLEDGE_DIR.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                text = KnowledgeBaseLoader._flatten(data)
                for i, chunk in enumerate(_chunk_text(text)):
                    docs.append({
                        "id":     f"{json_file.stem}_{i}",
                        "text":   chunk,
                        "source": json_file.name,
                        "meta":   {"file": json_file.name, "chunk": i},
                    })
            except Exception:
                continue
        return docs

    @staticmethod
    def _flatten(obj, depth: int = 0) -> str:
        if depth > 6:
            return ""
        if isinstance(obj, str):
            return obj
        if isinstance(obj, (int, float, bool)):
            return str(obj)
        if isinstance(obj, list):
            return " ".join(KnowledgeBaseLoader._flatten(x, depth + 1) for x in obj)
        if isinstance(obj, dict):
            parts = []
            for k, v in obj.items():
                parts.append(f"{k}: {KnowledgeBaseLoader._flatten(v, depth+1)}")
            return " | ".join(parts)
        return ""

    @staticmethod
    def add_external(docs: list[dict], source_name: str, records: list[dict]) -> list[dict]:
        """외부 DB(특허·논문·R&D) 레코드를 청크로 추가"""
        for i, rec in enumerate(records):
            text = KnowledgeBaseLoader._flatten(rec)
            for j, chunk in enumerate(_chunk_text(text)):
                docs.append({
                    "id":     f"{source_name}_{i}_{j}",
                    "text":   chunk,
                    "source": source_name,
                    "meta":   rec,
                })
        return docs


# ─────────────────────────────────────────────
# RAG 인덱스
# ─────────────────────────────────────────────
class RAGIndex:
    """지식베이스 벡터 인덱스 + 유사도 검색"""

    def __init__(self):
        self._docs:    list[dict]     = []
        self._vectors: list[list[float]] = []
        self._embedder = _make_embedder()  # sentence-transformers 우선, TF-IDF 폴백
        self._built    = False

    def build(self, docs: Optional[list[dict]] = None) -> None:
        if docs is None:
            docs = KnowledgeBaseLoader.load_all()
        self._docs = docs
        texts = [d["text"] for d in docs]
        self._embedder.fit(texts)
        self._vectors = [self._embedder.embed(t) for t in texts]
        self._built = True

    def search(self, query: str, top_k: int = 5, source_filter: str = "") -> list[dict]:
        """쿼리와 가장 유사한 청크 반환"""
        if not self._built:
            self.build()
        q_vec = self._embedder.embed(query)
        scored = []
        for i, (doc, vec) in enumerate(zip(self._docs, self._vectors)):
            if source_filter and source_filter not in doc.get("source", ""):
                continue
            sim = self._embedder.cosine(q_vec, vec)
            scored.append((sim, i, doc))
        scored.sort(key=lambda x: -x[0])
        return [
            {"score": round(s, 4), "text": d["text"], "source": d["source"], "meta": d["meta"]}
            for s, _, d in scored[:top_k]
        ]

    def search_multi(self, queries: list[str], top_k: int = 3) -> list[dict]:
        """복수 쿼리 결과 합산 (중복 제거)"""
        seen, results = set(), []
        for q in queries:
            for r in self.search(q, top_k=top_k):
                key = r["text"][:80]
                if key not in seen:
                    seen.add(key)
                    results.append(r)
        return results[:top_k * len(queries)]


# ─────────────────────────────────────────────
# RAG 컨텍스트 포매터
# ─────────────────────────────────────────────
def build_rag_context(results: list[dict], max_tokens: int = 1200) -> str:
    """검색 결과를 LLM 프롬프트용 컨텍스트 블록으로 변환"""
    lines = ["[지식베이스 참조 컨텍스트]"]
    total = 0
    for i, r in enumerate(results, 1):
        snippet = r["text"][:300]
        line    = f"\n[{i}] 출처: {r['source']} (유사도 {r['score']})\n{snippet}"
        total  += len(line.split())
        if total > max_tokens:
            break
        lines.append(line)
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 싱글턴 전역 인덱스 (최초 호출 시 자동 빌드)
# ─────────────────────────────────────────────
_GLOBAL_INDEX: Optional[RAGIndex] = None


def get_index() -> RAGIndex:
    global _GLOBAL_INDEX
    if _GLOBAL_INDEX is None:
        _GLOBAL_INDEX = RAGIndex()
        _GLOBAL_INDEX.build()
    return _GLOBAL_INDEX


def rag_search(query: str, top_k: int = 5, source_filter: str = "") -> str:
    """단일 함수 인터페이스 — BaseAgent에서 self._rag(query)로 호출"""
    results = get_index().search(query, top_k=top_k, source_filter=source_filter)
    return build_rag_context(results)
