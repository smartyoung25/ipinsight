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

# 실행전략 보완 4모듈 (Gap 해소)
from .g4_team_assessor import TeamAssessor            # 팀·실행 역량 평가
from .g5_unit_economics import UnitEconomicsAssessor  # CAC·LTV·Burn Rate
from .g2_funding_planner import FundingPlanner         # 자금조달 시나리오
from .g8_regulatory_roadmap import RegulatoryRoadmapAgent  # 도메인별 규제 로드맵

__all__ = [
    # 기존 G0~G10
    "TechScout", "IPStructurer", "TRLAssessor", "MarketScanner",
    "CustomerValidator", "BMDesigner", "ValuationEngine", "PoCManager",
    "MRLARLAssessor", "DealStructurer", "PerformanceTracker",
    # IP Lifecycle 확장
    "IDFGenerator", "PatentPortfolioStrategist", "WhitespaceAnalyzer",
    "PatentabilityAssessor",
    "GlobalIPStrategist", "CompetitiveMonitor", "PortfolioOptimizer",
    # 실행전략 보완
    "TeamAssessor", "UnitEconomicsAssessor", "FundingPlanner", "RegulatoryRoadmapAgent",
]
