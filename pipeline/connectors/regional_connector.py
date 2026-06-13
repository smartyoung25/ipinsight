"""4개 지역 통합 커넥터 — KR·US·EU·개발도상국(DEV)
한국·미국·유럽·개발도상국의 특허 환경·규제·시장·정책·ESG를 지역별로 자동 분기.
개도국 = 동남아(VN/ID/TH/PH/MY) + 남아시아(IN/BD/PK) + 중동/아프리카(EG/NG/KE/ZA) + 중남미(BR/MX/CO/CL)
"""
from __future__ import annotations
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────
# 지역 분류
# ─────────────────────────────────────────────────────────
REGION_KR  = {"KR"}
REGION_US  = {"US", "CA"}
REGION_EU  = {"DE", "FR", "GB", "NL", "SE", "FI", "DK", "NO", "CH", "AT", "BE", "IE", "IT", "ES", "PL", "EP"}
REGION_DEV = {
    # 동남아시아
    "VN", "ID", "TH", "PH", "MY", "MM", "KH", "LA",
    # 남아시아
    "IN", "BD", "PK", "LK", "NP",
    # 중동·북아프리카
    "EG", "MA", "TN", "JO", "AE", "SA",
    # 사하라이남 아프리카
    "NG", "KE", "ZA", "ET", "GH", "TZ", "RW",
    # 중남미
    "BR", "MX", "CO", "CL", "PE", "AR",
    # 동유럽·중앙아시아
    "UA", "KZ", "UZ",
}

def classify_region(country_code: str) -> str:
    c = country_code.upper()
    if c in REGION_KR:  return "KR"
    if c in REGION_US:  return "US"
    if c in REGION_EU:  return "EU"
    if c in REGION_DEV: return "DEV"
    return "OTHER"

def classify_regions(codes: list[str]) -> dict[str, list[str]]:
    """국가 코드 목록 → 지역별 분류"""
    out: dict[str, list[str]] = {"KR": [], "US": [], "EU": [], "DEV": [], "OTHER": []}
    for c in codes:
        out[classify_region(c)].append(c)
    return {k: v for k, v in out.items() if v}


# ─────────────────────────────────────────────────────────
# 지역별 정적 지식 DB
# ─────────────────────────────────────────────────────────

# ① 특허·IP 환경
IP_ENV: dict[str, dict] = {
    "KR": {
        "system":       "선출원주의 (AIA 동일)",
        "patent_office": "KIPO (한국특허청)",
        "strength":     "강함 — 연간 23만건, 반도체·디스플레이 강점",
        "avg_grant_months": 14,
        "utility_model": True,
        "ip_score_gii": 75,  # GII 2024
        "key_treaties": ["PCT", "Paris Convention", "Madrid Protocol"],
        "tlo_examples": ["KAIST IP", "SNU TLO", "ETRI TLO"],
        "fto_risk":     "중간 — NPE(특허괴물) 노출 낮음",
        "filing_cost_usd": 3000,
    },
    "US": {
        "system":       "선출원주의 (AIA 2013)",
        "patent_office": "USPTO",
        "strength":     "매우 강함 — 연간 65만건, 세계 최강 집행력(ITC·PTAB)",
        "avg_grant_months": 24,
        "utility_model": False,
        "ip_score_gii": 90,
        "key_treaties": ["PCT", "Paris Convention", "TRIPS"],
        "tlo_examples": ["Stanford OTL", "MIT TLO", "Caltech OTT"],
        "fto_risk":     "높음 — NPE·대형 소송 빈번",
        "filing_cost_usd": 12000,
    },
    "EU": {
        "system":       "선출원주의 (EPO + UPC 2023)",
        "patent_office": "EPO (유럽특허청) + UPC (단일법원)",
        "strength":     "강함 — UPC 이후 단일 집행 가능, GII IP 85점",
        "avg_grant_months": 36,
        "utility_model": True,  # 독일·프랑스 실용신안 허용
        "ip_score_gii": 85,
        "key_treaties": ["EPC", "PCT", "Madrid Protocol", "TRIPS"],
        "tlo_examples": ["Fraunhofer IPA", "KU Leuven Research", "TU Munich InovATUM"],
        "fto_risk":     "중간 — 국가별 집행 편차, GDPR 데이터 관련 리스크",
        "filing_cost_usd": 8000,
    },
    "DEV": {
        "system":       "국가별 상이 (대부분 선출원, 일부 허점)",
        "patent_office": "국가별 — DPKC(VN)·DGIP(ID)·DIP(TH)·IPO(PH) 등",
        "strength":     "약함~중간 — 집행력 제한, 모방 리스크 존재",
        "avg_grant_months": 36,
        "utility_model": True,  # 대부분 허용
        "ip_score_gii": 40,  # 평균
        "key_treaties": ["PCT (가입국 상이)", "Paris Convention"],
        "tlo_examples": ["IIT Delhi FITT (IN)", "USP TT (BR)", "ARIPO (아프리카 지역특허)"],
        "fto_risk":     "높음 — 집행력 약하나 역설적으로 소송 부담 낮음",
        "filing_cost_usd": 1500,
        "regional_offices": {
            "ARIPO": "아프리카 지역지식재산청 (19개국)",
            "OAPI":  "아프리카 지식재산청 (17개 프랑코폰)",
            "ASEAN": "ASEAN IP 협력 (공동 심사 확대 중)",
        },
    },
}

