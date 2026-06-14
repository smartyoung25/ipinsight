"""Pydantic 요청/응답 스키마"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Optional


class StageRequest(BaseModel):
    tech_id: str = Field(..., description="기술 고유 ID")
    input_data: dict[str, Any] = Field(..., description="단계별 입력 데이터")


class PipelineRequest(BaseModel):
    tech_id: str = Field(..., description="기술 고유 ID")
    stage_inputs: dict[int, dict[str, Any]] = Field(
        ..., description="단계별 입력 데이터. {0: {...}, 1: {...}}"
    )
    stop_on_kill: bool = Field(True, description="Kill 판정 시 파이프라인 중단 여부")


class FundingMatchRequest(BaseModel):
    trl: int = Field(..., ge=1, le=9, description="현재 TRL 단계")
    country: str = Field("", description="대상 국가 코드 (KOR/USA/EU/ISR/SGP/JPN/CHN)")
    sector: str = Field("", description="산업 분야")
    stage_id: str = Field("", description="현재 프로세스 단계 (G0~G10)")


class StageResult(BaseModel):
    stage: str
    score: float
    gate: str
    output_doc: dict[str, Any]
    next_actions: list[str]
    warnings: list[str] = []


# ── Phase 2 — 엔드포인트별 타입 스키마 ──────────────────────────

class IPAnalysisRequest(BaseModel):
    """IP 라이프사이클 / 특허 분석"""
    tech_id: str = Field(..., description="기술 고유 ID")
    tech_name: str = Field(..., description="기술명")
    tech_description: str = Field("", description="기술 설명 (선택)")
    ipc_codes: list[str] = Field(default_factory=list, description="IPC 코드 목록")
    cpc_codes: list[str] = Field(default_factory=list, description="CPC 코드 목록")
    target_markets: list[str] = Field(["KR", "US", "EP"], description="목표 시장")
    trl: int = Field(3, ge=1, le=9, description="현재 TRL")
    input_data: dict[str, Any] = Field(default_factory=dict)


class GapRequest(BaseModel):
    """갭 보완 / 기술 이전 모듈"""
    tech_id: str = Field(..., description="기술 고유 ID")
    tech_name: str = Field("", description="기술명")
    industry_sector: str = Field("", description="산업 섹터 (IT·바이오·제조·에너지 등)")
    trl: int = Field(3, ge=1, le=9, description="현재 TRL")
    input_data: dict[str, Any] = Field(default_factory=dict)


class ExecutionRequest(BaseModel):
    """실행 전략 / 사업화 모듈"""
    tech_id: str = Field(..., description="기술 고유 ID")
    tech_name: str = Field("", description="기술명")
    business_model: str = Field("", description="사업 모델 (B2B/B2C/라이선싱/JV 등)")
    target_revenue_usd: Optional[float] = Field(None, description="목표 매출 (USD)")
    input_data: dict[str, Any] = Field(default_factory=dict)


class RoadmapRequest(BaseModel):
    """G0→G10 전체 파이프라인 로드맵"""
    tech_id: str = Field(..., description="기술 고유 ID")
    tech_name: str = Field(..., description="기술명")
    tech_type: str = Field("general", description="기술 유형 (biotech·ICT·device·material·process·general)")
    region: str = Field("KOR", description="주요 목표 국가 (KOR·USA·EU·JPN·CHN 등)")
    trl_current: int = Field(3, ge=1, le=9, description="현재 TRL")
    trl_target: int = Field(9, ge=1, le=9, description="목표 TRL")
    stage_inputs: dict[str, Any] = Field(default_factory=dict, description="단계별 사전 입력값")


class ValuationRequest(BaseModel):
    """기술 가치평가 (G6)"""
    tech_id: str = Field(..., description="기술 고유 ID")
    revenue_forecast: dict[str, float] = Field(
        default_factory=dict, description="연도별 매출 예측 {2025: 1e6, ...}"
    )
    discount_rate: float = Field(0.15, ge=0.0, le=1.0, description="할인율")
    royalty_rate: float = Field(0.05, ge=0.0, le=0.5, description="로열티율")
    method: str = Field("dcf", description="평가 방법 (dcf·cca·roa)")
    input_data: dict[str, Any] = Field(default_factory=dict)


class RegulationRequest(BaseModel):
    """규제·인증 경로 (G7/G8)"""
    tech_id: str = Field(..., description="기술 고유 ID")
    product_type: str = Field("", description="제품 유형 (의료기기·식품·화학·소프트웨어 등)")
    target_countries: list[str] = Field(["KR"], description="인증 목표 국가")
    fda_510k: bool = Field(False, description="FDA 510(k) 대상 여부")
    input_data: dict[str, Any] = Field(default_factory=dict)


class PCMLRequest(BaseModel):
    """PCML v2.0 청구항 구조 분석 요청 (New PCML v2.0 전용)"""
    tech_id: str = Field(..., description="기술/특허 고유 ID")
    patent_id: str = Field("", description="특허번호 (KR10-..., US..., EP...). tech_id 기본 사용")
    patent_text: str = Field("", description="특허 원문 직접 입력 (청구항 + 명세서 권장)")
    input_mode: str = Field(
        "full_spec",
        description="claim_only | full_spec | enriched. patent_text 없으면 자동 claim_only",
    )
    input_data: dict[str, Any] = Field(default_factory=dict, description="추가 입력 (legal_raw, family_raw 등)")


class TokenRequest(BaseModel):
    """JWT 토큰 발급"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT 토큰 발급 응답"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class JobStatus(BaseModel):
    """비동기 Job 상태"""
    job_id: str
    status: str = Field(..., description="queued / running / completed / failed")
    created_at: float = 0.0
    completed_at: Optional[float] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """표준 오류 응답"""
    code: int
    message: str
    detail: str = ""
