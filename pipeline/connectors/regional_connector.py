"""8개 지역 통합 커넥터 — KR·US·EU·JP·CN·IN·RU·DEV
한국·미국·유럽·일본·중국·인도·러시아·개발도상국의
특허 환경·규제·시장·자금·GTM·ESG를 지역별로 완전 분기.
JP/CN/IN/RU는 REGION_DEV에서 독립한 전략 지역으로 격상.
"""
from __future__ import annotations
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────
# 지역 분류 (8개 지역)
# ─────────────────────────────────────────────────────────
REGION_KR  = {"KR"}
REGION_US  = {"US", "CA"}
REGION_EU  = {
    "DE", "FR", "GB", "NL", "SE", "FI", "DK", "NO", "CH",
    "AT", "BE", "IE", "IT", "ES", "PL", "PT", "CZ", "HU", "EP",
}
REGION_JP  = {"JP"}
REGION_CN  = {"CN", "HK", "MO", "TW"}   # HK/MO는 CNS 하위, TW는 별도이나 CH 리스크 포함
REGION_IN  = {"IN"}
REGION_RU  = {"RU", "BY", "AM", "GE"}   # 러시아 + 경제권
REGION_DEV = {
    # 동남아시아
    "VN", "ID", "TH", "PH", "MY", "MM", "KH", "LA",
    # 남아시아 (인도 제외)
    "BD", "PK", "LK", "NP",
    # 중동·북아프리카
    "EG", "MA", "TN", "JO", "AE", "SA",
    # 사하라이남 아프리카
    "NG", "KE", "ZA", "ET", "GH", "TZ", "RW",
    # 중남미
    "BR", "MX", "CO", "CL", "PE", "AR",
    # 중앙아시아
    "KZ", "UZ", "UA",
}

_REGION_MAP = {
    "KR": REGION_KR, "US": REGION_US, "EU": REGION_EU,
    "JP": REGION_JP, "CN": REGION_CN, "IN": REGION_IN,
    "RU": REGION_RU, "DEV": REGION_DEV,
}

def classify_region(country_code: str) -> str:
    c = country_code.upper()
    for label, s in _REGION_MAP.items():
        if c in s:
            return label
    return "OTHER"

def classify_regions(codes: list[str]) -> dict[str, list[str]]:
    """국가 코드 목록 → 지역별 분류"""
    out: dict[str, list[str]] = {
        "KR": [], "US": [], "EU": [], "JP": [],
        "CN": [], "IN": [], "RU": [], "DEV": [], "OTHER": [],
    }
    for c in codes:
        out[classify_region(c)].append(c)
    return {k: v for k, v in out.items() if v}


# ─────────────────────────────────────────────────────────
# ① 특허·IP 환경
# ─────────────────────────────────────────────────────────
IP_ENV: dict[str, dict] = {
    "KR": {
        "system":        "선출원주의",
        "patent_office": "KIPO (한국특허청)",
        "strength":      "강함 — 연간 23만건, 반도체·디스플레이 강점",
        "avg_grant_months": 14,
        "utility_model": True,
        "ip_score_gii":  75,
        "key_treaties":  ["PCT", "Paris Convention", "Madrid Protocol"],
        "tlo_examples":  ["KAIST IP", "SNU TLO", "ETRI TLO"],
        "fto_risk":      "중간",
        "filing_cost_usd": 3000,
    },
    "US": {
        "system":        "선출원주의 (AIA 2013)",
        "patent_office": "USPTO",
        "strength":      "매우 강함 — 연간 65만건, ITC·PTAB",
        "avg_grant_months": 24,
        "utility_model": False,
        "ip_score_gii":  90,
        "key_treaties":  ["PCT", "Paris Convention", "TRIPS"],
        "tlo_examples":  ["Stanford OTL", "MIT TLO"],
        "fto_risk":      "높음 — NPE·대형 소송",
        "filing_cost_usd": 12000,
    },
    "EU": {
        "system":        "선출원주의 (EPO + UPC 2023)",
        "patent_office": "EPO + UPC",
        "strength":      "강함 — UPC 단일법원 집행",
        "avg_grant_months": 36,
        "utility_model": True,
        "ip_score_gii":  85,
        "key_treaties":  ["EPC", "PCT", "Madrid Protocol"],
        "tlo_examples":  ["Fraunhofer IPA", "KU Leuven"],
        "fto_risk":      "중간",
        "filing_cost_usd": 8000,
    },
    "JP": {
        "system":        "선출원주의 (특허법 기반, 1985년 개정)",
        "patent_office": "JPO (특허청 — Japan Patent Office)",
        "strength":      "매우 강함 — 연간 29만건, 전통 제조+로봇+소재 강점",
        "avg_grant_months": 14,
        "utility_model": True,   # 실용신안 (Utility Model) 제도 유지
        "ip_score_gii":  80,
        "key_treaties":  ["PCT", "Paris Convention", "Madrid Protocol", "Hague System"],
        "tlo_examples":  ["University of Tokyo TLO", "Osaka University TLO", "NTT IP"],
        "fto_risk":      "중간 — 특허괴물(NPE) 적고, 기업 간 크로스라이선스 관행 강함",
        "filing_cost_usd": 5000,
        "special_notes": [
            "선발명(발명자 우선) 관행 문화 잔존 → 선행발명 증거 관리 중요",
            "실체심사청구(RCE) 없음 — JPO 자동 심사",
            "일본어 번역본 우선 (영문 출원 가능하나 번역 필수)",
            "대기업(도요타·소니·파나소닉) 크로스라이선스 네트워크 진입 어려움",
        ],
    },
    "CN": {
        "system":        "선출원주의 (특허법 2021년 제4차 개정 — 처벌 강화)",
        "patent_office": "CNIPA (국가지식재산권국 — 국가知識産権局)",
        "strength":      "양적 세계 1위(연간 160만건) — 질적 가치는 최상급 아님, 급속 개선 중",
        "avg_grant_months": 22,
        "utility_model": True,   # 실용신안(实用新型) — 무심사 빠른 등록
        "ip_score_gii":  55,
        "key_treaties":  ["PCT", "Paris Convention", "TRIPS", "Madrid Protocol"],
        "tlo_examples":  ["Tsinghua University TLO", "Peking University", "CETC TLO"],
        "fto_risk":      "높음 — 현지 실용신안 방어특허 매우 많음. 중국법원 보호주의 경향",
        "filing_cost_usd": 2500,
        "special_notes": [
            "중국 내 발명 → 국내 출원 후 6개월 경과해야 해외 PCT 가능 (보안심사법)",
            "실용신안(실신) + 발명특허 이중 전략 — 실신(18개월 등록)으로 선점 후 발명 심사",
            "외국기업 IP 보호 최근 강화(배상 10배 징벌적 손해배상 도입)",
            "기술이전 시 '기술수출입관리조례' → 특정 기술 정부 사전승인 필요",
            "데이터 관련 IP: 데이터 현지화법(PIPL·DSL·CSL) — 알고리즘·AI 모델 역외 이전 제한",
        ],
        "caution":       "기술 강제이전·디자인 모방·합작법인(JV) 내 유출 리스크",
    },
    "IN": {
        "system":        "선출원주의 (1970년 특허법 + 2005년 TRIPS 개정)",
        "patent_office": "CGPDTM (Controller General of Patents, Designs & Trade Marks)",
        "strength":      "중간 — 연간 7만건, 제약·ICT 분야 급성장",
        "avg_grant_months": 48,
        "utility_model": False,   # 실용신안 제도 없음
        "ip_score_gii":  42,
        "key_treaties":  ["PCT", "Paris Convention", "TRIPS"],
        "tlo_examples":  ["IIT Delhi FITT", "IISc STIC", "CSIR 산하 연구소"],
        "fto_risk":      "중간 — 강제실시권(Compulsory License) 실적 있음 (의약품)",
        "filing_cost_usd": 2000,
        "special_notes": [
            "Section 3(d): 공지 물질의 신규 형태·새로운 용도는 특허 불가 (제약 에버그리닝 방지)",
            "강제실시권: 특허 등록 3년 후 합리적 조건으로 정부 강제 허여 가능",
            "48개월 심사대기 → 인도-미국 PPH(특허심사 하이웨이) 활용 권장",
            "특허 출원 언어: 영어 또는 힌디어",
            "DPIIT '스타트업 인도' 등록 시 특허 수수료 80% 감면",
        ],
    },
    "RU": {
        "system":        "선출원주의 (러시아 민법 4편 + 특허법 기반)",
        "patent_office": "Rospatent (연방지식재산청 — Роспатент)",
        "strength":      "중간 — 연간 3.5만건, 방산·우주·원자력 원천기술 강점",
        "avg_grant_months": 18,
        "utility_model": True,   # 실용신안 (полезная модель)
        "ip_score_gii":  40,
        "key_treaties":  ["PCT", "Paris Convention", "Madrid Protocol", "Eurasian Patent (EAPO)"],
        "tlo_examples":  ["Skoltech TLO", "Moscow State University TLO", "Rusnano Portfolio"],
        "fto_risk":      "높음 (제재 이후) — 평행수입 합법화, 특허 강제 허여 가능",
        "filing_cost_usd": 1500,
        "special_notes": [
            "2022 제재 이후 '비우호국' 특허권자 동의 없이 발명 사용 가능 (정부령 № 299)",
            "EAPO(유라시아 특허청) — 1건 출원으로 9개 CIS 국가 동시 보호",
            "소프트웨어 특허: 원칙적 불허 (알고리즘 자체), 기술적 효과 입증 시 허용",
            "2023년 이후 서방 국가 특허 집행 사실상 불가 — 현지 파트너 의존도 높음",
            "IP 전략: 러시아 내 사업 시 러시아 법인으로 IP 등록 권장 (외국법인 집행 취약)",
        ],
        "sanction_risk": "매우 높음 — 서방 제재로 기술 거래·특허 라이선스 제한",
        "eurasian_patent": {
            "org":      "EAPO (Eurasian Patent Organization)",
            "members":  ["RU", "BY", "AM", "KZ", "KG", "TJ", "TM", "AZ"],
            "advantage": "1건 출원으로 8개 유라시아 회원국 동시 보호",
            "url":      "https://www.eapo.org",
        },
    },
    "DEV": {
        "system":        "국가별 상이 (대부분 선출원)",
        "patent_office": "국가별 (ARIPO·OAPI 지역청 활용 가능)",
        "strength":      "약함~중간",
        "avg_grant_months": 36,
        "utility_model": True,
        "ip_score_gii":  40,
        "key_treaties":  ["PCT (가입국 상이)", "Paris Convention"],
        "fto_risk":      "높음 — 집행력 제한",
        "filing_cost_usd": 1500,
    },
}