# ② 규제·인증 환경
REGULATORY_ENV: dict[str, dict] = {
    "KR": {
        "framework":   "스마트농업법(2023)·의료기기법·개인정보보호법·에너지법",
        "agencies":    ["MFDS(식약처)", "MAFRA(농림부)", "MOTIE(산업부)", "MSIT(과기부)"],
        "certifications": {
            "agritech":       "GAP인증·스마트팜 인증·친환경농산물인증",
            "medical_device": "MFDS 1~4등급 허가 (Class I~IV)",
            "software":       "ISMS-P·CC인증(국정원)·GS인증",
            "energy":         "REC(신재생에너지 인증)·에너지효율등급",
        },
        "avg_cert_months": {"medical_device": 12, "agritech": 6, "software": 3},
        "sandbox":     "ICT규제 샌드박스·규제자유특구 활용 가능",
        "cost_usd":    {"medical_device": 30000, "agritech": 5000, "software": 8000},
    },
    "US": {
        "framework":   "FDA·USDA·EPA·FCC·SEC 분산 규제",
        "agencies":    ["FDA", "USDA", "EPA", "FCC", "FTC", "SEC", "CISA"],
        "certifications": {
            "agritech":       "USDA Organic·GlobalGAP·Food Safety Modernization Act",
            "medical_device": "FDA 510(k)·PMA·De Novo (Class I/II/III)",
            "software":       "FedRAMP·SOC2·HIPAA·CCPA",
            "energy":         "Energy Star·UL 9540·IEEE 1547",
        },
        "avg_cert_months": {"medical_device": 18, "agritech": 8, "software": 6},
        "sandbox":     "FDA Breakthrough Device·FCC Innovation Zone",
        "cost_usd":    {"medical_device": 200000, "agritech": 20000, "software": 50000},
    },
    "EU": {
        "framework":   "CE Mark 통합 + 섹터별 지침(MDR·RED·NIS2·AI Act·GDPR)",
        "agencies":    ["EMA(의약품)", "EASA(항공)", "ENISA(사이버)", "EC DG GROW"],
        "certifications": {
            "agritech":       "GlobalG.A.P.·EU Organic·SPS 기준",
            "medical_device": "CE Mark MDR 2017/745 (Class I/IIa/IIb/III)",
            "software":       "CE Mark(RED)·GDPR DPA·AI Act Risk Class·ISO 27001",
            "energy":         "CE Mark(LVD·ErP)·EU ETS·RED II·RE100",
        },
        "avg_cert_months": {"medical_device": 24, "agritech": 10, "software": 8},
        "sandbox":     "EIC Transition·Digital Innovation Hubs(DIH)·Living Labs",
        "cost_usd":    {"medical_device": 80000, "agritech": 15000, "software": 30000},
        "ai_act_risk_classes": {
            "unacceptable": "소셜 스코어링·금지",
            "high":         "의료·교육·고용·인프라 AI → 적합성평가 의무",
            "limited":      "챗봇·딥페이크 → 투명성 의무",
            "minimal":      "스팸필터·게임 → 자율규제",
        },
    },
    "DEV": {
        "framework":   "국가별 상이 — 국제 표준(WHO·Codex·ISO) 준용 추세",
        "agencies":    {
            "IN":  ["CDSCO(의료기기)", "FSSAI(식품)", "BIS(표준)", "DOT(통신)"],
            "VN":  ["DAV(의약품)", "DARD(농업)", "MOST(과학기술부)"],
            "ID":  ["BPOM(식품의약품)", "Kementan(농업)", "Kominfo(정보통신)"],
            "BR":  ["ANVISA(의약식품)", "MAPA(농업)", "ANATEL(통신)"],
            "NG":  ["NAFDAC(식품의약품)", "FMARD(농업)", "NCC(통신)"],
            "ZA":  ["SAHPRA(의약품)", "DAFF(농업)", "ICASA(통신)"],
        },
        "certifications": {
            "agritech":       "GlobalG.A.P.(수출 요구)·국가별 GAP·Codex Alimentarius",
            "medical_device": "WHO 사전적격성평가(PQ)·국가별 허가·IMDRF 가이드라인",
            "software":       "국가별 데이터보호법 (인도 DPDP Act·브라질 LGPD)",
            "energy":         "IEC 62368 기준·국가별 그린에너지 인증",
        },
        "avg_cert_months": {"medical_device": 24, "agritech": 12, "software": 6},
        "market_entry_notes": {
            "localization":   "현지 파트너·유통망 필수 (직접진출 리스크 高)",
            "standards":      "국제 인증(CE·FDA) 보유 시 개도국 진입 가속",
            "leapfrog":       "피쳐폰→스마트폰·오프그리드→재생에너지 도약기술 유리",
            "informal_econ":  "비공식 경제 30~60% → B2B보다 B2G·원조연계 유리",
        },
    },
}

