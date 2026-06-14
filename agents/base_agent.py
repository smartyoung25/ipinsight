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
        """LLM 클라이언트 초기화.

        우선순위: Groq(키 있을 때) > Anthropic(키+크레딧) > 규칙기반
        Groq가 설정되면 무료 즉시 사용 가능하므로 Anthropic보다 우선.
        Anthropic만 있을 때는 크레딧 상태를 런타임에 확인.
        """
        # 1순위: Groq (키 있으면 우선 — 무료·안정적)
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key:
            try:
                from openai import OpenAI
                self._llm_client = OpenAI(
                    api_key=groq_key,
                    base_url="https://api.groq.com/openai/v1",
                )
                self._llm_backend = "groq"
                return
            except ImportError:
                pass

        # 2순위: Anthropic (Groq 없을 때)
        ant_key = os.getenv("ANTHROPIC_API_KEY", "")
        if ant_key:
            try:
                import anthropic
                self._llm_client = anthropic.Anthropic(api_key=ant_key)
                self._llm_backend = "anthropic"
                return
            except ImportError:
                pass

        self._llm_client = None
        self._llm_backend = "rule"

    def _llm(self, prompt: str, system: str = "") -> str:
        """LLM 호출 — Anthropic → Groq → 규칙기반 폴백 순서."""
        if self._llm_client is None:
            return self._rule_fallback(prompt)

        backend = getattr(self, "_llm_backend", "anthropic")
        sys_msg = system or f"당신은 글로벌 기술사업화 전문가입니다. {self.stage_name} 단계를 담당합니다."

        try:
            if backend == "anthropic":
                msg = self._llm_client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    system=sys_msg,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text
            elif backend == "groq":
                resp = self._llm_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    max_tokens=2048,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": prompt},
                    ],
                )
                return resp.choices[0].message.content
        except Exception as _e:
            import logging as _log
            _log.getLogger("base_agent").warning("LLM(%s) 실패 → 규칙폴백: %s", backend, _e)
            return self._rule_fallback(prompt)

    def _rag(self, query: str, top_k: int = 5, source_filter: str = "") -> str:
        """RAG 검색 — knowledge/*.json 벡터 인덱스에서 관련 컨텍스트 반환"""
        try:
            from pipeline.rag_retriever import rag_search
            return rag_search(query, top_k=top_k, source_filter=source_filter)
        except Exception:
            return ""

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
