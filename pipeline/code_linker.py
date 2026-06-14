"""글로벌 코드 연결 파이프라인 — 7+4개 코드·DB 체계 통합
특허(IPC/CPC) → 기술(CPC-Y) → WIPO → 산업(NAICS) → 규제(CFR/CE) → 기업(LEI) → 정책(NTIS/ROR)
+ 논문(OpenAlex/PubMed) → 시장(WorldBank/OECD) → 임상(ClinicalTrials/EUDAMED) → ESG(ClimateTRACE/OWID)
"""
from __future__ import annotations
import json
import urllib.request
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────
# 결과 컨테이너
# ─────────────────────────────────────────────────────────
@dataclass
class CodeContext:
    tech_id:    str
    patent:     dict = field(default_factory=dict)   # IPC/CPC 특허 패밀리
    technology: dict = field(default_factory=dict)   # CPC-Y 기술분류
    wipo:       dict = field(default_factory=dict)   # PCT 출원 동향
    industry:   dict = field(default_factory=dict)   # NAICS/ISIC 산업
    regulatory: dict = field(default_factory=dict)   # CFR/CE/KFD 규제경로
    company:    dict = field(default_factory=dict)   # LEI/DUNS 기업
    policy:     dict = field(default_factory=dict)   # NTIS/ROR 정책·R&D
    # Phase 1 추가 — 즉시연결 DB
    paper:      dict = field(default_factory=dict)   # OpenAlex+PubMed+EuropePMC 논문
    market:     dict = field(default_factory=dict)   # WorldBank+OECD 시장·경제
    clinical:   dict = field(default_factory=dict)   # ClinicalTrials+EUDAMED 임상·규제
    esg:        dict = field(default_factory=dict)   # ClimateTRACE+OWID ESG·탄소
    trade:      dict = field(default_factory=dict)   # UN Comtrade 무역 흐름 (수출입·HS코드)
    # Phase 2 추가 — 8개 지역 통합 (KR·US·EU·JP·CN·IN·RU·DEV)
    regional:       dict = field(default_factory=dict)   # 지역별 IP·규제·자금·GTM·ESG
    route_decision: str  = ""                            # QueryRouter 라우팅 결과 (디버그)
    errors:     list = field(default_factory=list)

    def to_dict(self, *, debug: bool = False) -> dict:
        """결과 딕셔너리 변환. debug=True 시 route_decision 포함."""
        _skip = {"errors"} if debug else {"errors", "route_decision"}
        return {k: v for k, v in self.__dict__.items() if k not in _skip}