# ─────────────────────────────────────────────────────────
# ② 규제·인증 환경
# ─────────────────────────────────────────────────────────
REGULATORY_ENV: dict[str, dict] = {
    "KR": {
        "framework":   "스마트농업법·의료기기법·개인정보보호법·에너지법",
        "agencies":    ["MFDS(식약처)", "MAFRA(농림부)", "MOTIE(산업부)", "MSIT(과기부)"],
        "certifications": {
            "agritech":       "GAP인증·스마트팜인증·친환경농산물",
            "medical_device": "MFDS 1~4등급",
            "software":       "ISMS-P·CC인증·GS인증",
            "energy":         "REC·에너지효율등급",
        },
        "avg_cert_months": {"medical_device": 12, "agritech": 6, "software": 3},
        "sandbox":     "ICT규제 샌드박스·규제자유특구",
        "cost_usd":    {"medical_device": 30000, "agritech": 5000, "software": 8000},
    },
    "US": {
        "framework":   "FDA·USDA·EPA·FCC 분산 규제",
        "agencies":    ["FDA", "USDA", "EPA", "FCC", "FTC"],
        "certifications": {
            "agritech":       "USDA Organic·GlobalGAP·FSMA",
            "medical_device": "FDA 510(k)·PMA·De Novo",
            "software":       "FedRAMP·SOC2·HIPAA",
            "energy":         "Energy Star·UL 9540",
        },
        "avg_cert_months": {"medical_device": 18, "agritech": 8, "software": 6},
        "sandbox":     "FDA Breakthrough Device·FCC Innovation Zone",
        "cost_usd":    {"medical_device": 200000, "agritech": 20000, "software": 50000},
    },
    "EU": {
        "framework":   "CE Mark + MDR·AI Act·GDPR·NIS2",
        "agencies":    ["EMA", "EASA", "ENISA"],
        "certifications": {
            "agritech":       "GlobalG.A.P.·EU Organic·SPS",
            "medical_device": "CE Mark MDR 2017/745",
            "software":       "CE Mark·GDPR·AI Act",
            "energy":         "CE Mark·EU ETS·RED II",
        },
        "avg_cert_months": {"medical_device": 24, "agritech": 10, "software": 8},
        "sandbox":     "EIC Transition·Digital Innovation Hubs",
        "cost_usd":    {"medical_device": 80000, "agritech": 15000, "software": 30000},
    },
    "JP": {
        "framework":   "PMD Act(의약품의료기기법)·Food Sanitation Act·電気用品安全法(전기제품)·개인정보보호법(APPI)",
        "agencies":    ["PMDA(의약품의료기기종합기구)", "MHLW(후생노동성)", "MAFF(농림수산성)",
                        "MIC(총무성)", "METI(경제산업성)", "Nippon Jiho(전기용품)"],
        "certifications": {
            "agritech":       "JAS인증·농약등록·유기JAS·GAP(JGAP·GlobalGAP)",
            "medical_device": "PMD Act 클래스I~IV·PMDA 사전심사·특정보험의료재료",
            "software":       "Pmark(개인정보)·ISMS(ISO27001)·클라우드안전마크",
            "energy":         "PSE마크(电기용품)·省エネ법·J-Credit(탄소크레딧)",
            "manufacturing":  "JIS(일본산업규격)·ISO·CE Mark(수출용)",
        },
        "avg_cert_months": {"medical_device": 18, "agritech": 12, "software": 6, "manufacturing": 9},
        "sandbox":     "규제 샌드박스(産業競争力強化法)·대형실증특구·スーパーシティ(슈퍼시티)",
        "cost_usd":    {"medical_device": 100000, "agritech": 20000, "software": 25000},
        "special_notes": [
            "PMDA 사전상담 제도 — 의료기기 허가 전 무료 사전상담 적극 활용",
            "일본어 서류 필수 (영문 병행 가능하나 일본어 주문서 기준)",
            "대기업 유통망(도매상·商社) 없이 직접 병원·농협 판매 어려움",
            "농약 등록: 농약취체법 기반 — 외국 기업은 일본 법인 또는 지정 수입자 필요",
        ],
    },
    "CN": {
        "framework":   "SAMR(국가시장감독관리총국)·NMPA(의약품)·데이터 3법(PIPL·DSL·CSL)·AI관리규정",
        "agencies":    ["NMPA(국가약품감독관리국)", "MOA(농업농촌부)", "MIIT(공업정보화부)",
                        "CAC(국가인터넷정보판공실)", "SAMR(국가시장감독관리총국)"],
        "certifications": {
            "agritech":       "NY인증(농업행업표준)·绿色食品(녹색식품)·有机产品(유기제품)·农药登记(농약등록)",
            "medical_device": "NMPA 클래스I~III·CCC인증·동등성(실질동등) 경로",
            "software":       "MLPS(网络安全等级保护 — 等保 2.0)·ICP经营许可证·数据安全法",
            "energy":         "CCC마크(强制性认证)·能效标识(에너지효율)·碳市场(중국 탄소시장 ETS)",
            "manufacturing":  "CCC·GB국가표준·ISO",
        },
        "avg_cert_months": {"medical_device": 24, "agritech": 18, "software": 12, "manufacturing": 9},
        "sandbox":     "자유무역시험구(FTZ) 네거티브리스트·하이난자유항·보세구 샌드박스",
        "cost_usd":    {"medical_device": 120000, "agritech": 30000, "software": 40000},
        "special_notes": [
            "데이터 현지화: 중요 데이터·개인정보 원칙 중국 내 저장 (DSL·PIPL)",
            "알고리즘 추천 규정(2022): AI 추천 서비스 CAC 사전 신고 필수",
            "생성형 AI 관리규정(2023): 서비스 출시 전 CAC 보안 평가 필요",
            "합작법인(JV): 많은 업종 외자 지분 50% 이하 제한 — 네거티브리스트 확인 필수",
            "NMPA 동등성 경로: FDA/CE 허가 의료기기는 동등성 신청으로 심사 단축 가능",
        ],
        "caution":     "기술 강제이전·데이터 현지화·사이버보안법 컴플라이언스 필수",
    },
    "IN": {
        "framework":   "의약품법·식품안전법(FSSAI)·환경보호법·정보기술법(IT Act 2000)·DPDP Act(2023)",
        "agencies":    ["CDSCO(의료기기)", "FSSAI(식품)", "BIS(표준)", "SEBI(증권)", "TRAI(통신)"],
        "certifications": {
            "agritech":       "FSSAI인증·India Organic·GlobalGAP·CIL(살충제등록)",
            "medical_device": "CDSCO 클래스A~D·MDR 2017·Indian BIS(국내 의료기기)",
            "software":       "BIS표준·DPDP Act 준수·CERT-In 보안감사·ISO 27001",
            "energy":         "BEE(에너지효율국) 인증·MNRE 태양광·REC(재생에너지)",
            "manufacturing":  "BIS·ISI마크·ISO·GMP",
        },
        "avg_cert_months": {"medical_device": 24, "agritech": 12, "software": 6, "manufacturing": 9},
        "sandbox":     "스타트업 인도 규제 샌드박스·IFSCA(국제금융서비스)·농업 혁신 특구",
        "cost_usd":    {"medical_device": 30000, "agritech": 8000, "software": 10000},
        "special_notes": [
            "PLI(Production-Linked Incentive) 제도: 제조·의약·반도체·전자 분야 생산 인센티브",
            "Make in India: 외국 제품 정부 조달 제한 — 현지 생산(현지화율 50%+) 우대",
            "GEM(Government e-Marketplace): 정부 조달 플랫폼 — 현지법인 필수",
            "DPDP Act(2023): EU GDPR과 유사, 데이터 수탁자·수탁자 개념 도입",
            "Price control: DPCO(의약품 가격통제령) — 필수의약품 가격 상한제",
        ],
    },
    "RU": {
        "framework":   "연방법·기술규정(GOST R)·개인정보보호법(242-FZ)·주권 인터넷법(90-FZ)·제재 대응 특별조치",
        "agencies":    ["Roszdravnadzor(의약품의료기기)", "Rosselkhoznadzor(농업)", "Roskomnadzor(통신·데이터)",
                        "Rosstandart(국가표준)", "FSB(사이버보안 — 암호화)"],
        "certifications": {
            "agritech":       "GOST R(국가표준)·위생역학결론·Rospotrebnadzor 위생 인증·농약 국가등록",
            "medical_device": "Roszdravnadzor 등록·GOST R ISO 13485·EAEU MR(유라시아 의료기기)",
            "software":       "FSTEC(정보보안 인증)·FSB(암호화 — ViPNet·GOST암호 필수)·러시아 소프트웨어 등록부",
            "energy":         "GOST R·Rostekhnadzor(원자력·에너지 감독)·탄소발자국 GOST R(신규)",
            "manufacturing":  "GOST R·EAC마크(유라시아 경제연합)·TR EAEU",
        },
        "avg_cert_months": {"medical_device": 18, "agritech": 12, "software": 9, "manufacturing": 12},
        "sandbox":     "Skolkovo 혁신 클러스터·특별경제구역(SEZ)·첨단기술센터(НТЦ)",
        "cost_usd":    {"medical_device": 20000, "agritech": 10000, "software": 15000},
        "special_notes": [
            "EAC 마크: 유라시아경제연합(EAEU) 단일 인증 — RU+BY+KZ+AM+KG 동시 유효",
            "암호화 제품: FSB 허가 필수 (GOST 암호 알고리즘 요구 — OpenSSL 대체 불가)",
            "소프트웨어 현지화: 정부 기관 대상 러시아산 소프트웨어 우선 구매 의무 (Реестр)",
            "개인정보: 러시아 국민 데이터 → 러시아 서버 저장 의무 (242-FZ, Roskomnadzor 집행)",
            "2022년 이후: 서방 인증(CE·FDA) 보유 의료기기도 Roszdravnadzor 별도 등록 필요",
            "제재 우회 수출: 미국·EU·영국 법인은 러시아 거래 시 OFAC·EU제재·UK OFSI 확인 필수",
        ],
        "sanction_risk": "매우 높음 — 2022년 이후 광범위한 제재로 신규 진출 사실상 불가 (서방 기업)",
        "eaeu_regulatory": {
            "name":    "EAEU (유라시아 경제연합) 통합 규제",
            "members": ["RU", "BY", "KZ", "AM", "KG"],
            "key_rules": "TR EAEU 기술규정 40개+ — EAC 마크로 5개국 동시 판매 가능",
        },
    },
    "DEV": {
        "framework":   "국가별 상이 — WHO·Codex·ISO 국제 표준 준용 추세",
        "agencies":    {"VN": ["DAV", "DARD"], "BR": ["ANVISA", "MAPA"], "NG": ["NAFDAC"]},
        "certifications": {
            "agritech":       "GlobalG.A.P.·국가별 GAP·Codex",
            "medical_device": "WHO PQ·국가별 허가",
            "software":       "국가별 데이터보호법",
            "energy":         "IEC 62368·국가별 그린 인증",
        },
        "avg_cert_months": {"medical_device": 24, "agritech": 12, "software": 6},
        "market_entry_notes": "현지 파트너·유통망 필수",
    },
}

