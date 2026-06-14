"""임상·규제 근거 Connector — ClinicalTrials.gov + EUDAMED
G8 RegulatoryRoadmap 실데이터 보강. 모두 무료·키 불필요.
"""
from __future__ import annotations
import json, urllib.request, urllib.parse, hashlib, time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / ".rag_cache"
CACHE_DIR.mkdir(exist_ok=True)

import os as _os

_CT  = "https://clinicaltrials.gov/api/v2"
_EUD = "https://ec.europa.eu/tools/eudamed/api"
_FDA = "https://api.fda.gov"


def _fda_key_param() -> str:
    """FDA API 키를 쿼리 파라미터로 반환 (미설정 시 빈 문자열)"""
    key = _os.environ.get("FDA_API_KEY", "")
    return f"&api_key={key}" if key else ""


def _get(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "IPInsight/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _cached_get(url: str, ttl_hours: int = 24) -> dict:
    key = hashlib.md5(url.encode()).hexdigest()
    f = CACHE_DIR / f"clinical_{key}.json"
    if f.exists() and (time.time() - f.stat().st_mtime) / 3600 < ttl_hours:
        return json.loads(f.read_text(encoding="utf-8"))
    data = _get(url)
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


class ClinicalConnector:
    """
    ① ClinicalTrials.gov v2 — clinicaltrials.gov/api/v2  (무료, 45만건)
    ② EUDAMED              — ec.europa.eu/tools/eudamed  (무료, EU 의료기기)
    활용: G8 규제 로드맵 임상 근거, G7 PoC 설계 벤치마킹
    """

    # ClinicalTrials 상태 → 규제 단계 매핑
    _STATUS_PHASE = {
        "RECRUITING":             "진행 중 (모집)",
        "ACTIVE_NOT_RECRUITING":  "진행 중 (모집완료)",
        "COMPLETED":              "완료",
        "NOT_YET_RECRUITING":     "시작 전",
        "TERMINATED":             "조기종료",
        "WITHDRAWN":              "철회",
    }

    def search_trials(self, query: str, limit: int = 5, phase: str = "") -> dict:
        """ClinicalTrials.gov 임상시험 검색"""
        try:
            params: dict = {"query.term": query, "pageSize": limit, "format": "json"}
            if phase:
                params["filter.advanced"] = f"AREA[Phase]{phase}"
            url = f"{_CT}/studies?{urllib.parse.urlencode(params)}"
            data = _cached_get(url)
            studies = data.get("studies", [])
            # v2 API: totalCount 키 없음 — nextPageToken 유무로 더 있음 판단
            # 반환된 studies 수로 근사치 사용
            total = len(studies)
            if data.get("nextPageToken"):
                total = len(studies) + 1   # "더 있음" 표시 (정확한 수는 API 미제공)
            return {
                "source":        "ClinicalTrials.gov v2",
                "query":         query,
                "total":         total,
                "trials": [
                    {
                        "nct_id":    s.get("protocolSection", {}).get("identificationModule", {}).get("nctId"),
                        "title":     s.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle", ""),
                        "status":    self._STATUS_PHASE.get(
                            s.get("protocolSection", {}).get("statusModule", {}).get("overallStatus", ""), "알 수 없음"),
                        "phase":     s.get("protocolSection", {}).get("designModule", {}).get("phases", []),
                        "sponsor":   s.get("protocolSection", {}).get("sponsorCollaboratorsModule", {})
                                      .get("leadSponsor", {}).get("name", ""),
                        "start":     s.get("protocolSection", {}).get("statusModule", {}).get("startDateStruct", {}).get("date"),
                        "enrollment": s.get("protocolSection", {}).get("designModule", {}).get("enrollmentInfo", {}).get("count"),
                    }
                    for s in studies
                ],
            }
        except Exception as e:
            return {"source": "ClinicalTrials.gov", "query": query, "error": str(e)[:80]}

    def regulatory_benchmark(self, tech_name: str, device_type: str = "medical_device") -> dict:
        """기술명 → 유사 임상 건수·평균 단계·평균 규모 벤치마킹"""
        data = self.search_trials(tech_name, limit=10)
        trials = data.get("trials", [])
        # search_trials는 "total" 키 반환, to_dict 전달 시 total_in_db 매핑 수정
        total_in_db = data.get("total", data.get("totalCount", 0))
        phases = [t["phase"] for t in trials if t.get("phase")]
        sponsors = [t["sponsor"] for t in trials if t.get("sponsor")]
        enrollments = [t["enrollment"] for t in trials if t.get("enrollment") and isinstance(t["enrollment"], (int, float))]
        return {
            "source":             "ClinicalTrials.gov v2",
            "tech_name":          tech_name,
            "similar_trials":     len(trials),
            "total_in_db":        total_in_db,
            "phase_distribution": phases,
            "avg_enrollment":     round(sum(enrollments) / len(enrollments)) if enrollments else None,
            "top_sponsors":       list(set(sponsors))[:5],
            "regulatory_signal":  self._regulatory_signal(len(trials), total_in_db),
            "trials":             trials[:5],
        }

    def eudamed_search(self, keyword: str, limit: int = 5) -> dict:
        """EUDAMED EU 의료기기 등록 검색"""
        try:
            params = urllib.parse.urlencode({"keyword": keyword, "page": 0, "size": limit})
            data = _cached_get(f"{_EUD}/actors?{params}", ttl_hours=72)
            items = data.get("data", {}).get("content", []) if isinstance(data.get("data"), dict) else []
            return {
                "source":   "EUDAMED (EU 의료기기 DB)",
                "keyword":  keyword,
                "total":    data.get("data", {}).get("totalElements", 0) if isinstance(data.get("data"), dict) else 0,
                "devices":  [
                    {
                        "name":    i.get("actorName", ""),
                        "country": i.get("countryIso", ""),
                        "role":    i.get("actorType", {}).get("code", ""),
                    }
                    for i in items[:limit]
                ],
            }
        except Exception as e:
            return {"source": "EUDAMED", "keyword": keyword, "error": str(e)[:80],
                    "portal": "https://ec.europa.eu/tools/eudamed"}

    def fda_device_clearance(self, device_name: str, limit: int = 5) -> dict:
        """FDA 510(k) 의료기기 승인 현황 — openFDA (무키 1,000/일, FDA_API_KEY 설정 시 120,000/일)"""
        try:
            encoded = urllib.parse.quote(device_name)
            url = (f"{_FDA}/device/510k.json"
                   f"?search=device_name:{encoded}&limit={limit}"
                   f"{_fda_key_param()}")
            data = _cached_get(url, ttl_hours=72)
            results = data.get("results", [])
            total_count = data.get("meta", {}).get("results", {}).get("total", len(results))
            return {
                "source":        "FDA openFDA 510(k)",
                "query":         device_name,
                "total_cleared": total_count,
                "api_limit":     "120,000/일 (키 설정)" if _fda_key_param() else "1,000/일 (무키)",
                "clearances": [
                    {
                        "k_number":    r.get("k_number", ""),
                        "device_name": r.get("device_name", ""),
                        "applicant":   r.get("applicant", ""),
                        "decision":    r.get("decision_description", ""),
                        "date":        r.get("decision_date", ""),
                        "product_code": r.get("product_code", ""),
                    }
                    for r in results[:limit]
                ],
            }
        except Exception as e:
            return {"source": "FDA 510(k)", "query": device_name, "error": str(e)[:80],
                    "note": "FDA_API_KEY 설정 시 한도 120배 확대 (open.fda.gov/apis/authentication/)"}

    def fda_adverse_events(self, device_name: str, limit: int = 5) -> dict:
        """FDA MAUDE 이상사례 DB — 기기 리스크 프로파일링"""
        try:
            encoded = urllib.parse.quote(device_name)
            url = (f"{_FDA}/device/event.json"
                   f"?search=device.brand_name:{encoded}&limit={limit}"
                   f"{_fda_key_param()}")
            data = _cached_get(url, ttl_hours=72)
            results = data.get("results", [])
            total_count = data.get("meta", {}).get("results", {}).get("total", 0)
            return {
                "source":       "FDA MAUDE 이상사례 DB",
                "query":        device_name,
                "total_events": total_count,
                "risk_signal":  "위험 모니터링 필요" if total_count > 100 else "이상사례 낮음",
                "events": [
                    {
                        "event_type": r.get("event_type", ""),
                        "date":       r.get("date_received", ""),
                        "outcome":    r.get("mdr_text", [{}])[0].get("text", "")[:80] if r.get("mdr_text") else "",
                    }
                    for r in results[:limit]
                ],
            }
        except Exception as e:
            return {"source": "FDA MAUDE", "query": device_name, "error": str(e)[:80]}

    def _regulatory_signal(self, similar: int, total: int) -> str:
        if total > 500:
            return "검증된 기술 (임상 다수 — 후발 진입 경쟁 높음)"
        if total > 50:
            return "성장 중 (임상 증가 — 적절한 진입 시점)"
        if total > 5:
            return "초기 단계 (임상 소수 — 선도자 기회)"
        return "미개척 (임상 없음 — 규제 불확실성 높음)"