# ─────────────────────────────────────────────────────────
# 공통 HTTP 유틸
# ─────────────────────────────────────────────────────────
def _get(url: str, timeout: int = 8) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "IPInsight/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ─────────────────────────────────────────────────────────
# 1. 특허 — IPC / CPC  (USPTO PatentsView + EPO OPS)
# ─────────────────────────────────────────────────────────
class PatentConnector:
    """
    특허 검색 — 3단계 폴백:
      1. EPO OPS (developers.epo.org 무료 등록, EPO_CLIENT_ID + EPO_CLIENT_SECRET 설정)
      2. Google Patents JSON (무료·키 불필요, 실측 200 OK) — 1회 재시도
      3. 정적 CPC 분류 폴백
    코드 체계: IPC(A~H 8섹션) / CPC(IPC+Y확장)
    """

    _GOOGLE_PATENT   = "https://patents.google.com/xhr/query"
    _CROSSREF        = "https://api.crossref.org/works"
    _EPO_TOKEN_URL   = "https://ops.epo.org/3.2/auth/accesstoken"
    _EPO_SEARCH_URL  = "https://ops.epo.org/3.2/rest-services/published-data/search"
    _epo_bearer: str = ""          # 런타임 캐시 (OAuth2 Bearer)
    _epo_token_exp: float = 0.0    # 만료 epoch (초)

    def search_by_cpc(self, cpc_code: str, limit: int = 5) -> dict:
        """CPC 코드로 특허 검색 — EPO OPS → Google Patents JSON → 정적 폴백"""
        # EPO OPS 우선 (환경변수 EPO_CLIENT_ID + EPO_CLIENT_SECRET 설정 시)
        import os
        if os.environ.get("EPO_CLIENT_ID") and os.environ.get("EPO_CLIENT_SECRET"):
            token = self._get_epo_token()
            if token:
                result = self._epo_search(cpc_code, limit, token)
                if "error" not in result:
                    return result

        # Google Patents JSON (키 불필요, 200 OK 실측) — 503 시 1회 재시도
        last_err = None
        for attempt in range(2):
            try:
                if attempt > 0:
                    time.sleep(2)
                query = urllib.parse.quote(f"CPC={cpc_code}")
                url = (f"{self._GOOGLE_PATENT}?url=q%3D{query}"
                       f"%26before%3Dpriority%3A20260101"
                       f"%26after%3Dpriority%3A20230101%26num%3D{limit}")
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; IPInsight/1.0)",
                    "Accept": "application/json",
                })
                with urllib.request.urlopen(req, timeout=12) as r:
                    data = json.loads(r.read())
                patents = []
                for cluster in data.get("results", {}).get("cluster", []):
                    for item in cluster.get("result", []):
                        p = item.get("patent", {})
                        patents.append({
                            "id":       p.get("publication_number", ""),
                            "title":    p.get("title", ""),
                            "date":     p.get("filing_date", p.get("grant_date", "")),
                            "assignee": p.get("assignee", ""),
                            "abstract": p.get("abstract", "")[:200],
                        })
                return {
                    "source":      "Google Patents",
                    "cpc_query":   cpc_code,
                    "total_found": len(patents),
                    "patents":     patents[:limit],
                }
            except Exception as e:
                last_err = e
        return {
            "source":    "Google Patents → 정적 폴백 (503 일시오류)",
            "cpc_query": cpc_code,
            "error":     str(last_err)[:80],
            "fallback":  _cpc_static(cpc_code),
            "note":      "EPO OPS 무료 등록(developers.epo.org) 시 안정적 대체 가능",
        }

    def fto_landscape(self, ipc_codes: list[str]) -> dict:
        """IPC 코드 목록 → FTO 지형 (Google Patents 출원인 집계)"""
        results = {}
        for ipc in ipc_codes[:3]:
            try:
                cpc_q = ipc.replace(" ", "+")
                url = (f"{self._GOOGLE_PATENT}?url=q%3DCPC%3D{urllib.parse.quote(ipc)}"
                       f"%26before%3Dpriority%3A20260101%26after%3Dpriority%3A20200101%26num%3D20")
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; IPInsight/1.0)",
                    "Accept": "application/json",
                })
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read())
                assignees: dict[str, int] = {}
                total = 0
                for cluster in data.get("results", {}).get("cluster", []):
                    for item in cluster.get("result", []):
                        p = item.get("patent", {})
                        org = p.get("assignee", "Unknown") or "Unknown"
                        assignees[org] = assignees.get(org, 0) + 1
                        total += 1
                results[ipc] = {
                    "total_patents": total,
                    "top_assignees": sorted(assignees.items(), key=lambda x: -x[1])[:5],
                }
            except Exception as e:
                results[ipc] = {"error": str(e)[:60], "fallback": _cpc_static(ipc)}
        return {"source": "Google Patents", "fto_landscape": results}

    def _get_epo_token(self) -> str:
        """EPO OPS OAuth2 Bearer 토큰 획득 (20분 캐시)"""
        import os, base64
        if self._epo_bearer and time.time() < self._epo_token_exp - 60:
            return self._epo_bearer
        client_id = os.environ.get("EPO_CLIENT_ID", "")
        client_secret = os.environ.get("EPO_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            return ""
        try:
            credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            payload = b"grant_type=client_credentials"
            req = urllib.request.Request(
                self._EPO_TOKEN_URL,
                data=payload,
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            token = data.get("access_token", "")
            expires_in = int(data.get("expires_in", 1200))
            PatentConnector._epo_bearer = token
            PatentConnector._epo_token_exp = time.time() + expires_in
            return token
        except Exception:
            return ""

    def _epo_search(self, cpc_code: str, limit: int, token: str) -> dict:
        """EPO OPS — OAuth2 Bearer 토큰으로 CPC 검색"""
        try:
            url = (f"{self._EPO_SEARCH_URL}"
                   f"?q=cpc+any+%22{urllib.parse.quote(cpc_code)}%22&Range=1-{limit}")
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "IPInsight/1.0",
            })
            with urllib.request.urlopen(req, timeout=12) as r:
                raw = json.loads(r.read())
            # EPO OPS 응답 파싱 (JSON 포맷 선택 시)
            patents = []
            ops_response = raw.get("ops:world-patent-data", {})
            results = ops_response.get("ops:biblio-search", {}).get("ops:search-result", {})
            for entry in results.get("ops:publication-reference", []):
                doc = entry.get("document-id", {})
                # EPO OPS JSON: 값이 {"$": "DE"} 형태
                def _v(field): return doc.get(field, {}).get("$", "") if isinstance(doc.get(field), dict) else doc.get(field, "")
                country = _v("country")
                number  = _v("doc-number")
                kind    = _v("kind")
                patents.append({
                    "id":     f"{country}{number}.{kind}",
                    "source": "EPO OPS",
                    "cpc":    cpc_code,
                    "family_id": entry.get("@family-id", ""),
                })
            return {
                "source":      "EPO OPS",
                "cpc_query":   cpc_code,
                "total_found": len(patents),
                "patents":     patents[:limit] or [{"note": "EPO OPS 연결 성공 (결과 0건 또는 XML 응답)"}],
            }
        except Exception as e:
            return {"error": str(e)}

    def get_patent_detail(self, patent_id: str) -> dict:
        """EPO OPS 서지정보 조회 (출원인·발명자 등 특허 상세)
        patent_id 예: 'EP4755175.A1', 'DE102024136833.A1'
        """
        import os
        if not (os.environ.get("EPO_CLIENT_ID") and os.environ.get("EPO_CLIENT_SECRET")):
            return {"patent_id": patent_id, "error": "EPO OPS 인증 미설정 (.env 확인)"}
        token = self._get_epo_token()
        if not token:
            return {"patent_id": patent_id, "error": "EPO OPS 토큰 획득 실패"}
        try:
            safe_id = urllib.parse.quote(patent_id.replace(".", ""), safe="")
            url = (f"https://ops.epo.org/3.2/rest-services/published-data"
                   f"/publication/epodoc/{safe_id}/biblio")
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "IPInsight/1.0",
            })
            with urllib.request.urlopen(req, timeout=12) as r:
                raw = json.loads(r.read())
            bib = (raw.get("ops:world-patent-data", {})
                   .get("ops:biblio-search", raw)
                   .get("ops:publication-reference", {}))
            return {
                "source":        "EPO OPS",
                "patent_id":     patent_id,
                "bibliographic": bib,
            }
        except Exception as e:
            return {
                "patent_id": patent_id,
                "error":     str(e)[:120],
                "note":      "EPO OPS 서지정보 조회 실패 — 특허 ID 형식 확인",
            }