# ─────────────────────────────────────────────────────────
# ③ 자금조달·투자 생태계
# ─────────────────────────────────────────────────────────
FUNDING_ENV: dict[str, dict] = {
    "KR": {
        "vc_total_usd_bn":  8.2,
        "avg_series_a_usd": 5_000_000,
        "key_programs":     ["TIPS", "창업패키지", "기보(KIBO)", "KIAT", "KOICA ODA"],
        "gov_rd_pct_gdp":   4.9,
        "unicorns":         23,
        "exit_options":     ["KOSDAQ", "KOSPI", "나스닥 ADR", "M&A(대기업)"],
    },
    "US": {
        "vc_total_usd_bn":  170,
        "avg_series_a_usd": 15_000_000,
        "key_programs":     ["SBIR/STTR", "NSF I-Corps", "ARPA-E", "DOE LPO"],
        "gov_rd_pct_gdp":   3.5,
        "unicorns":         700,
        "exit_options":     ["NYSE", "NASDAQ", "M&A", "SPAC"],
        "dfi_programs":     ["DFC", "USAID DIV"],
    },
    "EU": {
        "vc_total_usd_bn":  55,
        "avg_series_a_usd": 8_000_000,
        "key_programs":     ["EIC Accelerator (€2.5M+지분)", "Horizon Europe (€95.5B)", "EIF VC"],
        "gov_rd_pct_gdp":   2.2,
        "unicorns":         130,
        "exit_options":     ["Euronext", "Frankfurt SE", "LSE", "M&A"],
    },
    "JP": {
        "vc_total_usd_bn":  9.5,
        "avg_series_a_usd": 3_000_000,
        "key_programs":     [
            "JST (과학기술진흥기구) — ACT-X·CREST·PRESTO",
            "NEDO (에너지산업기술종합개발기구) — 그린이노베ーション基金(2조엔)",
            "IPA (정보처리추진기구) — 未踏 (미토) 슈퍼크리에이터",
            "経済安保法(경제안보법 2022) — 특정중요기술 국가지원",
            "VC: SoftBank Vision·JAFCO·Global Brain·Incubate Fund",
        ],
        "gov_rd_pct_gdp":   3.3,
        "unicorns":         10,
        "exit_options":     ["TSE(도쿄증권거래소) Prime·Growth·TOKYO PRO Market", "M&A(대기업)"],
        "corporate_vc":     ["소니벤처즈", "도요타벤처즈", "NTT그룹", "덴소·아이신"],
        "special_notes": [
            "SBIR(일본판): 중소기업기술개발補助金 + JST·NEDO 중소기업지원",
            "외국 스타트업: J-Startup Global(경산성) — 일본 진출 해외 딥테크 지원",
            "VC 에코시스템: 미국 대비 초기단계(Seed·Series A) 부족 — 후기 단계 자금은 충분",
            "기업내 신사업(사내스타트업) 분사 모델 활발 — 대기업과 Co-Creation 전략 유효",
        ],
    },
    "CN": {
        "vc_total_usd_bn":  40,
        "avg_series_a_usd": 10_000_000,
        "key_programs":     [
            "火炬計劃(Torch Program) — 153개 첨단기술개발구(HIDZ)",
            "科创板(STAR Market/科創板) — 상하이 나스닥형 기술주 시장",
            "国家자연科学基金(NSFC) — 기초연구 연간 $50B+",
            "专项资金(전문 보조금) — AI·반도체·바이오 국가 전략산업",
            "지방정府 보조금: 각 성·시 별도 인센티브 (세금감면·토지·인재보조)",
        ],
        "gov_rd_pct_gdp":   2.5,
        "unicorns":         340,
        "exit_options":     ["A股(상하이·선전)", "科创板(STAR)", "港股(홍콩)", "나스닥·NYSE (VIE 구조)"],
        "state_funds":      ["国家集成電路産業基金(빅펀드 2기)", "国家新興産業創投引導基金"],
        "special_notes": [
            "VIE 구조: 중국 내 사업권을 해외 지주사에 계약으로 귀속 — IPO·외국인투자 우회 수단",
            "외국 VC: 2021년 이후 중국 빅테크 투자 규제 강화로 위축",
            "국가 주도: 반도체(芯片)·AI·양자·생명과학 정부 지원 최우선",
            "쌍순환 정책: 내수(内循環) + 수출(外循環) 동시 전략 — 내수 시장 먼저 공략 유리",
        ],
    },
    "IN": {
        "vc_total_usd_bn":  15,
        "avg_series_a_usd": 3_000_000,
        "key_programs":     [
            "Startup India Seed Fund (DPIIT)",
            "BIRAC (바이오기술산업연구지원위원회)",
            "SIDBI Fund of Funds (중소기업개발은행)",
            "Atal Innovation Mission (AIM·NITI Aayog)",
            "PLI (Production-Linked Incentive) — 14개 분야 생산 보조금",
        ],
        "gov_rd_pct_gdp":   0.7,    # 선진국 대비 낮음 — 민간 R&D 확대 중
        "unicorns":         110,
        "exit_options":     ["NSE Emerge·BSE SME (소형 상장)", "NSE·BSE 메인보드", "나스닥·NYSE (GDR·ADR)", "M&A"],
        "corporate_vc":     ["TCS Ventures", "Wipro Ventures", "Infosys Ventures", "Tata Capital"],
        "special_notes": [
            "제로-결함 제조: PLI 인센티브 최대 5~15% (분야별 상이) — 현지 생산 필수",
            "India Stack: Aadhaar·UPI·ONDC — 핀테크·에그리테크 API 생태계 세계 선진",
            "GLP 면제: 인도 CDSCO는 일부 분야 GLP 시험 면제 → 인도 내 임상 병행 필요",
            "딥테크 펀드: SEBI 규정 완화로 AIF(대안투자펀드) 딥테크 투자 증가",
        ],
    },
    "RU": {
        "vc_total_usd_bn":  0.3,   # 2022년 이후 급감
        "avg_series_a_usd": 500_000,
        "key_programs":     [
            "Skolkovo 재단 (세금혜택·보조금·연구지원)",
            "RVC (Russian Venture Company — 국가 펀드오브펀즈)",
            "Роснано (Rusnano — 나노기술 국가 펀드)",
            "РФРИТ (디지털기술 발전기금)",
            "ФСИ (Фонд Содействия Инновациям — 혁신지원기금, '비니크 프로그램')",
        ],
        "gov_rd_pct_gdp":   1.1,
        "unicorns":         3,     # 2022년 이후 대부분 출국
        "exit_options":     ["MOEX (모스크바 증권거래소)", "M&A(국내)", "전략적 투자자"],
        "special_notes": [
            "2022년 이후 서방 VC 철수 — 국내 자금 의존도 90%+",
            "Skolkovo: 세금 혜택(소득세·VAT 면제) + 규제 샌드박스 유지",
            "뇌 유출(Brain Drain): IT인재 대규모 해외 이주 → 채용 경쟁력 약화",
            "병렬 수입(平行수입): 2022년 합법화 — 서방 제품 무허가 수입 가능",
            "국가 투자: 방산·에너지·우주·AI 국가 전략 기업 지원 지속",
        ],
        "sanction_risk":    "신규 외국 투자·사업 진출 사실상 불가 (서방 기업 기준)",
    },
    "DEV": {
        "vc_total_usd_bn":  {"IN_excl": 8, "SEA": 8, "AFR": 1.5},
        "avg_series_a_usd": 2_000_000,
        "key_programs": {
            "multilateral": [
                "World Bank IFC SME Ventures",
                "ADB Ventures",
                "AfDB",
                "IADB Lab",
                "GCF (녹색기후기금)",
            ],
        },
        "exit_options":     ["M&A(MNC)", "지역 IPO", "2차 매각"],
    },
}