# ③ 자금조달·투자 생태계
FUNDING_ENV: dict[str, dict] = {
    "KR": {
        "vc_total_usd_bn":  8.2,  # 2024년 VC 투자
        "avg_series_a_usd": 5_000_000,
        "key_programs":     ["TIPS", "창업패키지", "기술보증기금(KIBO)", "산업기술진흥원(KIAT)"],
        "gov_rd_pct_gdp":   4.9,  # 세계 1위 수준
        "unicorns":         23,
        "exit_options":     ["KOSDAQ", "KOSPI", "나스닥 ADR", "M&A(대기업)"],
        "dev_aid_given":    "ODA 공여국 — KOICA 개도국 스마트팜 지원",
    },
    "US": {
        "vc_total_usd_bn":  170,
        "avg_series_a_usd": 15_000_000,
        "key_programs":     ["SBIR/STTR", "NSF I-Corps", "ARPA-E", "DOE LPO", "NIH SBIR"],
        "gov_rd_pct_gdp":   3.5,
        "unicorns":         700,
        "exit_options":     ["NYSE", "NASDAQ", "M&A", "SPAC"],
        "dfi_programs":     ["DFC(개도국금융공사)", "USAID DIV", "Power Africa"],
    },
    "EU": {
        "vc_total_usd_bn":  55,
        "avg_series_a_usd": 8_000_000,
        "key_programs":     ["EIC Accelerator(최대 €2.5M+지분)", "Horizon Europe(€95.5B)", "EIF VC", "InvestEU"],
        "gov_rd_pct_gdp":   2.2,
        "unicorns":         130,
        "exit_options":     ["Euronext", "Frankfurt SE", "LSE", "M&A"],
        "dev_aid_given":    "EFSD+(EU 개발금융)·EDFI(유럽개발금융기관) 연계",
        "impact_investing": "EU Taxonomy for Sustainable Finance — ESG 의무 공시",
    },
    "DEV": {
        "vc_total_usd_bn":  {"IN": 15, "BR": 4, "SEA": 8, "AFR": 1.5},
        "avg_series_a_usd": 2_000_000,
        "key_programs": {
            "multilateral": [
                {"name": "World Bank IFC", "focus": "민간부문 투자", "url": "https://www.ifc.org"},
                {"name": "ADB (아시아개발은행)", "focus": "아시아 인프라·혁신", "url": "https://www.adb.org"},
                {"name": "AfDB (아프리카개발은행)", "focus": "아프리카 농업·에너지", "url": "https://www.afdb.org"},
                {"name": "IADB (미주개발은행)", "focus": "중남미 스타트업", "url": "https://www.iadb.org"},
                {"name": "UNDP SDG Impact", "focus": "SDG 연계 임팩트 투자", "url": "https://sdgimpact.undp.org"},
                {"name": "GEF (지구환경기금)", "focus": "기후·생물다양성", "url": "https://www.thegef.org"},
                {"name": "Green Climate Fund (GCF)", "focus": "기후변화 완화·적응", "url": "https://www.greenclimate.fund"},
            ],
            "bilateral": [
                {"name": "KOICA ODA", "country": "KOR→DEV", "focus": "스마트팜·ICT 원조"},
                {"name": "USAID DIV", "country": "USA→DEV", "focus": "개발혁신벤처"},
                {"name": "GIZ (독일)", "country": "DEU→DEV", "focus": "농업·에너지·디지털"},
                {"name": "JICA (일본)", "country": "JPN→DEV", "focus": "인프라·스마트농업"},
                {"name": "AFD (프랑스)", "country": "FRA→DEV", "focus": "기후·도시화"},
            ],
            "impact_vc": [
                {"name": "Acumen Fund",        "focus": "농업·의료·에너지 빈곤층"},
                {"name": "Omidyar Network",    "focus": "금융포용·교육·거버넌스"},
                {"name": "Leapfrog Investments","focus": "금융보험·의료 신흥시장"},
                {"name": "AgFunder",            "focus": "개도국 애그리테크"},
                {"name": "Seedstars",           "focus": "신흥시장 초기 스타트업"},
            ],
        },
        "market_entry_model": {
            "B2G":     "정부 조달·원조 연계 — 가장 안정적",
            "B2B_MNC": "현지 진출 다국적기업 공급망 편입",
            "B2C_Mobile": "모바일 퍼스트 직접판매 (M-Pesa 등 연계)",
            "Franchise": "현지 파트너 프랜차이즈 모델",
        },
        "exit_options":     ["전략적 M&A(MNC)", "IPO (국내거래소)", "2차 매각(PE)"],
        "leapfrog_sectors": ["모바일금융(핀테크)", "오프그리드 태양광", "정밀농업", "원격의료", "에듀테크"],
    },
}

