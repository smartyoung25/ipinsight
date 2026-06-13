"""시장규모·경제지표 Connector — World Bank + OECD
G3 MarketScanner TAM/SAM 실데이터 자동화.
모두 무료·키 불필요.
"""
from __future__ import annotations
import json, urllib.request, urllib.parse, hashlib, time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / ".rag_cache"
CACHE_DIR.mkdir(exist_ok=True)

_WB  = "https://api.worldbank.org/v2"
_OECD = "https://stats.oecd.org/sdmx-json/data"

# World Bank 핵심 지표 — 기술사업화 TAM 산출용
_WB_INDICATORS = {
    "NY.GDP.MKTP.CD":   "GDP (현재 USD)",
    "SP.POP.TOTL":      "총 인구",
    "NE.EXP.GNFS.ZS":   "GDP 대비 수출 비율 %",
    "GB.XPD.RSDV.GD.ZS":"GDP 대비 R&D 지출 %",
    "IP.PAT.RESD":      "거주자 특허 출원 수",
    "IT.NET.USER.ZS":   "인터넷 사용자 비율 %",
    "EN.ATM.CO2E.PC":   "1인당 CO₂ 배출량 (t)",
    "SH.XPD.CHEX.GD.ZS":"GDP 대비 의료비 지출 %",
    "AG.LND.AGRI.ZS":   "농경지 비율 %",
}

# 주요 10개국 코드
_COUNTRIES = {
    "KR": "한국", "US": "미국", "CN": "중국", "JP": "일본",
    "DE": "독일", "GB": "영국", "FR": "프랑스", "IN": "인도",
    "SG": "싱가포르", "IL": "이스라엘",
}

# OECD MSTI R&D 지표
_OECD_DATASETS = {
    "MSTI_PUB": "과학기술지표 (R&D 지출·연구인력·특허)",
    "PATS_IPC":  "IPC 특허 통계",
}


def _get(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "IPInsight/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _cached_get(url: str, ttl_hours: int = 168) -> dict:  # 기본 7일 캐시
    key = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"market_{key}.json"
    if cache_file.exists():
        if (time.time() - cache_file.stat().st_mtime) / 3600 < ttl_hours:
            return json.loads(cache_file.read_text(encoding="utf-8"))
    data = _get(url)
    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


class MarketConnector:
    """
    ① World Bank Open Data — api.worldbank.org  (무료, 키 불필요, 지표 8000개)
    ② OECD.Stat SDMX       — stats.oecd.org     (무료, 키 불필요, 35개국)
    활용: G3 MarketScanner TAM 산출, G5 BM 시장 크기 근거
    """

    def gdp_indicators(self, country_codes: list[str], indicators: list[str] = None) -> dict:
        """국가별 GDP·인구·R&D 핵심 지표 조회 (최근 3년)"""
        inds = indicators or ["NY.GDP.MKTP.CD", "SP.POP.TOTL", "GB.XPD.RSDV.GD.ZS"]
        results = {}
        for country in country_codes[:10]:
            results[country] = {"name": _COUNTRIES.get(country, country), "indicators": {}}
            for ind in inds:
                try:
                    url = f"{_WB}/country/{country}/indicator/{ind}?format=json&mrv=3&per_page=3"
                    data = _cached_get(url)
                    records = data[1] if isinstance(data, list) and len(data) > 1 else []
                    values = [
                        {"year": r.get("date"), "value": r.get("value")}
                        for r in (records or []) if r.get("value") is not None
                    ]
                    results[country]["indicators"][ind] = {
                        "label":  _WB_INDICATORS.get(ind, ind),
                        "values": values,
                        "latest": values[0]["value"] if values else None,
                    }
                except Exception as e:
                    results[country]["indicators"][ind] = {"error": str(e)[:60]}
        return {"source": "World Bank Open Data", "countries": results}

    def tam_estimate(self, sector: str, target_countries: list[str]) -> dict:
        """섹터별 TAM 추정 — GDP + 섹터 지출 비율로 산출"""
        # 섹터별 GDP 지출 지표 매핑
        _SECTOR_INDICATOR = {
            "medical_device":  "SH.XPD.CHEX.GD.ZS",
            "agritech":        "AG.LND.AGRI.ZS",
            "software_saas":   "IT.NET.USER.ZS",
            "energy":          "EG.USE.PCAP.KG.OE",
            "default":         "NY.GDP.MKTP.CD",
        }
        ind = _SECTOR_INDICATOR.get(sector, _SECTOR_INDICATOR["default"])
        gdp_data = self.gdp_indicators(target_countries, ["NY.GDP.MKTP.CD", ind])

        tam_by_country = {}
        for cc, info in gdp_data.get("countries", {}).items():
            gdp    = info["indicators"].get("NY.GDP.MKTP.CD", {}).get("latest")
            factor = info["indicators"].get(ind, {}).get("latest")
            if gdp and factor:
                # TAM = GDP × 섹터비율 (%) / 100 × 시장침투 보정계수
                penetration = {"medical_device": 0.15, "agritech": 0.08,
                               "software_saas": 0.05, "energy": 0.10}.get(sector, 0.05)
                tam = gdp * (factor / 100) * penetration
                tam_by_country[cc] = {
                    "gdp_usd":         gdp,
                    "sector_factor":   factor,
                    "tam_usd":         round(tam),
                    "tam_bn":          round(tam / 1e9, 2),
                }
        total_tam = sum(v["tam_usd"] for v in tam_by_country.values())
        return {
            "source":        "World Bank (TAM 추정)",
            "sector":        sector,
            "methodology":   "GDP × 섹터지출비율 × 침투계수",
            "tam_by_country": tam_by_country,
            "total_tam_usd": total_tam,
            "total_tam_bn":  round(total_tam / 1e9, 2),
        }

    def oecd_rd_stats(self, country: str = "KOR", years: str = "2020:2022") -> dict:
        """OECD R&D 지출·연구인력 통계"""
        try:
            # MSTI: Total GERD (총 R&D 지출), Real PPP USD MIO
            url = f"{_OECD}/MSTI_PUB/{country}.TOT_GERD.REAL_PPP.USD_MIO/all?startTime={years.split(':')[0]}&endTime={years.split(':')[-1]}&format=jsondata"
            data = _cached_get(url)
            series = data.get("dataSets", [{}])[0].get("series", {})
            obs = next(iter(series.values()), {}).get("observations", {}) if series else {}
            time_periods = data.get("structure", {}).get("dimensions", {}).get("observation", [{}])[0].get("values", [])
            values = [
                {"year": time_periods[int(k)]["id"] if int(k) < len(time_periods) else k,
                 "gerd_usd_mio": round(v[0], 1)}
                for k, v in sorted(obs.items(), key=lambda x: int(x[0]))
            ]
            return {"source": "OECD MSTI", "country": country, "gerd_usd_mio": values}
        except Exception as e:
            return {"source": "OECD MSTI", "country": country, "error": str(e)[:80]}

    def market_summary(self, sector: str, target_countries: list[str]) -> dict:
        """World Bank + OECD 통합 시장 요약"""
        tam   = self.tam_estimate(sector, target_countries)
        oecd  = {cc: self.oecd_rd_stats(cc) for cc in target_countries[:3]}
        return {
            "sector":       sector,
            "tam":          tam,
            "rd_spending":  oecd,
            "data_quality": "World Bank 실측 + OECD 실측 (정적 추정 아님)",
        }