# ─────────────────────────────────────────────────────────
# ④ GTM (시장 진입) 전략
# ─────────────────────────────────────────────────────────
GTM_STRATEGY: dict[str, dict] = {
    "KR": {
        "recommended_channels": ["정부 R&D→대기업 공급망", "TIPS→코스닥"],
        "partnership_model":    "대기업 CVC(삼성·현대·LG·SK)",
        "sales_cycle_months":   6,
        "pilot_approach":       "스마트팜 실증단지·농진청 시범사업",
        "language":             "한국어 필수",
        "cultural_notes":       "빠른 의사결정·관계 중심·정부 신뢰 높음",
    },
    "US": {
        "recommended_channels": ["PLG→ENT", "파트너 리셀러", "DoD 조달"],
        "partnership_model":    "직접영업(AE) + 채널 파트너",
        "sales_cycle_months":   9,
        "pilot_approach":       "Innovation Challenge + Pilot-as-a-Service",
        "language":             "영어",
        "cultural_notes":       "ROI 중심·계약 문화·빠른 결정",
    },
    "EU": {
        "recommended_channels": ["Horizon Europe 과제→공공조달", "EIC Accelerator"],
        "partnership_model":    "유럽 TLO·Fraunhofer·KIC 네트워크",
        "sales_cycle_months":   12,
        "pilot_approach":       "EU Living Lab·DIH 실증",
        "language":             "영어+현지어",
        "cultural_notes":       "규제 준수·지속가능성·사회적 가치",
    },
    "JP": {
        "recommended_channels": [
            "일본 대기업 파트너십 (소지·伊藤忠·三菱商事 등 종합상사 통한 유통)",
            "NEDO·JST 공동연구 → 대기업 기술이전",
            "정부 실증사업(Society 5.0·スーパーシティ 실증)",
            "J-Startup 프로그램 활용 (경산성 선발 → 규제 완화·공공조달 우선)",
        ],
        "partnership_model":    "종합상사(総合商社) 또는 대기업 전략투자·合弁회사(JV)",
        "sales_cycle_months":   18,
        "pilot_approach":       "PoC(개념검증) → 파일럿 → 제품화 3단계, 최소 18개월",
        "language":             "일본어 필수 (기술 서류·영업 모두)",
        "cultural_notes": [
            "넴아와시(根回し): 의사결정 전 관계자 사전 합의 필수",
            "실패 회피 문화: 검증된 기술·레퍼런스 우선 — 첫 고객 확보가 핵심",
            "명함(名刺) 교환·에티켓 — 관계 구축 투자 필수",
            "시간 정확성 절대적 — 납기·약속 이행이 신뢰의 기본",
            "로컬라이제이션: UI·서류 일본어화, 일본 안전 규격 적합 필수",
        ],
        "market_entry_model":   "직접 설립보다 현지 파트너사와 합병회사(合弁) 또는 대리점 계약 시작 권장",
        "gtm_sequence":         ["PoC 파트너 확보 → 정부 실증사업 참여 → NEDO 공동연구 → 상용화"],
    },
    "CN": {
        "recommended_channels": [
            "B2G: 정부 조달·국유기업 공급망 (안정적이나 진입장벽 높음)",
            "B2B: 민영기업·IT기업(알리바바·화웨이·바이두 에코시스템) 파트너십",
            "플랫폼: 타오바오·징동·핀둬둬·더우인 직판 (소비재)",
            "자유무역시험구(FTZ): 상하이·선전·하이난 FTZ 입주 후 전국 확장",
        ],
        "partnership_model":    "합작법인(JV) 또는 현지 대리인(代理商) — 단독 외자법인(WFOE) 한계 있음",
        "sales_cycle_months":   12,
        "pilot_approach":       "FTZ 내 시범사업 → 국가급 실증 프로젝트 → 전국 확산",
        "language":             "중국어(만다린) 필수 — 영어 의존 금지",
        "cultural_notes": [
            "关係(관시): 인맥·신뢰 관계 선행 — 비즈니스는 관계 이후",
            "面子(면자): 공개적 비판·거절 금물 — 체면 손상 없이 문제 해결",
            "가격 협상: 최초 제안의 50~70% 수준 예상",
            "지방정부 관계: 각 성·시 정부와의 관계 구축 중요 (보조금·토지·허가)",
            "파트너 선정: 배경 조사(Due Diligence) 철저 — 문화혁명 이후 신뢰 구조 복잡",
        ],
        "market_entry_model":   "WFOE(외자독자법인) vs JV(합작법인) vs VIE 구조 — 업종·목적별 선택",
        "risks":                ["기술 유출", "규제 급변", "플랫폼 독점(빅테크) 의존", "US-CN 디커플링"],
        "gtm_sequence":         ["FTZ 입주 → 정부 파일럿 → 현지 파트너 JV → 전국 확산"],
    },
    "IN": {
        "recommended_channels": [
            "B2G: 정부 조달(GeM 플랫폼) — Make in India 현지화 필수",
            "B2B: IT기업(인포시스·위프로·TCS) 공급망 + 농협(IFFCO·KRIBHCO)",
            "B2C: 모바일 퍼스트 — 인도 스마트폰 보급 80%, 저가 데이터",
            "D2F(Direct to Farmer): APMC 우회 → 농부 직거래 플랫폼(AgriBazaar·Ninjacart)",
        ],
        "partnership_model":    "현지 법인(Private Limited) 설립 + 현지 유통 파트너",
        "sales_cycle_months":   12,
        "pilot_approach":       "소규모 파일럿(10~50 농가) → 주정부 PPP → 중앙정부 사업",
        "language":             "영어 (공용어) + 지역어 (힌디어·타밀어·텔루구어 등 22개 언어)",
        "cultural_notes": [
            "가격 민감도 매우 높음 — '인도 가격(India Price)'은 글로벌 가격의 1/5~1/3",
            "다양성: 29개 주마다 문화·언어·규제 상이 — 단일 전략 불가",
            "Jugaad(저비용 혁신): 현지 환경에 맞는 간소화 제품 선호",
            "결정 속도 느림 — 합의 기반 의사결정, 계층적 승인 구조",
            "관계 중요: 소개(Referral) 없는 콜드콜 효과 낮음",
        ],
        "market_entry_model":   "인도는 단일 시장이 아님 — 주별(State) 진입 전략 필요",
        "tier_strategy": {
            "tier1": "뭄바이·델리·벵갈루루 (B2B·IT·스타트업)",
            "tier2": "푸네·하이데라바드·아흐마다바드 (제조·AgriTech)",
            "tier3": "농촌 지역 (AgriTech·핀테크·에듀테크 리프로그 기회)",
        },
        "gtm_sequence":         ["현지 법인 설립 → PLI 신청 → GeM 등록 → 주정부 PPP → 전국 확장"],
    },
    "RU": {
        "recommended_channels": [
            "⚠️ 서방 기업: 2022년 이후 신규 진출 불가 (제재)",
            "비제재국 기업: Skolkovo 입주 → 국내 유통 파트너",
            "기술이전: 특허 라이선스보다 기술 매각(Buy-out) 선호 (환율 리스크)",
        ],
        "partnership_model":    "러시아 현지 파트너 + 에스크로 결제 (SWIFT 차단 우회)",
        "sales_cycle_months":   24,
        "pilot_approach":       "Skolkovo 실증 → 국가 조달",
        "language":             "러시아어 필수 (영어 통하지 않는 경우 多)",
        "cultural_notes": [
            "Blat(블라트): 인맥·연줄 기반 비즈니스 — 공식 채널보다 인맥이 중요",
            "협상 문화: 강경한 초기 입장 → 양보를 통한 합의 과정",
            "국가 리스크: 갑작스러운 규제 변경·자산 몰수 리스크",
            "결제: SWIFT 차단 → 중국 CIPS·비트코인·루블 직결제 사용 증가",
            "평행 수입: 서방 브랜드 제품 병렬 수입 확대 — 정품 채널 무력화",
        ],
        "sanction_note":        "서방 기업 신규 진출 불가. 비제재국(UAE·터키·중앙아시아) 우회 구조만 가능",
        "exit_strategy":        "진출보다 철수(Exit) 전략 먼저 검토 필요",
    },
    "DEV": {
        "recommended_channels": ["원조·ODA 연계", "현지 통신사/NGO 파트너십", "모바일 B2C"],
        "partnership_model":    "현지 임팩트 허브 + NGO + 정부 농업부",
        "sales_cycle_months":   18,
        "pilot_approach":       "CGIAR·FAO·WFP 시범사업 연계",
        "language":             "현지어 필수",
        "cultural_notes":       "신뢰 구축 우선·현지인 고용·지역사회 참여",
    },
}

