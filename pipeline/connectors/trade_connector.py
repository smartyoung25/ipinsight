"""무역 흐름 Connector — UN Comtrade v2 (무료 공개 엔드포인트, 키 불필요)
G3 시장스캔·G6 가치평가의 실수출입 데이터 근거.

HS 코드 → 국가별 수출입 금액·물량·상위 교역국
"""
from __future__ import annotations
import json, urllib.request, urllib.parse, hashlib, time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / ".rag_cache"
CACHE_DIR.mkdir(exist_ok=True)

_COMTRADE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

# 기술사업화 관련 주요 HS 코드
HS_CODES: dict[str, dict] = {
    "agritech": {
        "8432": "농업용 기계(파종·경작·수확)",
        "8424": "관개·분무 장치",
        "9026": "유량·액위 측정기기",
        "8543": "전기기기(IoT 센서 포함)",
    },
    "medical_device": {
        "9018": "의료용 기기·수술기구",
        "9027": "물리·화학 분석기기",
        "9019": "호흡기·치료기",
        "8517": "통신기기(원격의료 단말)",
    },
    "energy": {
        "8541": "반도체·태양광 셀",
        "8502": "발전기·발전 세트",
        "8507": "배터리·에너지저장",
        "8504": "변압기·전력 변환기",
    },
    "software_saas": {
        "8471": "자동 데이터 처리기계",
        "8517": "통신기기",
        "8543": "전기기기",
        "9031": "측정·검사기기",
    },
    "manufacturing": {
        "8479": "산업기계(범용)",
        "8537": "제어반·PLC",
        "9031": "측정·검사기기",
        "8413": "펌프·액체 처리기기",
    },
}

# ISO → UN Comtrade 국가 코드
REPORTER_CODES: dict[str, int] = {
    "KR": 410, "US": 842, "CN": 156, "JP": 392, "DE": 276,
    "IN": 356, "GB": 826, "FR": 251, "VN": 704, "TH": 764,
    "BR": 76,  "MX": 484, "AU": 36,  "CA": 124, "SG": 702,
}


def _cached_get(url: str, ttl_hours: int = 168) -> dict:
    key = hashlib.md5(url.encode()).hexdigest()
    f = CACHE_DIR / f"trade_{key}.json"
    if f.exists() and (time.time() - f.stat().st_mtime) / 3600 < ttl_hours:
        return json.loads(f.read_text(encoding="utf-8"))
    req = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": "IPInsight/1.0"
    })
    with urllib.request.urlopen(req, timeout=12) as r:
        data = json.loads(r.read())
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


class TradeConnector:
    """
    UN Comtrade v2 공개 엔드포인트 — 키 불필요, 실측 200 OK.
    제약: 공개 엔드포인트는 연간 집계만 제공(월별/분기별은 API키 필요).
    """

    def trade_flow(
        self,
        hs_code: str,
        reporter_iso: str = "KR",
        period: str = "2022",
        partner_iso: str = "0",   # 0 = 세계 전체
    ) -> dict:
        """HS 코드 × 국가 → 연간 수출입 금액"""
        reporter = REPORTER_CODES.get(reporter_iso.upper(), 410)
        partner  = REPORTER_CODES.get(partner_iso.upper(), 0) if partner_iso != "0" else 0
        url = (f"{_COMTRADE}?cmdCode={hs_code}&period={period}"
               f"&reporterCode={reporter}&partnerCode={partner}")
        try:
            data = _cached_get(url)
            rows = data.get("data", [])
            results = []
            # flowDesc는 공개 엔드포인트에서 null → flowCode 사용 (X=수출, M=수입, C=재수출 등)
            _FLOW_MAP = {"X": "Export", "M": "Import", "C": "Re-Export", "D": "Re-Import"}
            for row in rows:
                flow_code = row.get("flowCode", "")
                results.append({
                    "reporter":     row.get("reporterISO") or reporter_iso,
                    "partner":      row.get("partnerDesc") or row.get("partnerISO") or "World",
                    "flow":         _FLOW_MAP.get(flow_code, flow_code),
                    "flow_code":    flow_code,
                    "hs_code":      hs_code,
                    "value_usd":    row.get("primaryValue", 0) or row.get("fobvalue", 0),
                    "net_wgt_kg":   row.get("netWgt"),
                    "period":       period,
                })
            return {
                "source":      "UN Comtrade v2",
                "hs_code":     hs_code,
                "reporter":    reporter_iso,
                "period":      period,
                "total_value_usd": sum(r["value_usd"] or 0 for r in results),
                "rows":        results,
            }
        except Exception as e:
            return {"source": "UN Comtrade", "hs_code": hs_code, "error": str(e)[:80]}

    def sector_trade_summary(
        self,
        tech_type: str,
        reporters: list[str] | None = None,
        period: str = "2022",
    ) -> dict:
        """tech_type 전체 HS 코드 × 복수 국가 → 무역 요약"""
        reporters = reporters or ["KR", "US", "CN", "JP", "DE"]
        hs_map = HS_CODES.get(tech_type, HS_CODES["agritech"])
        summary: list[dict] = []
        errors: list[str] = []

        for hs_code, hs_desc in list(hs_map.items())[:2]:   # API 절약: 상위 2개 HS만
            for reporter in reporters[:3]:                    # 상위 3개국
                try:
                    result = self.trade_flow(hs_code, reporter, period)
                    if "error" not in result:
                        for row in result["rows"]:
                            # flowCode X = 수출, flow 텍스트도 체크
                            if row.get("flow_code") == "X" or row.get("flow") in ("Export", "수출"):
                                summary.append({
                                    "country":     reporter,
                                    "hs_code":     hs_code,
                                    "hs_desc":     hs_desc,
                                    "export_usd":  row["value_usd"] or 0,
                                    "period":      period,
                                })
                                break
                except Exception as e:
                    errors.append(f"{reporter}/{hs_code}: {e}")

        # 국가별 총 수출 집계
        by_country: dict[str, float] = {}
        for row in summary:
            by_country[row["country"]] = by_country.get(row["country"], 0) + (row["export_usd"] or 0)

        return {
            "source":       "UN Comtrade v2",
            "tech_type":    tech_type,
            "period":       period,
            "hs_codes_used": list(hs_map.keys())[:2],
            "by_country":  {k: round(v / 1e6, 1) for k, v in sorted(
                            by_country.items(), key=lambda x: -x[1])},  # 백만 USD
            "detail":       summary,
            "errors":       errors,
            "note":         "UN Comtrade 공개 엔드포인트 — 연간 집계, 키 불필요",
        }

    def market_size_from_trade(
        self,
        tech_type: str,
        target_countries: list[str],
        period: str = "2022",
    ) -> dict:
        """무역 데이터 기반 시장 규모 추정 (수출입 합산)"""
        summary = self.sector_trade_summary(tech_type, target_countries, period)
        by_country = summary.get("by_country", {})
        total_bn = round(sum(by_country.values()) / 1000, 2)  # 십억 달러
        return {
            "source":          "UN Comtrade v2 (무역 기반 시장 추정)",
            "tech_type":       tech_type,
            "period":          period,
            "total_trade_bn_usd": total_bn,
            "by_country_mn_usd":  by_country,
            "methodology":    "수출 데이터 합산 (TAM 하한 추정치 — 생산+내수 포함 시 실제 더 큼)",
        }
