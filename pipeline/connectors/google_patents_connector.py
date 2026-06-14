"""Google Patents 스크레이퍼 — API 키 불필요 (httpx + BeautifulSoup)

포팅 출처: ip-insight-handoff/app/lib/google-patents.ts

지원:
  - KR/US/EP/PCT 특허번호 정규화
  - Google Patents HTML 파싱 (청구항·초록·서지정보·패밀리)
  - KIPRIS 실패 시 폴백 경로
"""
from __future__ import annotations

import re
import time
from typing import Optional

import httpx

_BASE_URL = "https://patents.google.com/patent/{}/en"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}
_TIMEOUT = 20.0
_RATE_LIMIT_DELAY = 1.0   # Google 요청 간 최소 간격(초)
_last_request: float = 0.0


def _normalize_patent_number(patent_id: str) -> str:
    """특허번호를 Google Patents 검색 형식으로 정규화."""
    raw = patent_id.strip().upper()
    raw = re.sub(r"[\s\-]", "", raw)

    # KR10-YYYY-XXXXXXX → KR10YYYYXXXXXXX
    if raw.startswith("KR"):
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 10:
            return f"KR{digits}"
        return raw

    # US 특허
    if raw.startswith("US"):
        return raw

    # PCT (WO)
    if raw.startswith("WO"):
        return raw

    # EP
    if raw.startswith("EP"):
        return raw

    # 순수 숫자 → KR 가정
    if re.fullmatch(r"\d+", raw):
        return f"KR{raw}"

    return raw


def _get_search_variants(patent_id: str) -> list[str]:
    """Google Patents URL에서 시도할 번호 변형 목록."""
    norm = _normalize_patent_number(patent_id)
    variants = [norm]

    # Kind code 제거 변형
    without_kind = re.sub(r"[A-Z]\d*$", "", norm)
    if without_kind != norm:
        variants.append(without_kind)

    return variants


def _parse_html(html: str, source_url: str) -> Optional[dict]:
    """Google Patents HTML에서 필요한 정보를 추출한다.

    BeautifulSoup이 없는 환경을 위해 순수 정규식 폴백 포함.
    """
    try:
        from bs4 import BeautifulSoup
        return _parse_html_bs4(html, source_url)
    except ImportError:
        return _parse_html_regex(html, source_url)


def _parse_html_bs4(html: str, source_url: str) -> Optional[dict]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # 제목
    title_el = soup.select_one("h1.title, span[itemprop='name']")
    title = title_el.get_text(strip=True) if title_el else ""

    # 초록
    abstract_el = soup.select_one(".abstract, div[itemprop='content']")
    abstract = abstract_el.get_text(strip=True) if abstract_el else ""

    # 청구항
    claim_els = soup.select(".claims .claim-text, .claim")
    claims: list[dict] = []
    for i, el in enumerate(claim_els):
        text = el.get_text(strip=True)
        if not text:
            continue
        is_independent = "claim-dependent" not in el.get("class", [])
        dep_match = re.search(r"청구항\s*(\d+)", text) or re.search(r"[Cc]laim\s+(\d+)", text)
        depends_on = int(dep_match.group(1)) if dep_match and not is_independent else None
        claims.append({
            "number": i + 1,
            "text": text,
            "is_independent": is_independent,
            "depends_on": depends_on,
        })

    # 서지정보
    def _meta(prop: str) -> str:
        el = soup.select_one(f"[itemprop='{prop}']")
        return el.get_text(strip=True) if el else ""

    # 명세서 요약
    desc_el = soup.select_one(".description")
    description = desc_el.get_text(strip=True)[:3000] if desc_el else ""

    # IPC/CPC 코드
    ipc_codes = [el.get_text(strip=True) for el in soup.select(".classification-ipc .badge")]
    cpc_codes = [el.get_text(strip=True) for el in soup.select(".classification-cpc .badge")]

    # 패밀리
    family_els = soup.select(".family-list-item a, .related-patent a")
    family_members = list({el.get_text(strip=True) for el in family_els if el.get_text(strip=True)})

    claim_text = "\n".join(f"청구항 {c['number']}. {c['text']}" for c in claims)
    full_text = f"{title}\n\n[초록]\n{abstract}\n\n[청구항]\n{claim_text}"

    if not title and not abstract and not claims:
        return None

    return {
        "title": title,
        "abstract": abstract,
        "description": description,
        "claims": claims,
        "claims_text": claim_text,
        "text": full_text,
        "applicant": _meta("assignee"),
        "inventors": [el.get_text(strip=True) for el in soup.select("[itemprop='inventor']")],
        "filing_date": _meta("filingDate"),
        "publication_date": _meta("publicationDate"),
        "priority_date": _meta("priorityDate"),
        "ipc_codes": ipc_codes,
        "cpc_codes": cpc_codes,
        "claim_stats": {
            "total_count": len(claims),
            "independent_count": sum(1 for c in claims if c["is_independent"]),
            "dependent_count": sum(1 for c in claims if not c["is_independent"]),
        },
        "family_info": {
            "family_members": family_members,
            "total_family_count": len(family_members),
        },
        "source_url": source_url,
        "source": "google_patents",
    }


def _parse_html_regex(html: str, source_url: str) -> Optional[dict]:
    """BeautifulSoup 없이 정규식으로 최소 정보 추출 (폴백)."""
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
    title = re.sub(r"\s*-\s*Google Patents", "", title_m.group(1).strip() if title_m else "")

    abstract_m = re.search(r'class="abstract"[^>]*>(.*?)</div>', html, re.DOTALL)
    abstract = re.sub(r"<[^>]+>", " ", abstract_m.group(1) if abstract_m else "").strip()

    if not title and not abstract:
        return None

    return {
        "title": title,
        "abstract": abstract,
        "claims": [],
        "claims_text": "",
        "text": f"{title}\n\n[초록]\n{abstract}",
        "source_url": source_url,
        "source": "google_patents_regex_fallback",
    }


def fetch_from_google_patents(patent_id: str) -> Optional[dict]:
    """Google Patents에서 특허 정보를 스크레이핑한다.

    반환값: {title, abstract, claims, text, ...} 또는 None
    """
    global _last_request
    variants = _get_search_variants(patent_id)

    for variant in variants:
        url = _BASE_URL.format(variant)

        # Rate limiting
        elapsed = time.time() - _last_request
        if elapsed < _RATE_LIMIT_DELAY:
            time.sleep(_RATE_LIMIT_DELAY - elapsed)

        try:
            resp = httpx.get(url, headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True)
            _last_request = time.time()

            if resp.status_code == 404:
                continue
            if resp.status_code != 200:
                continue

            data = _parse_html(resp.text, str(resp.url))
            if data:
                data["patent_number"] = variant
                return data
        except Exception:
            _last_request = time.time()
            continue

    return None


class GooglePatentsConnector:
    """Google Patents 커넥터 — KIPRIS 폴백 또는 해외 특허 수집용."""

    name = "google_patents"

    def fetch(self, patent_id: str) -> Optional[dict]:
        """특허번호로 Google Patents 스크레이핑. 실패 시 None."""
        return fetch_from_google_patents(patent_id)

    def available(self) -> bool:
        """httpx 설치 여부로 가용성 판단 (키 불필요)."""
        try:
            import httpx  # noqa: F401
            return True
        except ImportError:
            return False
