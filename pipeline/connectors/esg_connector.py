"""ESG·기후·탄소 Connector — Climate TRACE + Our World in Data
G10-ESG 임팩트 정량화 실데이터 자동화. 모두 무료·키 불필요.
"""
from __future__ import annotations
import json, urllib.request, urllib.parse, hashlib, time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent.parent / ".rag_cache"
CACHE_DIR.mkdir(exist_ok=True)

_CT_API  = "https://api.climatetrace.org/v6"
_OWID    = "https://ourworldindata.org"

# Climate TRACE 섹터 코드
_SECTORS = {
    "agriculture":        "농업 (비료·가축·토지이용)",
    "buildings":          "건물 (냉난방·조명)",
    "fossil-fuel-operations": "화석연료 생산·처리",
    "forestry-and-land-use":  "산림·토지이용",
    "manufacturing":      "제조 (철강·시멘트·화학)",
    "mineral-extraction": "광물 채굴",
    "power":              "전력 생산",
    "transportation":     "교통·물류",
    "waste":              "폐기물 처리",
}

# OWID 데이터셋 슬러그 → 설명
_OWID_DATASETS = {
    "co2-emissions-vs-gdp":          "CO₂ 배출 vs GDP",
    "share-of-electricity-low-carbon":"저탄소 전력 비율",
    "renewable-energy-consumption":   "재생에너지 소비",
    "energy-use-per-capita":          "1인당 에너지 사용량",
    "food-ghg-emissions":             "식품 온실가스 배출",
}


