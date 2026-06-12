"""Pydantic 요청/응답 스키마"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any


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
