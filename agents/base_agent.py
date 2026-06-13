"""공통 Agent 기반 클래스 — 모든 G0~G10 Agent가 상속"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Literal
from pathlib import Path

# 프로젝트 루트 .env 자동 로드 (python-dotenv 설치 시)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass

Gate = Literal["Go", "Hold", "Kill"]

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


@dataclass
class StageResult:
    stage: str
    score: float          # 0~100
    gate: Gate
    output_doc: dict      # 단계별 핵심 산출물
    next_actions: list[str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class BaseAgent:
    stage_id: str = "G?"
    stage_name: str = "기본 단계"

    def __init__(self):
        self._llm_client = None
        self._init_llm()

    def _init_llm(self):
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key:
            try:
                import anthropic
                self._llm_client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                pass

    def _llm(self, prompt: str, system: str = "") -> str:
        """LLM 호출 — API 키 없으면 규칙기반 폴백"""
        if self._llm_client is None:
            return self._rule_fallback(prompt)
        try:
            msg = self._llm_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system=system or f"당신은 글로벌 기술사업화 전문가입니다. {self.stage_name} 단계를 담당합니다.",
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception:
            return self._rule_fallback(prompt)

    def _rule_fallback(self, prompt: str) -> str:
        return f"[규칙기반 폴백] {self.stage_name} 분석 완료. LLM 키 설정 시 상세 분석 가능."

    def _load_knowledge(self, filename: str) -> dict:
        path = KNOWLEDGE_DIR / filename
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _gate_from_score(self, score: float) -> Gate:
        if score >= 65:
            return "Go"
        if score >= 40:
            return "Hold"
        return "Kill"

    def assess(self, input_data: dict) -> StageResult:
        raise NotImplementedError