def _cpc_static(code: str) -> dict:
    """CPC 정적 분류 폴백 (API 오류 시)"""
    _MAP = {
        "Y02": "기후변화 완화 기술 (청정에너지·교통·건물·농업)",
        "A01": "농업·임업·축산·수산",
        "G06": "컴퓨팅·계산·카운팅",
        "H04": "전기통신",
        "C12": "생화학·미생물·유전공학",
        "A61": "의학·수의학·위생",
        "B60": "차량·운송",
        "F03": "기계·엔진·펌프",
    }
    prefix = code[:3]
    return {"cpc": code, "description": _MAP.get(prefix, "기타"), "note": "정적 폴백"}


# ─────────────────────────────────────────────────────────
# 2. 기술코드 — CPC-Y 신기술 서브섹션
# ─────────────────────────────────────────────────────────
class TechCodeConnector:
    """
    CPC-Y 섹션은 특허 내 기술분류 확장.
    Y02 = 기후기술, Y04 = 스마트그리드, Y10 = 기술 상호연결
    한국: 국가과학기술표준분류(KSTC) — NTIS API 연동
    """

    # CPC-Y 주요 기술 매핑 (정적 — EPO 공식)
    _CPC_Y = {
        "Y02A": "기후변화 적응",
        "Y02B": "건물 에너지효율",
        "Y02C": "탄소포집",
        "Y02D": "ICT 에너지효율",
        "Y02E": "청정에너지 생산",
        "Y02P": "생산공정 탄소저감",
        "Y02T": "교통 탄소저감",
        "Y02W": "폐기물·물 관리",
        "Y04S": "스마트그리드",
        "Y10S": "기술 응용 특허",
        "Y10T": "기술 분류 상호연결",
    }

    # 한국 국가과학기술표준분류(KSTC) 대분류
    _KSTC = {
        "NT": "나노기술",
        "BT": "생명공학기술",
        "IT": "정보통신기술",
        "ET": "환경기술",
        "ST": "우주항공기술",
        "CT": "문화기술",
        "MT": "제조기술",
        "AT": "농림수산식품기술",
    }

    def classify(self, cpc_codes: list[str], kstc_codes: list[str] = None) -> dict:
        """CPC-Y + KSTC 기술분류 매핑"""
        cpc_y = {c: self._CPC_Y[c] for c in cpc_codes if c in self._CPC_Y}
        kstc  = {k: self._KSTC[k]  for k in (kstc_codes or []) if k in self._KSTC}
        return {
            "source": "EPO CPC-Y (정적) + KSTC",
            "cpc_y_classifications": cpc_y,
            "kstc_classifications":  kstc,
            "tech_convergence": len(cpc_y) > 1,  # 복수 기술 융합 여부
        }

    def ntis_search(self, keyword: str, ntis_api_key: str = "") -> dict:
        """NTIS 국가R&D 과제 검색 (한국, API키 필요)"""
        if not ntis_api_key:
            return {"source": "NTIS", "note": "API키 미설정 — .env NTIS_API_KEY 설정 필요",
                    "portal": "https://www.ntis.go.kr/rndopen/"}
        try:
            url = (f"https://www.ntis.go.kr/rndopen/api/v1/project?"
                   f"serviceKey={ntis_api_key}&searchKeyword={urllib.parse.quote(keyword)}&numOfRows=5")
            data = _get(url)
            return {"source": "NTIS", "results": data}
        except Exception as e:
            return {"source": "NTIS", "error": str(e)}