# ④ 시장 진입 전략 (GTM)
GTM_STRATEGY: dict[str, dict] = {
    "KR": {
        "recommended_channels": ["정부 R&D 과제 → 실증 → 대기업 공급망", "TIPS → 시리즈A → 코스닥"],
        "partnership_model":    "대기업 CVC(삼성·현대·LG·SK) + 스타트업 협력",
        "sales_cycle_months":   6,
        "pilot_approach":       "스마트팜 실증단지(경남·전북) + 농진청 시범사업",
        "language":             "한국어 필수",
        "cultural_notes":       "빠른 의사결정 + 관계중심 + 정부신뢰도 높음",
    },
    "US": {
        "recommended_channels": ["PLG(Product-Led Growth) → ENT", "파트너/채널 리셀러", "DoD/연방 조달"],
        "partnership_model":    "전략적 파트너십 + 직접영업(AE 중심)",
        "sales_cycle_months":   9,
        "pilot_approach":       "Innovation Challenge + Pilot-as-a-Service",
        "language":             "영어",
        "cultural_notes":       "ROI 중심·계약문화·빠른 결정",
    },
    "EU": {
        "recommended_channels": ["Horizon Europe 과제 → 검증 → 공공조달", "EIC Accelerator → 유럽 확장"],
        "partnership_model":    "유럽 TLO·Fraunhofer·KIC 네트워크 활용",
        "sales_cycle_months":   12,
        "pilot_approach":       "EU Living Lab + DIH 실증",
        "language":             "영어+현지어 병행",
        "cultural_notes":       "규제 준수·지속가능성·사회적 가치 강조",
        "gdpr_note":            "데이터 처리 시 GDPR DPA 사전 검토 필수",
    },
    "DEV": {
        "recommended_channels": ["원조·ODA 연계 파일럿", "현지 통신사/농협/NGO 파트너십", "모바일 앱 B2C"],
        "partnership_model":    "현지 임팩트 허브 + 국제 NGO + 정부 농업부",
        "sales_cycle_months":   18,
        "pilot_approach":       "CGIAR·FAO·WFP 시범사업 연계",
        "language":             "현지어 필수 (스와힐리·벵골어·인도네시아어 등)",
        "cultural_notes":       "신뢰구축 우선·현지인 고용·지역사회 참여",
        "affordability":        "가격 현지화 필수 (DAC·PPP 기준 30~70% 할인)",
        "infrastructure":       "저전력·오프라인 동작·2G/3G 호환 필수",
        "country_specifics": {
            "IN":  "Startup India·Make in India 정책 연계, Tier-2/3 도시 시장",
            "VN":  "농업 디지털화 정책(2025년 30% 디지털 목표), 수출가공구 연계",
            "ID":  "4천개 섬 물류 제약, B2B 농업협동조합 채널",
            "BR":  "Agro 4.0 정책, EMBRAPA 연구기관 파트너십",
            "NG":  "Lagos 테크허브 생태계, 농업개발은행(BOA) 연계",
            "KE":  "iHub·M-Pesa 핀테크 생태계, 동아프리카 관문",
            "ZA":  "제조기반·물류허브·SADC 시장 관문",
            "EG":  "중동·북아프리카(MENA) 관문, 수에즈경제특구",
        },
    },
}