# ─────────────────────────────────────────────────────────
# ⑤ ESG·SDG 우선순위
# ─────────────────────────────────────────────────────────
ESG_PRIORITY: dict[str, dict] = {
    "KR": {
        "top_sdgs":        ["SDG 9 산업혁신", "SDG 12 지속가능소비", "SDG 13 기후행동"],
        "carbon_target":   "2030년 NDC 40% 감축(2018 대비), 2050 탄소중립",
        "esg_framework":   "K-ESG 가이드라인·한국거래소 ESG공시·TCFD 의무(2025~)",
        "green_finance":   "한국녹색채권·K-Taxonomy·탄소배출권(KAU)",
        "key_metric":      "온실가스 배출권 + TCFD",
    },
    "US": {
        "top_sdgs":        ["SDG 9", "SDG 7", "SDG 13"],
        "carbon_target":   "2030년 50~52% 감축(2005 대비), IRA $369B 청정에너지",
        "esg_framework":   "SEC 기후공시(2024)·SASB·GRI·TCFD",
        "green_finance":   "IRA 세제혜택·녹색채권(ICMA)·ESG ETF",
        "key_metric":      "Scope 1/2/3 SEC 의무공시(2026~)",
    },
    "EU": {
        "top_sdgs":        ["SDG 13", "SDG 7", "SDG 12", "SDG 11"],
        "carbon_target":   "2030년 55% 감축(Fit for 55), 2050 탄소중립",
        "esg_framework":   "CSRD·EU Taxonomy·SFDR·ESRS",
        "green_finance":   "EU Green Bond Standard·CBAM(탄소국경조정 2026~)",
        "key_metric":      "EU Taxonomy 6대 환경목표 + CBAM",
    },
    "JP": {
        "top_sdgs":        ["SDG 13 기후행동", "SDG 7 청정에너지", "SDG 9 산업혁신", "SDG 11 스마트시티"],
        "carbon_target":   "2030년 46% 감축(2013 대비), 2050 탄소중립(カーボンニュートラル)",
        "esg_framework":   "TCFD(일본 의무 공시 선도국)·TNFD(자연 관련 공시)·GX推進法(그린전환법)",
        "green_finance":   "GX트랜지션 채권(10년 20조엔)·J-Credit·재생가능에너지 FIT/FIP제도",
        "key_metric":      "TCFD 공시(도쿄증권거래소 Prime 상장사 의무)·카본크레딧(J-Credit)",
        "special_notes": [
            "사회과제 해결형: 少子高齢化(저출산 고령화)·식량자급률 향상 등 사회과제 연계 ESG 우대",
            "수소 전략: 2030년 수소 300만톤·2050년 2,000만톤 공급 목표 — 수소기술 기업 우대",
            "원자력 재가동: 2023년 GX전환법으로 원전 재가동·신형 원전 건설 정책 전환",
            "아시아 탄소크레딧: JCM(日本-개도국 공동크레딧 메커니즘) — 25개국 파트너",
        ],
    },
    "CN": {
        "top_sdgs":        ["SDG 13 기후행동", "SDG 7 청정에너지", "SDG 9 산업혁신", "SDG 2 식량"],
        "carbon_target":   "2030년 탄소 피크(炭素达峰), 2060년 탄소중립(炭素中和)",
        "esg_framework":   "A股 ESG공시(CSRC·거래소 의무화 추진)·녹색금융 지침·TCFD 준용",
        "green_finance":   "중국 녹색채권(Green Bond, 세계 2위 규모)·중국 탄소시장(CCER·전국 ETS)·녹색신용지침",
        "key_metric":      "全국 탄소시장(CEA·CCER) + 녹색금융 평가 — 은행 의무 녹색신용 비율",
        "special_notes": [
            "전국 ETS: 2021년 발전업 1위 시작 → 단계적 확대 (철강·시멘트·화학 예정)",
            "녹색채권 특징: 중국 정의와 국제 정의 상이 — 석탄 청정이용 포함 논란",
            "기후금융 기회: 신에너지(풍력·태양광) 세계 최대 시장 — 글로벌 공급망 핵심",
            "이중탄소(双碳) 정책: 성(省)·시(市)별 탄소감축 할당 → 지방정부 정책 편차 주의",
        ],
        "ets_details": {
            "name":     "全国碳市场 (전국 탄소 배출권 거래 시장)",
            "started":  "2021년",
            "price_rmb": "약 60~80위안/톤 (USD 8~11)",
            "sectors":  "발전업 우선, 단계적 확대",
        },
    },
    "IN": {
        "top_sdgs":        ["SDG 7 청정에너지", "SDG 13 기후행동", "SDG 2 식량", "SDG 9 산업혁신", "SDG 1 빈곤"],
        "carbon_target":   "2030년 GDP 단위 탄소강도 45% 감축(2005 대비), 비화석 전력 50%, 2070 탄소중립",
        "esg_framework":   "SEBI BRSR(Business Responsibility and Sustainability Report, 의무)·GRI·TCFD 선택",
        "green_finance":   "녹색채권(IREDA·SEBI 녹색본드)·재생에너지 인증서(REC)·PM-KUSUM 태양광 보조금",
        "key_metric":      "BRSR 의무공시(NSE·BSE 상위 1000사)·재생에너지 RPO(의무 구매 비율)",
        "special_notes": [
            "신재생에너지: 2030년 500GW 재생에너지 목표 — 태양광·풍력 세계 최대 잠재 시장",
            "탄소시장 부재: 인도는 자발적 탄소시장(VCMI) 단계 — 의무 탄소 거래제 미도입",
            "기후 취약국: 몬순 강우 변화·폭염·홍수 — 기후 적응 기술 수요 매우 높음",
            "International Solar Alliance(ISA): 인도 주도 국제태양광동맹 — 120개국 참여",
            "Panchamrit: 인도의 5대 기후 약속 — 500GW 비화석·50% 비화석 전력·1B톤 감축 등",
        ],
    },
    "RU": {
        "top_sdgs":        ["SDG 9 산업혁신", "SDG 7 청정에너지", "SDG 13 기후행동"],
        "carbon_target":   "2060년 탄소중립 (파리협정 NDC 2030년 1990년 대비 30% 감축)",
        "esg_framework":   "러시아 기업지배구조 코드·RSPP ESG인덱스·Мосбиржа(MOEX) ESG요건",
        "green_finance":   "러시아 녹색채권(모스크바거래소)·Росатом(원자력) 그린 택소노미·탄소단위(углеродные единицы)",
        "key_metric":      "탄소세 도입 논의 중(2025년 후 예상)·러시아 녹색분류체계(Green Taxonomy)",
        "special_notes": [
            "2022년 이후 서방 ESG 평가기관(MSCI·Sustainalytics) 러시아 기업 평가 중단",
            "CBAM 리스크: EU CBAM 2026년 — 러시아 철강·알루미늄·비료 수출 타격 예상",
            "에너지 전환 역설: 최대 화석연료 수출국 vs 탄소중립 선언 — 실행 가능성 낮음",
            "원자력: Росатом(로사톰) 원전 기술 세계 최고 — 개도국 원전 수출 ESG 논란",
            "탄소발자국 보고: 2023년 이후 단계적 의무화 (연방법 № 296-FZ)",
        ],
        "sanction_note":   "서방 ESG 평가·녹색채권 시장 접근 차단. 중국·중동 ESG 기준 준용",
    },
    "DEV": {
        "top_sdgs":        ["SDG 1", "SDG 2", "SDG 3", "SDG 6", "SDG 7"],
        "carbon_target":   "NDC 제출국 대부분 (이행 역량 부족)",
        "esg_framework":   "GRI·IIRC·UN SDG 자발적 보고",
        "green_finance":   "GCF·GEF·ADB 기후금융·혼합금융",
        "key_metric":      "적응(Adaptation) > 완화(Mitigation)",
    },
}