# ─────────────────────────────────────────────────────────
# 3. WIPO — PCT 출원·Nice분류·국가코드
# ─────────────────────────────────────────────────────────
class WIPOConnector:
    """
    API: WIPO PATENTSCOPE (무료, 키 불필요)
         https://patentscope.wipo.int/search/en/result.jsf
    API: WIPO Global Brand DB (상표, 무료)
    코드: PCT ST.3 국가코드 / Nice 상품·서비스 분류(1~45류)
    """

    # WIPO PCT 주요 출원국 코드 (ST.3)
    _PCT_COUNTRIES = {
        "US": "미국 (USPTO)", "EP": "유럽 (EPO)", "CN": "중국 (CNIPA)",
        "JP": "일본 (JPO)", "KR": "한국 (KIPO)", "DE": "독일", "GB": "영국",
        "FR": "프랑스", "IN": "인도", "CA": "캐나다", "AU": "호주",
        "IL": "이스라엘", "SG": "싱가포르", "WO": "PCT 국제출원",
    }

    # Nice 분류 주요 류 (기술사업화 연관)
    _NICE_TECH = {
        9:  "소프트웨어·전자기기·AI",
        10: "의료기기",
        11: "환경·에너지 기기",
        35: "기업경영·B2B 서비스",
        36: "금융·핀테크",
        38: "통신·플랫폼",
        40: "제조·가공",
        42: "R&D·SaaS·클라우드",
        44: "의료·농업 서비스",
        45: "법률·IP 서비스",
    }

    def pct_strategy(self, target_markets: list[str], nice_classes: list[int] = None) -> dict:
        """목표 시장 → PCT 출원 전략 + Nice 분류 매핑"""
        countries = {m: self._PCT_COUNTRIES.get(m, m) for m in target_markets}
        nice = {n: self._NICE_TECH.get(n, "기타") for n in (nice_classes or [])}
        priority_order = ["US", "EP", "CN", "JP", "KR"]  # 표준 PCT 우선 순위
        recommended = [c for c in priority_order if c in target_markets]
        return {
            "source": "WIPO PCT ST.3",
            "target_countries": countries,
            "recommended_priority": recommended,
            "nice_classifications": nice,
            "pct_deadline_months": 30,  # 우선일로부터 30개월 국내단계 진입
            "paris_convention_months": 12,
            "portal": "https://patentscope.wipo.int",
        }

    def patentscope_search(self, query: str, country: str = "WO") -> dict:
        """PATENTSCOPE 검색 (공개 웹, 직접 API 미지원 → 링크 반환)"""
        encoded = urllib.parse.quote(query)
        return {
            "source": "WIPO PATENTSCOPE",
            "query": query,
            "search_url": f"https://patentscope.wipo.int/search/en/result.jsf?query={encoded}",
            "bulk_data": "https://www.wipo.int/patentscope/en/data/",
            "note": "PATENTSCOPE는 직접 API 미제공 — 웹 검색 또는 Bulk XML 다운로드 활용",
        }


# ─────────────────────────────────────────────────────────
# 4. 산업코드 — NAICS / ISIC / KSIC
# ─────────────────────────────────────────────────────────
class IndustryConnector:
    """
    API: US Census NAICS API (무료)
         https://api.census.gov/data/2022/naics
    표준: NAICS 2022 (북미) / ISIC Rev.4 (UN) / KSIC (한국)
    """

    CENSUS_API = "https://api.census.gov/data/2022/naics"

    # 한국어 → 영어 기술키워드 간이 번역 (Census NAICS API 영문 매칭용)
    _KO_EN_MAP = {
        "스마트팜": "agriculture smart", "농업": "agriculture", "축산": "livestock",
        "의료기기": "medical devices", "의료": "health care", "바이오": "biotechnology",
        "소프트웨어": "software", "인공지능": "computer systems", "AI": "computer systems",
        "에너지": "electric power", "태양광": "electric power", "배터리": "electrical equipment",
        "반도체": "semiconductor electronic", "통신": "telecommunications",
        "자동차": "motor vehicle", "로봇": "manufacturing machinery",
        "식품": "food manufacturing", "화학": "chemical manufacturing",
        "건설": "construction", "물류": "transportation logistics",
        "핀테크": "financial activities", "교육": "educational services",
        "환경": "waste management", "제약": "pharmaceutical",
    }

    def _translate_keyword(self, keyword: str) -> str:
        """한국어 키워드 → 영어 변환 (Census API 영문 레이블 매칭용)"""
        for ko, en in self._KO_EN_MAP.items():
            if ko in keyword:
                return en
        return keyword  # 이미 영문이거나 미지원 → 원본 반환

    # NAICS 2자리 주요 섹터
    _NAICS_SECTORS = {
        "11": "농림어업", "21": "광업", "22": "공공서비스",
        "23": "건설", "31": "제조(식품·섬유)", "32": "제조(화학·플라스틱)",
        "33": "제조(금속·기계·전자)", "42": "도매유통", "44": "소매",
        "48": "운송·물류", "51": "정보·미디어·SW", "52": "금융·보험",
        "54": "전문과학기술서비스", "56": "경영지원·폐기물",
        "61": "교육", "62": "의료·사회복지", "71": "예술·엔터",
        "72": "숙박·외식", "92": "공공행정",
    }

    def search_naics(self, keyword: str, api_key: str = "") -> dict:
        """NAICS 코드 키워드 검색 (한국어 키워드 자동 영문 변환)"""
        en_keyword = self._translate_keyword(keyword)
        try:
            key_param = f"&key={api_key}" if api_key else ""
            url = f"{self.CENSUS_API}?get=NAICS2022,NAICS2022_LABEL&for=us:*{key_param}"
            data = _get(url)
            matched = [row for row in data[1:]
                       if en_keyword.lower() in row[1].lower()][:5]
            return {
                "source":     "US Census NAICS 2022",
                "keyword":    keyword,
                "translated": en_keyword if en_keyword != keyword else None,
                "matches":    [{"code": r[0], "label": r[1]} for r in matched],
            }
        except Exception:
            matched = [(k, v) for k, v in self._NAICS_SECTORS.items()
                       if en_keyword.lower() in v.lower() or keyword.lower() in v.lower()]
            return {
                "source":     "NAICS 2022 (정적 폴백)",
                "keyword":    keyword,
                "translated": en_keyword if en_keyword != keyword else None,
                "matches":    [{"code": k, "label": v} for k, v in matched[:5]],
                "full_api":   "https://api.census.gov/data/2022/naics",
            }

    def isic_map(self, naics_code: str) -> dict:
        """NAICS → ISIC Rev.4 매핑 (UN 표준, 정적)"""
        _NAICS_TO_ISIC = {
            "11": "A", "21": "B", "22": "D/E", "23": "F",
            "31": "C", "32": "C", "33": "C",
            "42": "G", "44": "G", "48": "H",
            "51": "J", "52": "K", "54": "M",
            "61": "P", "62": "Q", "92": "O",
        }
        prefix = naics_code[:2]
        isic = _NAICS_TO_ISIC.get(prefix, "N/A")
        return {"naics": naics_code, "isic_rev4": isic,
                "source": "UN ISIC Rev.4 정적 매핑"}


