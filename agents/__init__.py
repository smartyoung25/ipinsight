# G0~G10 기존 Agent
from .g0_tech_scout import TechScout
from .g1_ip_structurer import IPStructurer
from .g2_trl_assessor import TRLAssessor
from .g3_market_scanner import MarketScanner
from .g4_customer_validator import CustomerValidator
from .g5_bm_designer import BMDesigner
from .g6_valuation_engine import ValuationEngine
from .g7_poc_manager import PoCManager
from .g8_mrl_arl_assessor import MRLARLAssessor
from .g9_deal_structurer import DealStructurer
from .g10_performance_tracker import PerformanceTracker

# IP Lifecycle 확장 Agent (4단계 IP 프로세스 통합)
from .g0_idf_generator import IDFGenerator            # 1단계: 발명공개서(IDF)
from .g1_portfolio_strategist import PatentPortfolioStrategist  # 1단계: 특허 포트폴리오
from .g1_whitespace_analyzer import WhitespaceAnalyzer          # 1단계: 화이트스페이스 (WIPO)
from .g2_patentability_assessor import PatentabilityAssessor    # 2단계: 권리성 심화
from .g10_global_ip_strategist import GlobalIPStrategist        # 4단계: 글로벌 IP 전략
from .g10_competitive_monitor import CompetitiveMonitor         # 4단계: 경쟁대응
from .g10_portfolio_optimizer import PortfolioOptimizer         # 4단계: 포트폴리오 최적화

# ① 즉시 보완 (Gap Critical)
from .g4_team_assessor import TeamAssessor            # 팀·실행 역량 평가
from .g5_unit_economics import UnitEconomicsAssessor  # CAC·LTV·Burn Rate
from .g2_funding_planner import FundingPlanner         # 자금조달 시나리오
from .g8_regulatory_roadmap import RegulatoryRoadmapAgent  # 도메인별 규제 로드맵

# ② 중기 보완 (Gap Medium, 3개월)
from .g6_ir_deck import IRDeckGenerator                # IR Deck 자동 생성
from .g10_esg_impact import ESGImpactAssessor          # ESG·SDG 임팩트 평가
from .g1_trade_secret import TradeSecretAnalyzer       # 트레이드시크릿 vs 특허
from .g3_ecosystem_matcher import EcosystemMatcher     # 생태계 파트너 매칭

# ③ 장기 보완 (Gap Long-term, 6개월)
from .g10_exit_strategy import ExitStrategyDesigner    # M&A·IPO 엑시트 전략
from .g1_patent_maintenance import PatentMaintenanceOptimizer  # 특허 유지비 최적화

# Layer 3 서비스 — 수요조사서·SMK 자동 생성
from .g0_demand_survey import DemandSurveyGenerator    # 수요조사서
from .smk_generator import SMKGenerator                 # 사업화시장키트(SMK)

__all__ = [
    # 기존 G0~G10
    "TechScout", "IPStructurer", "TRLAssessor", "MarketScanner",
    "CustomerValidator", "BMDesigner", "ValuationEngine", "PoCManager",
    "MRLARLAssessor", "DealStructurer", "PerformanceTracker",
    # IP Lifecycle 확장
    "IDFGenerator", "PatentPortfolioStrategist", "WhitespaceAnalyzer",
    "PatentabilityAssessor",
    "GlobalIPStrategist", "CompetitiveMonitor", "PortfolioOptimizer",
    # ① Gap Critical
    "TeamAssessor", "UnitEconomicsAssessor", "FundingPlanner", "RegulatoryRoadmapAgent",
    # ② Gap Medium
    "IRDeckGenerator", "ESGImpactAssessor", "TradeSecretAnalyzer", "EcosystemMatcher",
    # ③ Gap Long-term
    "ExitStrategyDesigner", "PatentMaintenanceOptimizer",
    # Layer 3 서비스
    "DemandSurveyGenerator", "SMKGenerator",
]
