"""KIPRIS 커넥터 — 한국 특허 XML API (키 필요: KIPRIS_API_KEY)

포팅 출처: ip-insight-handoff/app/lib/tools/phase1-fetch/kipris.ts

지원:
  - KR 출원번호 정규화 (10xxxxxxxxx, KR10-xxxx-xxxxxxx, 13자리 등록번호 처리)
  - KIPRIS Plus API: getBibliographyDetailInfoSearch (서지사항 + 요약 + 청구항)
  - API 키 미설정 시 None 반환 (폴백 허용)
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Optional

import httpx

_KIPRIS_API_URL = (
    "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice"
    "/getBibliographyDetailInfoSearch"
)
_TIMEOUT = 15.0


def _build_application_candidates(patent_id: str) -> list[str]:
    """다양한 KR 특허번호 형식을 KIPRIS 출원번호 후보로 정규화.

    처리 형식:
      KR10-2021-0123456  → 1020210123456
      KR10-1234567       → 1020100000000 식 13자리 등록번호 처리 필요 없음
      10xxxxxxxxx (11자리) → 그대로
      13자리 등록번호(1012345678901) → 앞 10자리 추출 (KIPRIS 출원번호는 10자리)
    """
    raw = re.sub(r"[\s\-]", "", patent_id.upper().replace("KR", ""))

    candidates: list[str] = []

    # 순수 숫자만 남은 경우
    digits = re.sub(r"\D", "", raw)

    if len(digits) == 13:
        # 13자리 등록번호: 뒤 3자리(종별코드) 제거 → 10자리 출원번호
        candidates.append(digits[:10])
    elif len(digits) >= 10:
        candidates.append(digits[:11] if len(digits) >= 11 else digits)
        candidates.append(digits[:10])
    else:
        # 짧은 번호: 앞에 10 붙여 시도
        candidates.append(f"10{digits}")

    # 중복 제거, 순서 유지
    seen: set[str] = set()
    result: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def _parse_kipris_xml(xml_text: str) -> Optional[dict]:
    """KIPRIS XML 응답에서 title·abstract·claims를 추출."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    ns_map = {
        "body": root.tag.split("}")[0].lstrip("{") if "}" in root.tag else "",
    }

    def find_text(tag: str) -> str:
        for elem in root.iter():
            local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local == tag and elem.text:
                return elem.text.strip()
        return ""

    def find_all_texts(tag: str) -> list[str]:
        results = []
        for elem in root.iter():
            local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local == tag and elem.text:
                results.append(elem.text.strip())
        return results

    title = find_text("inventionTitle") or find_text("inventionTitleEng") or ""
    abstract = find_text("astrtCont") or find_text("abstractContent") or ""
    claims_list = find_all_texts("claim") or find_all_texts("claimContent")
    claims_text = "\n".join(f"청구항 {i+1}. {c}" for i, c in enumerate(claims_list))

    if not title and not abstract:
        return None

    return {
        "title": title,
        "abstract": abstract,
        "claims": claims_text,
        "text": f"{title}\n\n[요약]\n{abstract}\n\n[청구항]\n{claims_text}",
        "raw_xml": xml_text[:2000],
    }


def fetch_kipris_detail(
    application_number: str,
    kipris_key: str,
) -> Optional[dict]:
    """단일 출원번호로 KIPRIS API 호출."""
    params = {
        "applicationNumber": application_number,
        "ServiceKey": kipris_key,
    }
    try:
        resp = httpx.get(_KIPRIS_API_URL, params=params, timeout=_TIMEOUT)
        if resp.status_code != 200:
            return None
        return _parse_kipris_xml(resp.text)
    except Exception:
        return None


def fetch_from_kipris(patent_id: str) -> Optional[dict]:
    """특허번호로 KIPRIS에서 서지정보 + 청구항을 가져온다.

    반환값: {"title": str, "abstract": str, "claims": str, "text": str} 또는 None
    API 키가 없거나 조회 실패 시 None 반환.
    """
    kipris_key = os.environ.get("KIPRIS_API_KEY", "")
    if not kipris_key:
        return None

    candidates = _build_application_candidates(patent_id)
    for candidate in candidates:
        result = fetch_kipris_detail(candidate, kipris_key)
        if result:
            result["application_number"] = candidate
            result["source"] = "kipris"
            return result

    return None


class KiprisConnector:
    """KIPRIS 커넥터 — code_linker.py에서 사용."""

    name = "kipris"

    def fetch(self, patent_id: str) -> Optional[dict]:
        """특허번호로 원문 조회. 실패 시 None."""
        return fetch_from_kipris(patent_id)

    def available(self) -> bool:
        """API 키 설정 여부."""
        return bool(os.environ.get("KIPRIS_API_KEY", ""))