# ─────────────────────────────────────────────────────────
# 5. 규제코드 — CFR(미국) / CE(EU) / 식약처(KR)
# ─────────────────────────────────────────────────────────
class RegulatoryConnector:
    """
    API: eCFR (US CFR, 무료) — https://www.ecfr.gov/api/versioner/v1/
    API: EUR-Lex (EU, 무료)  — https://eur-lex.europa.eu/
    API: 식약처 공공데이터 (KR, 무료키)
    """

    # 기술 유형 → 규제 경로 매핑
    _REGULATORY_MAP = {
        "medical_device": {
            "US":  {"code": "21 CFR Part 820", "body": "FDA", "path": "510(k)/PMA"},
            "EU":  {"code": "MDR 2017/745",     "body": "CE", "path": "CE Mark Class I/II/III"},
            "KR":  {"code": "의료기기법",         "body": "MFDS", "path": "1~4등급 허가"},
        },
        "food_supplement": {
            "US":  {"code": "21 CFR Part 111",  "body": "FDA", "path": "GRAS/DSHEA"},
            "EU":  {"code": "EU 2002/46/EC",    "body": "EFSA", "path": "Novel Food"},
            "KR":  {"code": "건강기능식품법",       "body": "MFDS", "path": "개별인정형"},
        },
        "software_saas": {
            "US":  {"code": "21 CFR Part 11",   "body": "FDA/FTC", "path": "SaMD (해당시)"},
            "EU":  {"code": "GDPR + AI Act",    "body": "DPA",  "path": "Risk Class"},
            "KR":  {"code": "개인정보보호법+ISMS", "body": "KISA", "path": "ISMS-P 인증"},
        },
        "agritech": {
            "US":  {"code": "7 CFR",             "body": "USDA", "path": "USDA Organic/GAP"},
            "EU":  {"code": "EU GAP",            "body": "EUROPA", "path": "GlobalG.A.P."},
            "KR":  {"code": "농약관리법+스마트팜법", "body": "MAFRA", "path": "스마트농업법 인증"},
        },
        "energy": {
            "US":  {"code": "10 CFR",            "body": "DOE",  "path": "Energy Star"},
            "EU":  {"code": "EU ETS + RED II",   "body": "ENTSO", "path": "RE100/녹색인증"},
            "KR":  {"code": "에너지법+신재생에너지법", "body": "MOTIE", "path": "REC 인증"},
        },
    }

    def get_regulatory_path(self, tech_type: str, markets: list[str]) -> dict:
        """기술 유형 + 목표 시장 → 규제 경로"""
        path_map = self._REGULATORY_MAP.get(tech_type, {})
        result = {m: path_map.get(m, {"note": "규제경로 DB 없음 — 전문가 확인 필요"})
                  for m in markets}
        return {
            "source": "eCFR / EUR-Lex / MFDS (정적 매핑)",
            "tech_type": tech_type,
            "regulatory_paths": result,
            "ecfr_api":   "https://www.ecfr.gov/api/versioner/v1/",
            "eurlex_api": "https://eur-lex.europa.eu/content/tools/eur-lex-celex-api.html",
        }

    def ecfr_search(self, title: int, part: int) -> dict:
        """eCFR 특정 Title/Part 조회 (무료 API)"""
        try:
            url = f"https://www.ecfr.gov/api/versioner/v1/structure/current/title-{title}.json"
            data = _get(url)
            return {"source": "eCFR", "title": title, "part": part,
                    "structure": str(data)[:300]}
        except Exception as e:
            return {"source": "eCFR", "error": str(e),
                    "url": f"https://www.ecfr.gov/current/title-{title}/part-{part}"}