def _get(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "IPInsight/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _cached_get(url: str, ttl_hours: int = 168) -> dict:
    key = hashlib.md5(url.encode()).hexdigest()
    f = CACHE_DIR / f"esg_{key}.json"
    if f.exists() and (time.time() - f.stat().st_mtime) / 3600 < ttl_hours:
        return json.loads(f.read_text(encoding="utf-8"))
    data = _get(url)
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


class ESGConnector:
    """
    ① Climate TRACE — api.climatetrace.org/v6  (무료, 섹터별 실시설 배출 추적)
    ② Our World in Data — ourworldindata.org   (무료, 탄소·에너지·식량 시계열)
    활용: G10-ESG 탄소저감 정량화, 임팩트 투자자 IR 데이터
    """

    def sectors(self) -> dict:
        """Climate TRACE 섹터 목록 조회"""
        try:
            data = _cached_get(f"{_CT_API}/definitions/sectors", ttl_hours=720)
            return {"source": "Climate TRACE", "sectors": data}
        except Exception as e:
            return {"source": "Climate TRACE", "sectors": _SECTORS, "note": "정적 폴백", "error": str(e)[:60]}

    def emissions_by_sector(self, sector: str, countries: list[str] = None,
                            since: int = 2020) -> dict:
        """섹터별 국가 탄소 배출량 조회"""
        try:
            params: dict = {"sector": sector, "since": since, "to": 2023}
            if countries:
                params["countries"] = ",".join(countries[:5])
            url = f"{_CT_API}/country/emissions?{urllib.parse.urlencode(params)}"
            data = _cached_get(url)
            return {
                "source":  "Climate TRACE",
                "sector":  sector,
                "sector_name": _SECTORS.get(sector, sector),
                "unit":    "tCO₂e (이산화탄소 환산톤)",
                "data":    data,
            }
        except Exception as e:
            return {"source": "Climate TRACE", "sector": sector, "error": str(e)[:80]}

    def carbon_reduction_potential(self, tech_type: str, sector: str,
                                   efficiency_pct: float, target_countries: list[str]) -> dict:
        """기술 도입 시 탄소 저감량 추정"""
        emissions_data = self.emissions_by_sector(sector, target_countries)
        base_emissions = 0.0

        raw = emissions_data.get("data", {})
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    base_emissions += item.get("emissions_quantity", 0) or 0
        elif isinstance(raw, dict):
            base_emissions = raw.get("total_emissions", 0) or 0

        reduction = base_emissions * (efficiency_pct / 100)
        # 탄소 가격: EU ETS ~$60/tCO₂e, 한국 ETS ~$10, 글로벌 사회적 비용 $51
        carbon_prices = {"EU_ETS": 60, "KOR_ETS": 10, "social_cost": 51}
        monetary = {k: round(reduction * v) for k, v in carbon_prices.items()}

        return {
            "tech_type":              tech_type,
            "sector":                 sector,
            "base_emissions_tco2e":   round(base_emissions),
            "efficiency_pct":         efficiency_pct,
            "reduction_tco2e":        round(reduction),
            "monetary_value_usd":     monetary,
            "sdg_alignment":          self._sdg_from_sector(sector),
            "note":                   "Climate TRACE 실데이터 기반 추정",
        }

    def owid_energy_trend(self, country_code: str, dataset: str = "share-of-electricity-low-carbon") -> dict:
        """Our World in Data 에너지·탄소 시계열 (CSV → JSON 파싱)"""
        try:
            url = f"{_OWID}/grapher/{dataset}.csv"
            req = urllib.request.Request(url, headers={"User-Agent": "IPInsight/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode("utf-8")
            lines = raw.strip().split("\n")
            headers = lines[0].split(",")
            rows = []
            for line in lines[1:]:
                vals = line.split(",")
                if len(vals) >= 3 and country_code.upper() in vals[0].upper():
                    try:
                        rows.append({
                            "year":  int(vals[2]) if vals[2].strip().isdigit() else None,
                            "value": float(vals[3]) if len(vals) > 3 and vals[3].strip() else None,
                        })
                    except (ValueError, IndexError):
                        pass
            rows = [r for r in rows if r["year"] and r["value"] is not None]
            return {
                "source":      "Our World in Data",
                "dataset":     _OWID_DATASETS.get(dataset, dataset),
                "country":     country_code,
                "trend":       sorted(rows, key=lambda x: x["year"])[-5:],
                "description": _OWID_DATASETS.get(dataset, dataset),
            }
        except Exception as e:
            return {"source": "Our World in Data", "dataset": dataset,
                    "country": country_code, "error": str(e)[:80],
                    "portal": f"https://ourworldindata.org/grapher/{dataset}"}

    def esg_summary(self, tech_type: str, sector: str, efficiency_pct: float,
                    target_countries: list[str]) -> dict:
        """Climate TRACE + OWID 통합 ESG 요약"""
        reduction = self.carbon_reduction_potential(tech_type, sector, efficiency_pct, target_countries)
        energy = self.owid_energy_trend(target_countries[0] if target_countries else "KOR")
        return {
            "carbon_impact":  reduction,
            "energy_trend":   energy,
            "impact_rating":  self._impact_rating(reduction.get("reduction_tco2e", 0)),
            "data_quality":   "Climate TRACE 실측 + OWID 실측",
        }

    def _sdg_from_sector(self, sector: str) -> list[str]:
        _MAP = {
            "agriculture":   ["SDG 2 기아종식", "SDG 12 지속가능소비", "SDG 13 기후행동"],
            "power":         ["SDG 7 청정에너지", "SDG 13 기후행동"],
            "manufacturing": ["SDG 9 산업혁신", "SDG 12 지속가능소비"],
            "transportation":["SDG 11 지속가능도시", "SDG 13 기후행동"],
            "buildings":     ["SDG 11 지속가능도시", "SDG 7 청정에너지"],
            "waste":         ["SDG 12 지속가능소비", "SDG 6 깨끗한 물"],
        }
        return _MAP.get(sector, ["SDG 13 기후행동"])

    def _impact_rating(self, reduction_tco2e: float) -> str:
        if reduction_tco2e > 1_000_000:
            return "A+ (메가톤급 임팩트 — 임팩트 펀드 적합)"
        if reduction_tco2e > 100_000:
            return "A (대규모 임팩트 — ESG 공시 가능)"
        if reduction_tco2e > 10_000:
            return "B (중규모 임팩트 — 탄소크레딧 거래 가능)"
        if reduction_tco2e > 1_000:
            return "C (소규모 임팩트 — 내부 탄소 회계)"
        return "D (측정 불가 수준 — 기술 효율 재검토)"
