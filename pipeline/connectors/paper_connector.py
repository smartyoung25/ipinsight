"""논문·R&D 성과 Connector — OpenAlex + PubMed + Europe PMC
TRL 1~3 기초연구 근거 자동화, 기술 출처 기관 파악.
모두 무료·키 불필요 (OpenAlex 메일 권장, PubMed 무키 허용).
"""
from __future__ import annotations
import json
import urllib.request
import urllib.parse
import hashlib
import os
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / ".rag_cache"
CACHE_DIR.mkdir(exist_ok=True)


def _get(url: str, timeout: int = 8) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "IPInsight/1.0 (mailto:kyoyoung@gmail.com)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _cached_get(url: str, ttl_hours: int = 24) -> dict:
    key = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"paper_{key}.json"
    if cache_file.exists():
        age = (time.time() - cache_file.stat().st_mtime) / 3600
        if age < ttl_hours:
            return json.loads(cache_file.read_text(encoding="utf-8"))
    data = _get(url)
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


class PaperConnector:
    """
    ① OpenAlex  — api.openalex.org          (무료, 키 불필요, 2억건+)
    ② PubMed    — eutils.ncbi.nlm.nih.gov   (무료, 키 선택, 3500만건)
    ③ EuropePMC — ebi.ac.uk/europepmc       (무료, 키 불필요, 생명과학)
    활용: G2 TRLAssessor TRL 1~3 논문 근거, G0 기술 출처 기관 파악
    """

    OPENALEX  = "https://api.openalex.org"
    PUBMED    = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    # TRL 추정: 논문 유형 → TRL 레벨 매핑
    _PUBLICATION_TYPE_TRL = {
        "preprint":          (1, 2),
        "journal-article":   (2, 4),
        "proceedings":       (3, 5),
        "review":            (1, 3),
        "dataset":           (2, 4),
        "patent":            (5, 7),
    }

    def search_openalex(self, query: str, limit: int = 5) -> dict:
        """OpenAlex 논문 검색 — 기술명 → 관련 논문·인용·기관"""
        try:
            params = urllib.parse.urlencode({
                "filter": f"title.search:{query}",
                "select": "id,title,publication_year,cited_by_count,type,authorships,open_access",
                "per-page": limit,
                "sort": "cited_by_count:desc",
            })
            data = _cached_get(f"{self.OPENALEX}/works?{params}")
            works = data.get("results", [])
            return {
                "source":      "OpenAlex",
                "query":       query,
                "total":       data.get("meta", {}).get("count", 0),
                "papers": [
                    {
                        "title":       w.get("title", ""),
                        "year":        w.get("publication_year"),
                        "citations":   w.get("cited_by_count", 0),
                        "type":        w.get("type", ""),
                        "open_access": w.get("open_access", {}).get("is_oa", False),
                        "institution": (
                            (w.get("authorships") or [{}])[0]
                            .get("institutions", [{}])[0]
                            .get("display_name", "")
                        ),
                        "trl_estimate": self._trl_estimate(w.get("type", ""), w.get("cited_by_count", 0)),
                    }
                    for w in works
                ],
            }
        except Exception as e:
            return {"source": "OpenAlex", "query": query, "error": str(e)}

    def search_pubmed(self, query: str, limit: int = 5, api_key: str = "") -> dict:
        """PubMed 검색 — 의학·바이오 분야 임상 근거"""
        try:
            key_param = f"&api_key={api_key}" if api_key else ""
            # 1단계: ID 검색
            search_url = (
                f"{self.PUBMED}/esearch.fcgi?db=pubmed"
                f"&term={urllib.parse.quote(query)}&retmax={limit}&retmode=json{key_param}"
            )
            search = _cached_get(search_url)
            ids = search.get("esearchresult", {}).get("idlist", [])
            if not ids:
                return {"source": "PubMed", "query": query, "papers": []}
            # 2단계: 상세 조회
            fetch_url = (
                f"{self.PUBMED}/esummary.fcgi?db=pubmed"
                f"&id={','.join(ids)}&retmode=json{key_param}"
            )
            detail = _cached_get(fetch_url)
            result_map = detail.get("result", {})
            papers = []
            for uid in ids:
                item = result_map.get(uid, {})
                papers.append({
                    "pmid":      uid,
                    "title":     item.get("title", ""),
                    "year":      item.get("pubdate", "")[:4],
                    "journal":   item.get("source", ""),
                    "authors":   [a.get("name", "") for a in item.get("authors", [])[:3]],
                })
            return {"source": "PubMed", "query": query, "total": len(ids), "papers": papers}
        except Exception as e:
            return {"source": "PubMed", "query": query, "error": str(e)}

    def search_europepmc(self, query: str, limit: int = 5) -> dict:
        """Europe PMC 검색 — 생명과학 오픈액세스"""
        try:
            params = urllib.parse.urlencode({
                "query":    query,
                "format":   "json",
                "pageSize": limit,
                "sort":     "CITED desc",
            })
            data = _cached_get(f"{self.EUROPEPMC}/search?{params}")
            results = data.get("resultList", {}).get("result", [])
            return {
                "source": "Europe PMC",
                "query":  query,
                "total":  data.get("hitCount", 0),
                "papers": [
                    {
                        "title":   r.get("title", ""),
                        "year":    r.get("pubYear"),
                        "journal": r.get("journalTitle", ""),
                        "pmid":    r.get("pmid", ""),
                        "is_oa":   r.get("isOpenAccess", "N") == "Y",
                    }
                    for r in results
                ],
            }
        except Exception as e:
            return {"source": "Europe PMC", "query": query, "error": str(e)}

    def trl_evidence(self, query: str) -> dict:
        """3개 소스 통합 → TRL 근거 종합"""
        oa   = self.search_openalex(query, limit=3)
        pm   = self.search_pubmed(query, limit=3)
        epmc = self.search_europepmc(query, limit=3)

        all_papers = oa.get("papers", []) + pm.get("papers", []) + epmc.get("papers", [])
        total_citations = sum(p.get("citations", 0) for p in oa.get("papers", []))
        trl_hints = [p.get("trl_estimate") for p in oa.get("papers", []) if p.get("trl_estimate")]
        avg_trl = round(sum(trl_hints) / len(trl_hints), 1) if trl_hints else None

        return {
            "query":           query,
            "total_papers":    len(all_papers),
            "total_citations": total_citations,
            "trl_estimate":    avg_trl,
            "trl_basis":       "논문 수·인용·유형 기반 추정" if avg_trl else "데이터 부족",
            "sources":         {"openalex": oa, "pubmed": pm, "europepmc": epmc},
        }

    def _trl_estimate(self, pub_type: str, citations: int) -> int | None:
        """논문 유형 + 인용 수 → TRL 추정값 (중앙값)"""
        rng = self._PUBLICATION_TYPE_TRL.get(pub_type)
        if not rng:
            return None
        low, high = rng
        # 인용 100+ = 검증된 기술 → TRL 상향
        if citations > 100:
            high = min(high + 1, 9)
        return (low + high) // 2