# ─────────────────────────────────────────────────────────
# 6. 기업코드 — LEI / D-U-N-S / OpenCorporates
# ─────────────────────────────────────────────────────────
class CompanyConnector:
    """
    API: GLEIF LEI (무료, 키 불필요) — https://api.gleif.org/api/v1/
    API: OpenCorporates (무료 제한) — https://api.opencorporates.com/v0.4/
    코드: LEI(글로벌법인식별자 20자리) / D-U-N-S(Dun&Bradstreet, 유료) / BRN(사업자등록)
    """

    GLEIF_API        = "https://api.gleif.org/api/v1"
    OPENCORP_API     = "https://api.opencorporates.com/v0.4"

    def search_lei(self, company_name: str) -> dict:
        """회사명 → LEI 코드 조회 (GLEIF, 무료) — /lei-records?filter[entity.legalName] 사용"""
        try:
            encoded = urllib.parse.quote(company_name)
            # fuzzycompletions는 400 오류 → lei-records filter 방식 사용 (실측 200 OK)
            url = (f"{self.GLEIF_API}/lei-records"
                   f"?filter[entity.legalName]={encoded}&page[size]=5")
            req = urllib.request.Request(url, headers={
                "Accept": "application/vnd.api+json",
                "User-Agent": "IPInsight/1.0",
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            entities = data.get("data", [])[:5]
            return {
                "source":  "GLEIF LEI Registry",
                "query":   company_name,
                "total":   data.get("meta", {}).get("total", len(entities)),
                "results": [
                    {
                        "lei":        e.get("id", ""),
                        "legal_name": e.get("attributes", {}).get("entity", {})
                                       .get("legalName", {}).get("name", ""),
                        "country":    e.get("attributes", {}).get("entity", {})
                                       .get("legalAddress", {}).get("country", ""),
                        "status":     e.get("attributes", {}).get("entity", {}).get("status", ""),
                        "jurisdiction": e.get("attributes", {}).get("entity", {}).get("jurisdiction", ""),
                    }
                    for e in entities
                ],
            }
        except Exception as e:
            return {"source": "GLEIF", "error": str(e),
                    "portal": "https://www.gleif.org/en/lei-data/gleif-lei-look-up-api"}

    def get_lei_detail(self, lei_code: str) -> dict:
        """LEI 코드 → 기업 상세 (GLEIF)"""
        try:
            data = _get(f"{self.GLEIF_API}/lei-records/{lei_code}")
            attr = data.get("data", {}).get("attributes", {})
            return {
                "source":       "GLEIF",
                "lei":          lei_code,
                "legal_name":   attr.get("entity", {}).get("legalName", {}).get("name"),
                "status":       attr.get("entity", {}).get("status"),
                "jurisdiction": attr.get("entity", {}).get("jurisdiction"),
                "hq_country":   attr.get("entity", {}).get("legalAddress", {}).get("country"),
            }
        except Exception as e:
            return {"source": "GLEIF", "lei": lei_code, "error": str(e)}

    def search_opencorporates(self, company_name: str, jurisdiction: str = "") -> dict:
        """OpenCorporates 기업 검색 (무료 제한: 500req/월)"""
        try:
            params = urllib.parse.urlencode({"q": company_name, "jurisdiction_code": jurisdiction})
            data = _get(f"{self.OPENCORP_API}/companies/search?{params}")
            companies = data.get("results", {}).get("companies", [])[:3]
            return {
                "source": "OpenCorporates",
                "results": [
                    {
                        "name":         c.get("company", {}).get("name"),
                        "number":       c.get("company", {}).get("company_number"),
                        "jurisdiction": c.get("company", {}).get("jurisdiction_code"),
                        "status":       c.get("company", {}).get("current_status"),
                    }
                    for c in companies
                ],
            }
        except Exception as e:
            return {"source": "OpenCorporates", "error": str(e)}


# ─────────────────────────────────────────────────────────
# 7. 정책코드 — NTIS(KR) / ROR / Dimensions
# ─────────────────────────────────────────────────────────
class PolicyConnector:
    """
    API: ROR (Research Organization Registry, 무료) — https://api.ror.org/
    API: Dimensions (연구비·논문, 무료 제한) — https://app.dimensions.ai/
    API: NTIS (한국, 공공데이터포털 키 필요)
    코드: ROR ID (기관), GRID (전 ROR), NTIS 과제번호
    """

    ROR_API = "https://api.ror.org/organizations"

    def search_ror(self, org_name: str) -> dict:
        """기관명 → ROR ID (연구기관·대학·정부기관)"""
        try:
            params = urllib.parse.urlencode({"query": org_name})
            data = _get(f"{self.ROR_API}?{params}")
            items = data.get("items", [])[:5]
            return {
                "source": "ROR (Research Organization Registry)",
                "query":  org_name,
                "results": [
                    {
                        "ror_id":   i.get("id"),
                        "name":     i.get("name"),
                        "country":  i.get("country", {}).get("country_name"),
                        "type":     i.get("types", []),
                    }
                    for i in items
                ],
            }
        except Exception as e:
            return {"source": "ROR", "error": str(e), "portal": "https://ror.org/"}

    def policy_programs(self, tech_type: str, country: str = "KR") -> dict:
        """기술 유형 + 국가 → 정책 지원 프로그램 매핑 (정적)"""
        _PROGRAMS = {
            "KR": {
                "agritech":       ["농식품 기술사업화 펀드(농진청)", "스마트팜 혁신밸리(농림부)", "TIPS 농업특화"],
                "medical_device": ["범부처 전주기 의료기기연구개발", "첨단의료기기 GMP 지원(NIPA)"],
                "software_saas":  ["TIPS(중기부)", "K-Global 300", "디지털뉴딜 데이터바우처"],
                "energy":         ["에너지기술개발사업(MOTIE)", "그린뉴딜 RE100", "탄소중립 기술개발"],
                "default":        ["TIPS", "신기술창업전문회사", "기술보증기금(KIBO)"],
            },
            "US": {
                "agritech":       ["USDA SBIR", "NRCS EQIP"],
                "medical_device": ["NIH SBIR", "FDA Breakthrough Device"],
                "software_saas":  ["NSF SBIR", "DoD SBIR Phase I/II"],
                "energy":         ["DOE ARPA-E", "DOE SunShot"],
                "default":        ["SBA SBIR", "NSF I-Corps"],
            },
            "EU": {
                "default":        ["EIC Accelerator", "Horizon Europe", "EIF VC"],
            },
        }
        country_programs = _PROGRAMS.get(country, _PROGRAMS["KR"])
        programs = country_programs.get(tech_type, country_programs.get("default", []))
        return {
            "source":   "정책 DB (정적 + NTIS)",
            "country":  country,
            "tech_type": tech_type,
            "programs": programs,
            "ntis_portal": "https://www.ntis.go.kr/",
            "sbir_portal": "https://www.sbir.gov/",
            "eic_portal":  "https://eic.ec.europa.eu/",
        }


# ─────────────────────────────────────────────────────────
# 통합 파이프라인
# ─────────────────────────────────────────────────────────
class CodeLinkerPipeline:
    """7+4개 코드·DB 체계를 순서대로 연결하여 CodeContext 생성"""

    def __init__(self):
        self.patent     = PatentConnector()
        self.tech       = TechCodeConnector()
        self.wipo       = WIPOConnector()
        self.industry   = IndustryConnector()
        self.regulatory = RegulatoryConnector()
        self.company    = CompanyConnector()
        self.policy     = PolicyConnector()
        # Phase 1 Connectors (즉시연결 DB)
        try:
            from pipeline.connectors import (PaperConnector, MarketConnector,
                                              ClinicalConnector, ESGConnector, TradeConnector)
            from pipeline.connectors.regional_connector import RegionalConnector
        except ImportError:
            from connectors import (PaperConnector, MarketConnector,
                                    ClinicalConnector, ESGConnector, TradeConnector)
            from connectors.regional_connector import RegionalConnector
        self.paper    = PaperConnector()
        self.market   = MarketConnector()
        self.clinical = ClinicalConnector()
        self.esg      = ESGConnector()
        self.trade    = TradeConnector()
        self.regional = RegionalConnector()

    def run(self, tech_id: str, params: dict, stage: str = "ALL") -> CodeContext:
        """
        params:
          cpc_codes        list[str]   예: ["Y02E", "A01G"]
          ipc_codes        list[str]   예: ["A01G 31/00"]
          kstc_codes       list[str]   예: ["AT", "IT"]
          target_markets   list[str]   예: ["US", "EP", "KR"]
          nice_classes     list[int]   예: [42, 9]
          industry_keyword str         예: "농업"
          naics_code       str         예: "111"
          tech_type        str         예: "agritech"
          reg_markets      list[str]   예: ["US", "EU", "KR"]
          company_name     str         예: "Samsung Electronics"
          org_name         str         예: "KAIST"
          policy_country   str         예: "KR"
          ntis_api_key     str         (선택)

        stage: G0~G10 또는 "ALL" — QueryRouter가 불필요한 커넥터를 자동 스킵
        """
        from pipeline.query_router import QueryRouter
        _regions    = params.get("target_markets", ["KR"])
        _tech_type  = params.get("tech_type", "software_saas")
        _decision   = QueryRouter().route(stage, _tech_type, _regions)
        _active     = set(_decision.connectors)  # 이 스테이지에서 실행할 커넥터 집합

        ctx = CodeContext(tech_id=tech_id)
        ctx.route_decision = _decision.summary()

        # ── 커넥터별 작업 클로저 정의 (ALL 스테이지 36.5s → <10s 병렬화) ───────
        import os as _os
        _jobs: dict = {}

        if "patent" in _active:
            _cpc = params.get("cpc_codes", ["A01"])[0]
            _ipc = params.get("ipc_codes", [_cpc])
            def _j_patent(_c=_cpc, _i=_ipc):
                return {
                    "cpc_search":    self.patent.search_by_cpc(_c, limit=3),
                    "fto_landscape": self.patent.fto_landscape(_i),
                }
            _jobs["patent"] = _j_patent

        if "technology" in _active:
            _ntis_key = params.get("ntis_api_key") or _os.environ.get("NTIS_API_KEY", "")
            def _j_tech(_k=_ntis_key):
                result = self.tech.classify(
                    params.get("cpc_codes", []),
                    params.get("kstc_codes", []),
                )
                if _k:
                    result["ntis"] = self.tech.ntis_search(
                        params.get("industry_keyword", ""), _k
                    )
                return result
            _jobs["technology"] = _j_tech

        if "wipo" in _active:
            def _j_wipo():
                return self.wipo.pct_strategy(
                    params.get("target_markets", ["US", "EP", "KR"]),
                    params.get("nice_classes", [42]),
                )
            _jobs["wipo"] = _j_wipo

        if "industry" in _active:
            _kw      = params.get("industry_keyword", "")
            _naics_c = params.get("naics_code", "54")
            def _j_industry(_k=_kw, _n=_naics_c):
                return {
                    "naics_search": self.industry.search_naics(_k),
                    "isic_map":     self.industry.isic_map(_n),
                }
            _jobs["industry"] = _j_industry

        if "regulatory" in _active:
            def _j_regulatory():
                return self.regulatory.get_regulatory_path(
                    params.get("tech_type", "software_saas"),
                    params.get("reg_markets", ["US", "EU", "KR"]),
                )
            _jobs["regulatory"] = _j_regulatory

        if "company" in _active:
            _company = params.get("company_name", "")
            if _company:
                def _j_company(_c=_company):
                    return self.company.search_lei(_c)
                _jobs["company"] = _j_company

        if "policy" in _active:
            _org = params.get("org_name", "")
            def _j_policy(_o=_org):
                return {
                    "programs":   self.policy.policy_programs(
                        params.get("tech_type", "software_saas"),
                        params.get("policy_country", "KR"),
                    ),
                    "ror_search": self.policy.search_ror(_o) if _o else {},
                }
            _jobs["policy"] = _j_policy

        if "paper" in _active:
            _q = params.get("tech_name", params.get("industry_keyword", ""))
            if _q:
                def _j_paper(_qq=_q):
                    return self.paper.trl_evidence(_qq)
                _jobs["paper"] = _j_paper

        if "market" in _active:
            def _j_market():
                return self.market.market_summary(
                    params.get("tech_type", "software_saas"),
                    params.get("target_markets", ["US", "KR"]),
                )
            _jobs["market"] = _j_market

        if "clinical" in _active:
            _tn = params.get("tech_name", params.get("industry_keyword", ""))
            _tt = params.get("tech_type", "medical_device")
            if _tn:
                def _j_clinical(_n=_tn, _t=_tt):
                    result = self.clinical.regulatory_benchmark(_n, _t)
                    if _t == "medical_device":
                        result["fda_510k"] = self.clinical.fda_device_clearance(_n)
                    return result
                _jobs["clinical"] = _j_clinical

        if "esg" in _active:
            _sector_map = {
                "agritech": "agriculture", "energy": "power",
                "manufacturing": "manufacturing", "software_saas": "buildings",
            }
            _ct_sector = _sector_map.get(params.get("tech_type", ""), "manufacturing")
            def _j_esg(_s=_ct_sector):
                return self.esg.esg_summary(
                    params.get("tech_type", ""),
                    _s,
                    params.get("efficiency_pct", 10.0),
                    params.get("target_markets", ["KR"]),
                )
            _jobs["esg"] = _j_esg

        if "regional" in _active:
            def _j_regional():
                return self.regional.analyze(
                    _regions, _tech_type, params.get("efficiency_pct", 10.0)
                ).to_dict()
            _jobs["regional"] = _j_regional

        if "trade" in _active:
            def _j_trade():
                return self.trade.sector_trade_summary(
                    _tech_type,
                    reporters=_regions[:5],
                    period=params.get("trade_period", "2022"),
                )
            _jobs["trade"] = _j_trade

        # ── 병렬 실행 (ThreadPoolExecutor, 최대 8스레드) ──────────────────────
        if _jobs:
            with ThreadPoolExecutor(max_workers=min(len(_jobs), 8)) as pool:
                fs = {pool.submit(fn): name for name, fn in _jobs.items()}
                for future in as_completed(fs):
                    name = fs[future]
                    try:
                        result = future.result(timeout=30)
                        if result is not None:
                            setattr(ctx, name, result)
                    except Exception as e:
                        ctx.errors.append(f"{name}: {e}")

        return ctx


# ─────────────────────────────────────────────────────────
# CLI 테스트
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    pipeline = CodeLinkerPipeline()
    ctx = pipeline.run("DEMO-001", {
        "cpc_codes":        ["Y02E", "A01G"],
        "ipc_codes":        ["A01G 31/00"],
        "kstc_codes":       ["AT", "ET"],
        "target_markets":   ["US", "EP", "KR"],
        "nice_classes":     [44, 42],
        "industry_keyword": "농업",
        "naics_code":       "111",
        "tech_type":        "agritech",
        "reg_markets":      ["US", "EU", "KR"],
        "company_name":     "Samsung Electronics",
        "org_name":         "Seoul National University",
        "policy_country":   "KR",
    })
    print(json.dumps(ctx.to_dict(), ensure_ascii=False, indent=2))