# ─────────────────────────────────────────────────────────
# RegionalContext + RegionalConnector
# ─────────────────────────────────────────────────────────
@dataclass
class RegionalContext:
    tech_id:    str
    regions:    dict = field(default_factory=dict)
    ip:         dict = field(default_factory=dict)
    regulatory: dict = field(default_factory=dict)
    funding:    dict = field(default_factory=dict)
    gtm:        dict = field(default_factory=dict)
    esg:        dict = field(default_factory=dict)
    priority:   list = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__


class RegionalConnector:
    """
    8개 지역(KR·US·EU·JP·CN·IN·RU·DEV) 통합 컨텍스트 생성기.
    JP/CN/IN/RU는 DEV에서 독립한 전략 지역으로 완전 분기.
    """

    def analyze(self, target_countries: list[str], tech_type: str,
                efficiency_pct: float = 10.0) -> RegionalContext:
        ctx = RegionalContext(tech_id=f"{tech_type}_{'-'.join(target_countries[:3])}")

        region_map = classify_regions(target_countries)
        ctx.regions = {
            "input_countries": target_countries,
            "classified":      region_map,
            "active_regions":  list(region_map.keys()),
        }

        ctx.ip         = {r: IP_ENV.get(r, IP_ENV["DEV"])         for r in region_map}
        ctx.regulatory = {
            r: {
                "framework":      REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"])["framework"],
                "certifications": REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"])["certifications"].get(tech_type, "해당 없음"),
                "avg_months":     REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"]).get("avg_cert_months", {}).get(tech_type),
                "cost_usd":       REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"]).get("cost_usd", {}).get(tech_type),
                "sandbox":        REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"]).get("sandbox"),
                "special_notes":  REGULATORY_ENV.get(r, REGULATORY_ENV["DEV"]).get("special_notes", []),
            }
            for r in region_map
        }
        ctx.funding  = {r: FUNDING_ENV.get(r, FUNDING_ENV["DEV"])  for r in region_map}
        ctx.gtm      = {r: GTM_STRATEGY.get(r, GTM_STRATEGY["DEV"]) for r in region_map}
        ctx.esg      = {r: ESG_PRIORITY.get(r, ESG_PRIORITY["DEV"]) for r in region_map}
        ctx.priority = self._recommend_priority(region_map, tech_type)

        return ctx

    def country_profile(self, country_code: str, tech_type: str) -> dict:
        """단일 국가 상세 프로파일"""
        cc = country_code.upper()
        region = classify_region(cc)
        return {
            "country":     cc,
            "region":      region,
            "ip":          IP_ENV.get(region, IP_ENV["DEV"]),
            "regulatory":  REGULATORY_ENV.get(region, REGULATORY_ENV["DEV"]),
            "funding":     FUNDING_ENV.get(region, FUNDING_ENV["DEV"]),
            "gtm":         GTM_STRATEGY.get(region, GTM_STRATEGY["DEV"]),
            "esg":         ESG_PRIORITY.get(region, ESG_PRIORITY["DEV"]),
        }

    def patent_filing_strategy(self, target_countries: list[str],
                                budget_usd: float = 50_000) -> dict:
        region_map = classify_regions(target_countries)
        costs      = {r: IP_ENV.get(r, IP_ENV["DEV"])["filing_cost_usd"] for r in region_map}
        total_cost = sum(costs.values())

        order = []
        priority_regions = ["US", "KR", "JP", "CN", "EU", "IN", "RU", "DEV"]
        rationale_map = {
            "US":  "세계 최대 시장·NPE 방어·USPTO 집행력",
            "KR":  "국내 우선·KIPO 빠름·대기업 공급망",
            "JP":  "아시아 제조허브·JPO 빠름(14개월)·크로스라이선스",
            "CN":  "세계 최대 제조·모방 방어·실용신안 선점",
            "EU":  "UPC 단일법원·EPO 광역 보호",
            "IN":  "10억 소비자·만성 모방 방어·PCT PPH 활용",
            "RU":  "EAPO(9개국 동시)·우주·방산 기술 보호",
            "DEV": "ARIPO·OAPI 저비용 광역 보호",
        }
        for r in priority_regions:
            if r in region_map:
                order.append({
                    "region": r, "cost_usd": costs[r], "rationale": rationale_map.get(r, "")
                })
        return {
            "recommended_order": order,
            "total_cost_usd":    total_cost,
            "budget_usd":        budget_usd,
            "feasible":          total_cost <= budget_usd,
            "pct_first":         True,
            "pct_note":          "PCT 출원 → 30개월 내 국가단계 진입 결정",
        }

    def sanction_check(self, target_countries: list[str]) -> dict:
        """제재·지정학 리스크 체크"""
        HIGH_RISK = {"RU", "BY", "IR", "SY", "KP", "CU"}
        MEDIUM_RISK = {"CN", "VE", "SD"}
        results = []
        for cc in target_countries:
            c = cc.upper()
            if c in HIGH_RISK:
                level = "HIGH"
                note  = "서방 제재 대상 — 서방 기업 거래 시 OFAC·EU·UK 제재 법률 검토 필수"
            elif c in MEDIUM_RISK:
                level = "MEDIUM"
                note  = "부분 제재·수출통제 대상 — EAR/ITAR·US Entity List 확인 필요"
            else:
                level = "LOW"
                note  = "주요 제재 없음"
            results.append({"country": c, "risk_level": level, "note": note})
        return {"sanction_check": results, "tool": "OFAC·EU OJ·UK OFSI 교차 확인 권장"}

    def _recommend_priority(self, region_map: dict, tech_type: str) -> list[dict]:
        scores = {
            "KR": {"agritech": 90, "software_saas": 85, "medical_device": 75, "energy": 70,  "manufacturing": 75, "default": 80},
            "US": {"agritech": 75, "software_saas": 95, "medical_device": 90, "energy": 85,  "manufacturing": 70, "default": 85},
            "EU": {"agritech": 70, "software_saas": 80, "medical_device": 85, "energy": 90,  "manufacturing": 80, "default": 80},
            "JP": {"agritech": 80, "software_saas": 70, "medical_device": 80, "energy": 75,  "manufacturing": 90, "default": 78},
            "CN": {"agritech": 85, "software_saas": 75, "medical_device": 65, "energy": 85,  "manufacturing": 90, "default": 78},
            "IN": {"agritech": 88, "software_saas": 80, "medical_device": 65, "energy": 82,  "manufacturing": 75, "default": 78},
            "RU": {"agritech": 40, "software_saas": 30, "medical_device": 35, "energy": 40,  "manufacturing": 35, "default": 35},
            "DEV":{"agritech": 85, "software_saas": 65, "medical_device": 60, "energy": 80,  "manufacturing": 55, "default": 70},
        }
        rationale_map = {
            ("JP",  "manufacturing"):  "세계 최고 제조품질·로봇·소재 허브 — 공동연구 우선",
            ("JP",  "agritech"):       "고령화 농업 위기·스마트팜 국가 투자·高부가 식품 시장",
            ("CN",  "manufacturing"):  "세계 최대 제조 허브·거대 내수·공급망 진입",
            ("CN",  "agritech"):       "14억 식량안보·농업 디지털화 국가 의제·대규모 파일럿",
            ("IN",  "agritech"):       "14억 농업인구·식량안보 수요·ODA+VC 혼합자금",
            ("IN",  "software_saas"):  "영어권 IT인력·SaaS 수출기지·인도 스택(UPI·Aadhaar)",
            ("RU",  "default"):        "⚠️ 제재 리스크 최고 — 진출 전 법률 검토 필수",
        }
        result = []
        for region in region_map:
            sc    = scores.get(region, scores["DEV"])
            score = sc.get(tech_type, sc["default"])
            rat   = rationale_map.get((region, tech_type),
                    rationale_map.get((region, "default"),
                    f"{region} 시장 — {tech_type} 진입 전략 분석 필요"))
            result.append({
                "region":      region,
                "countries":   region_map[region],
                "entry_score": score,
                "rationale":   rat,
            })
        return sorted(result, key=lambda x: -x["entry_score"])