# ⑤ ESG·SDG 우선순위 (지역별)
ESG_PRIORITY: dict[str, dict] = {
    "KR": {
        "top_sdgs":      ["SDG 9 산업혁신", "SDG 12 지속가능소비", "SDG 13 기후행동"],
        "carbon_target": "2030년 NDC 40% 감축, 2050 탄소중립",
        "esg_framework": "K-ESG 가이드라인(산업부)·한국거래소 ESG공시",
        "green_finance": "한국녹색채권원칙·녹색분류체계(K-Taxonomy)",
        "key_metric":    "온실가스 배출권(KAU) + TCFD 공시 의무(2025~)",
    },
    "US": {
        "top_sdgs":      ["SDG 9", "SDG 7 청정에너지", "SDG 13"],
        "carbon_target": "2030년 50~52% 감축(2005 대비), IRA 청정에너지 세제",
        "esg_framework": "SEC 기후공시 규칙(2024)·SASB·GRI",
        "green_finance": "IRA (인플레감축법) — $369B 청정에너지 보조금",
        "key_metric":    "Scope 1/2/3 배출 SEC 의무공시(2026~)",
    },
    "EU": {
        "top_sdgs":      ["SDG 13", "SDG 7", "SDG 12", "SDG 11"],
        "carbon_target": "2030년 55% 감축(Fit for 55), 2050 탄소중립",
        "esg_framework": "CSRD(기업지속가능성보고지침)·EU Taxonomy·SFDR",
        "green_finance": "EU Green Bond Standard·Taxonomy 6대 환경목표",
        "key_metric":    "CBAM(탄소국경조정제도) — 2026년 수출입 탄소세 부과",
        "cbam_sectors":  ["철강", "알루미늄", "시멘트", "비료", "전력", "수소"],
    },
    "DEV": {
        "top_sdgs":      ["SDG 1 빈곤종식", "SDG 2 기아종식", "SDG 3 건강", "SDG 6 물", "SDG 7 에너지"],
        "carbon_target": "NDC 제출국 대부분 (이행 역량 부족)",
        "esg_framework": "GRI·IIRC·UN SDG 자발적 보고",
        "green_finance":  "GCF(녹색기후기금)·GEF·ADB 기후금융·혼합금융(Blended Finance)",
        "key_metric":    "적응(Adaptation) > 완화(Mitigation) — 기후취약국 우선",
        "impact_priority": {
            "food_security":   "식량안보 — 스마트팜·정밀농업",
            "clean_water":     "깨끗한 물 — 수처리·관개효율화",
            "clean_energy":    "청정에너지 — 오프그리드 태양광·소수력",
            "digital_inclusion": "디지털 포용 — 모바일 헬스·핀테크",
            "climate_adapt":   "기후적응 — 가뭄·홍수 내성 작물·조기경보",
        },
        "blended_finance": {
            "definition": "공적자금으로 민간투자 레버리지 (1:4~1:10)",
            "instruments": ["보증(Guarantee)", "양허성 융자(Concessional Loan)",
                            "기술지원(TA Grant)", "위험분담(Risk Sharing)"],
            "key_players": ["GCF", "GEF", "ADB", "IFC", "MIGA"],
        },
    },
}


# ─────────────────────────────────────────────────────────
# RegionalConnector 클래스
# ─────────────────────────────────────────────────────────
@dataclass
class RegionalContext:
    tech_id:    str
    regions:    dict = field(default_factory=dict)   # 분석 대상 지역 분류
    ip:         dict = field(default_factory=dict)   # 지역별 IP 환경
    regulatory: dict = field(default_factory=dict)   # 지역별 규제·인증
    funding:    dict = field(default_factory=dict)   # 지역별 자금·투자
    gtm:        dict = field(default_factory=dict)   # 지역별 GTM 전략
    esg:        dict = field(default_factory=dict)   # 지역별 ESG 우선순위
    priority:   list = field(default_factory=list)   # 진입 우선순위 추천

    def to_dict(self) -> dict:
        return self.__dict__


class RegionalConnector:
    """
    4개 지역(KR·US·EU·DEV) 통합 컨텍스트 생성기.
    입력: 국가 코드 목록 + 기술 유형 → 지역별 IP·규제·자금·GTM·ESG 완전 분기
    """

    def analyze(self, target_countries: list[str], tech_type: str,
                efficiency_pct: float = 10.0) -> RegionalContext:
        """
        target_countries: ["KR", "US", "DE", "VN", "NG"] 등 ISO 2자리 코드
        tech_type: agritech / medical_device / software_saas / energy / manufacturing
        """
        ctx = RegionalContext(tech_id=f"{tech_type}_{'-'.join(target_countries[:3])}")

        # 지역 분류
        region_map = classify_regions(target_countries)
        ctx.regions = {
            "input_countries":  target_countries,
            "classified":       region_map,
            "active_regions":   list(region_map.keys()),
            "dev_countries":    region_map.get("DEV", []),
        }

        # 지역별 IP 환경
        ctx.ip = {r: IP_ENV.get(r, IP_ENV["DEV"]) for r in region_map}

        # 지역별 규제
        ctx.regulatory = {
            r: {
                "framework":      REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"])["framework"],
                "certifications": REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"])["certifications"].get(tech_type, "해당 없음"),
                "avg_months":     REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"])["avg_cert_months"].get(tech_type),
                "cost_usd":       REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"]).get("cost_usd", {}).get(tech_type),
                "sandbox":        REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"]).get("sandbox"),
            }
            for r in region_map
        }

        # 지역별 자금·투자
        ctx.funding = {r: FUNDING_ENV.get(r, FUNDING_ENV["DEV"]) for r in region_map}

        # 지역별 GTM
        ctx.gtm = {r: GTM_STRATEGY.get(r, GTM_STRATEGY["DEV"]) for r in region_map}

        # 지역별 ESG
        ctx.esg = {r: ESG_PRIORITY.get(r, ESG_PRIORITY["DEV"]) for r in region_map}

        # 진입 우선순위 추천
        ctx.priority = self._recommend_priority(region_map, tech_type)

        return ctx

    def dev_country_detail(self, country_code: str, tech_type: str) -> dict:
        """개도국 특정 국가 상세 분석"""
        cc = country_code.upper()
        specifics = GTM_STRATEGY["DEV"]["country_specifics"].get(cc, {})
        agencies   = REGULATORY_ENV["DEV"]["agencies"] if isinstance(REGULATORY_ENV["DEV"]["agencies"], dict) else {}
        return {
            "country":        cc,
            "region_type":    "DEV" if cc in REGION_DEV else classify_region(cc),
            "ip_env":         IP_ENV["DEV"],
            "regulatory":     {"agencies": agencies.get(cc, []), "framework": REGULATORY_ENV["DEV"]["framework"]},
            "market_notes":   specifics,
            "gtm":            GTM_STRATEGY["DEV"],
            "funding":        FUNDING_ENV["DEV"],
            "esg_priority":   ESG_PRIORITY["DEV"]["impact_priority"],
            "leapfrog":       FUNDING_ENV["DEV"]["leapfrog_sectors"],
        }

    def patent_filing_strategy(self, target_countries: list[str],
                                budget_usd: float = 50_000) -> dict:
        """예산 내 PCT 출원 순서 최적화 (비용·시장가치 기반)"""
        region_map  = classify_regions(target_countries)
        costs       = {r: IP_ENV.get(r, IP_ENV["DEV"])["filing_cost_usd"] for r in region_map}
        total_cost  = sum(costs.values())

        priority_order = []
        if "US" in region_map: priority_order.append(("US", costs.get("US", 12000), "세계 최대 시장·집행력"))
        if "KR" in region_map: priority_order.append(("KR", costs.get("KR", 3000),  "국내 우선·KIPO 빠름"))
        if "EU" in region_map: priority_order.append(("EU", costs.get("EU", 8000),  "UPC 단일법원 활용"))
        if "DEV" in region_map: priority_order.append(("DEV", costs.get("DEV", 1500), "ARIPO/PCT 저비용"))

        return {
            "recommended_order": priority_order,
            "total_cost_usd":    total_cost,
            "budget_usd":        budget_usd,
            "feasible":          total_cost <= budget_usd,
            "pct_first":         True,  # 항상 PCT 먼저 (30개월 유예)
            "pct_note":          "PCT 출원 → 30개월 내 국가단계 진입 결정 (예산 보존)",
        }

    def _recommend_priority(self, region_map: dict, tech_type: str) -> list[dict]:
        """지역 × 기술 유형 → 진입 우선순위"""
        scores = {
            "KR": {"agritech": 90, "software_saas": 85, "medical_device": 75, "energy": 70, "default": 80},
            "US": {"agritech": 75, "software_saas": 95, "medical_device": 90, "energy": 85, "default": 85},
            "EU": {"agritech": 70, "software_saas": 80, "medical_device": 85, "energy": 90, "default": 80},
            "DEV":{"agritech": 85, "software_saas": 65, "medical_device": 60, "energy": 80, "default": 70},
        }
        result = []
        for region in region_map:
            sc = scores.get(region, scores["DEV"])
            score = sc.get(tech_type, sc["default"])
            result.append({
                "region":       region,
                "countries":    region_map[region],
                "entry_score":  score,
                "rationale":    self._rationale(region, tech_type),
            })
        return sorted(result, key=lambda x: -x["entry_score"])

    def _rationale(self, region: str, tech_type: str) -> str:
        _MAP = {
            ("KR",  "agritech"):        "스마트팜 선진국·정부 실증지원·빠른 상용화",
            ("KR",  "software_saas"):   "B2B 대기업 공급망·공공조달·TIPS 자금",
            ("US",  "software_saas"):   "세계 최대 SaaS 시장·PLG 가능·VC 풍부",
            ("US",  "medical_device"):  "FDA 허가 = 글로벌 신뢰·최대 시장",
            ("EU",  "energy"):          "EU ETS·Fit for 55·탄소중립 정책 수혜",
            ("EU",  "medical_device"):  "UPC+MDR 통합·CE = 유럽 전체 접근",
            ("DEV", "agritech"):        "식량안보 수요·ODA 연계·임팩트 투자 유입",
            ("DEV", "energy"):          "오프그리드 수요·GCF 기후금융·리프로그",
        }
        return _MAP.get((region, tech_type), f"{region} 시장 — 기술 유형 {tech_type} 적합성 분석 필요")
