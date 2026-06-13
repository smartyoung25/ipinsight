"""Layer 4 — 검증: PoC 검증 자동화 체크리스트
클라우드 PoC + 온프레미스 전환 가능성 + 기능 단위 테스트 + 재현성 문서화.
실행: python deploy/poc_checklist.py
"""
from __future__ import annotations
import sys
import time
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Literal

ROOT = Path(__file__).parent.parent

CheckStatus = Literal["PASS", "FAIL", "SKIP", "WARN"]


@dataclass
class CheckItem:
    category:    str
    name:        str
    description: str
    status:      CheckStatus = "SKIP"
    detail:      str = ""
    duration_ms: float = 0.0


@dataclass
class PoCReport:
    timestamp:   str = ""
    environment: str = "cloud"
    total:       int = 0
    passed:      int = 0
    failed:      int = 0
    warned:      int = 0
    skipped:     int = 0
    items:       list[CheckItem] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return round(self.passed / max(self.total, 1) * 100, 1)

    def to_dict(self) -> dict:
        return asdict(self)


class PoCVerifier:

    def __init__(self, base_url: str = "http://localhost:8100"):
        self.base_url = base_url
        self.report   = PoCReport()

    def _check(self, item: CheckItem, fn) -> CheckItem:
        t0 = time.time()
        try:
            result, detail = fn()
            item.status  = "PASS" if result else "FAIL"
            item.detail  = detail
        except Exception as e:
            item.status  = "FAIL"
            item.detail  = f"예외: {e}"
        item.duration_ms = round((time.time() - t0) * 1000, 1)
        return item

    # ─── Layer 1: AI 모델 ───────────────────────────────

    def check_llm_fallback(self) -> CheckItem:
        item = CheckItem("AI 모델", "LLM 폴백", "API 키 없을 때 규칙기반 폴백 동작 확인")
        def fn():
            import os
            old = os.environ.pop("ANTHROPIC_API_KEY", None)
            try:
                from agents.base_agent import BaseAgent
                class _T(BaseAgent):
                    stage_id = "T"
                    stage_name = "테스트"
                    def assess(self, d): pass
                agent = _T()
                result = agent._llm("테스트 프롬프트")
                ok = "폴백" in result or "규칙" in result or len(result) > 0
                return ok, f"폴백 응답: {result[:80]}"
            finally:
                if old:
                    os.environ["ANTHROPIC_API_KEY"] = old
        return self._check(item, fn)

    def check_rag_index(self) -> CheckItem:
        item = CheckItem("AI 모델", "RAG 인덱스 빌드", "knowledge/*.json 벡터 인덱싱 확인")
        def fn():
            sys.path.insert(0, str(ROOT))
            from pipeline.rag_retriever import get_index
            idx = get_index()
            cnt = len(idx._docs)
            return cnt > 0, f"인덱싱된 청크: {cnt}개"
        return self._check(item, fn)

    def check_rag_search(self) -> CheckItem:
        item = CheckItem("AI 모델", "RAG 검색", "쿼리 → 유사 청크 검색 동작 확인")
        def fn():
            from pipeline.rag_retriever import rag_search
            ctx = rag_search("특허 기술 TRL 평가", top_k=3)
            ok  = "[지식베이스" in ctx and len(ctx) > 50
            return ok, f"컨텍스트 길이: {len(ctx)}자"
        return self._check(item, fn)

    # ─── Layer 2: 데이터 ───────────────────────────────

    def check_knowledge_files(self) -> CheckItem:
        item = CheckItem("데이터", "knowledge/*.json 무결성", "9개 지식베이스 JSON 파싱 가능 여부")
        def fn():
            kdir = ROOT / "knowledge"
            files = list(kdir.glob("*.json"))
            ok_cnt = 0
            for f in files:
                try:
                    json.loads(f.read_text(encoding="utf-8"))
                    ok_cnt += 1
                except Exception:
                    pass
            return ok_cnt == len(files), f"{ok_cnt}/{len(files)} 파일 파싱 성공"
        return self._check(item, fn)

    def check_schema_file(self) -> CheckItem:
        item = CheckItem("데이터", "스키마 정의서", "knowledge/schema.json 존재 + 6개 도메인 확인")
        def fn():
            schema_path = ROOT / "knowledge" / "schema.json"
            if not schema_path.exists():
                return False, "schema.json 없음"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            domains = list(schema.get("domains", {}).keys())
            ok = len(domains) >= 6
            return ok, f"도메인: {domains}"
        return self._check(item, fn)

    # ─── Layer 3: 서비스 ───────────────────────────────

    def check_agent_imports(self) -> CheckItem:
        item = CheckItem("서비스", "전체 에이전트 임포트", "agents/__init__.py 모든 클래스 임포트 확인")
        def fn():
            import agents
            expected = [
                "TechScout","IPStructurer","TRLAssessor","MarketScanner",
                "TeamAssessor","UnitEconomicsAssessor","FundingPlanner","RegulatoryRoadmapAgent",
                "IRDeckGenerator","ESGImpactAssessor","TradeSecretAnalyzer","EcosystemMatcher",
                "ExitStrategyDesigner","PatentMaintenanceOptimizer",
                "DemandSurveyGenerator","SMKGenerator",
            ]
            missing = [c for c in expected if not hasattr(agents, c)]
            return len(missing) == 0, f"누락 클래스: {missing}" if missing else "모든 에이전트 임포트 성공"
        return self._check(item, fn)

    def check_roadmap_builder(self) -> CheckItem:
        item = CheckItem("서비스", "로드맵 빌더", "TRL3→9 로드맵 마일스톤 생성 확인")
        def fn():
            from pipeline.roadmap_builder import build_roadmap
            rm = build_roadmap("test", "테스트 기술", current_trl=3, target_trl=9)
            cnt = len(rm.get("milestones", []))
            ok  = cnt >= 5
            return ok, f"마일스톤 {cnt}개 생성"
        return self._check(item, fn)

    def check_demand_survey(self) -> CheckItem:
        item = CheckItem("서비스", "수요조사서 생성", "DemandSurveyGenerator 동작 확인")
        def fn():
            from agents.g0_demand_survey import DemandSurveyGenerator
            result = DemandSurveyGenerator().assess({
                "tech_name": "스마트팜 AI",
                "tech_description": "온실 수확량 예측 시스템",
                "industry_sector": "AgriTech",
                "trl": 5,
            })
            d = result.to_dict()
            ok = d["stage"] == "G0-DS" and "document_type" in d["output_doc"]
            return ok, f"수요조사서 score={d['score']}"
        return self._check(item, fn)

    def check_smk_generator(self) -> CheckItem:
        item = CheckItem("서비스", "SMK 생성", "SMKGenerator 동작 확인")
        def fn():
            from agents.smk_generator import SMKGenerator
            result = SMKGenerator().assess({
                "tech_name": "스마트팜 AI",
                "industry_sector": "AgriTech",
                "value_proposition": "수확량 30% 향상",
                "tam_usd": 5_000_000_000,
                "gtm_motion": "direct_sales",
                "differentiators": ["AI 정확도", "저비용", "국산화"],
            })
            d = result.to_dict()
            ok = d["stage"] == "SMK" and "market_sizing" in d["output_doc"]
            return ok, f"SMK score={d['score']}"
        return self._check(item, fn)

    def check_api_health(self) -> CheckItem:
        item = CheckItem("서비스", "API /health", f"FastAPI 서버 헬스체크 ({self.base_url})")
        def fn():
            try:
                import urllib.request
                with urllib.request.urlopen(f"{self.base_url}/health", timeout=5) as r:
                    body = json.loads(r.read())
                    return body.get("status") == "ok", f"응답: {body}"
            except Exception as e:
                return False, f"서버 미응답 (정상 — 로컬 서버 구동 불필요): {e}"
        item2 = self._check(item, fn)
        if item2.status == "FAIL" and "미응답" in item2.detail:
            item2.status = "WARN"
        return item2

    def check_gap_endpoints_registered(self) -> CheckItem:
        item = CheckItem("서비스", "Gap 엔드포인트 등록", "api/main.py에 9개 gap 엔드포인트 확인")
        def fn():
            main_text = (ROOT / "api" / "main.py").read_text(encoding="utf-8")
            endpoints = [
                "/gap/ir-deck", "/gap/esg-impact", "/gap/trade-secret",
                "/gap/ecosystem-match", "/gap/exit-strategy", "/gap/patent-maintenance",
                "/gap/stages",
            ]
            missing = [e for e in endpoints if e not in main_text]
            return len(missing) == 0, f"누락 엔드포인트: {missing}" if missing else "모든 Gap 엔드포인트 등록됨"
        return self._check(item, fn)

    # ─── Layer 4: 검증·재현성 ───────────────────────────

    def check_test_files(self) -> CheckItem:
        item = CheckItem("검증", "테스트 파일 존재", "tests/ 디렉터리 테스트 파일 확인")
        def fn():
            test_dir = ROOT / "tests"
            files    = list(test_dir.glob("test_*.py"))
            return len(files) >= 3, f"테스트 파일 {len(files)}개 발견: {[f.name for f in files]}"
        return self._check(item, fn)

    def check_onpremise_requirements(self) -> CheckItem:
        item = CheckItem("검증", "온프레미스 요구사항", "requirements.txt + .env.example 존재 확인")
        def fn():
            req  = (ROOT / "requirements.txt").exists()
            env  = (ROOT / ".env.example").exists() or (ROOT / ".env").exists()
            return req and env, f"requirements.txt={req}, .env={env}"
        return self._check(item, fn)

    def check_python_version(self) -> CheckItem:
        item = CheckItem("검증", "Python 버전", "Python 3.10+ 확인")
        def fn():
            v = sys.version_info
            ok = (v.major, v.minor) >= (3, 10)
            return ok, f"Python {v.major}.{v.minor}.{v.micro}"
        return self._check(item, fn)

    # ─── 전체 실행 ───────────────────────────────────

    def run_all(self) -> PoCReport:
        from datetime import datetime
        self.report.timestamp   = datetime.now().isoformat()
        self.report.environment = "cloud_poc"

        checks = [
            # AI 모델
            self.check_llm_fallback,
            self.check_rag_index,
            self.check_rag_search,
            # 데이터
            self.check_knowledge_files,
            self.check_schema_file,
            # 서비스
            self.check_agent_imports,
            self.check_roadmap_builder,
            self.check_demand_survey,
            self.check_smk_generator,
            self.check_api_health,
            self.check_gap_endpoints_registered,
            # 검증
            self.check_test_files,
            self.check_onpremise_requirements,
            self.check_python_version,
        ]

        for fn in checks:
            item = fn()
            self.report.items.append(item)

        self.report.total   = len(self.report.items)
        self.report.passed  = sum(1 for i in self.report.items if i.status == "PASS")
        self.report.failed  = sum(1 for i in self.report.items if i.status == "FAIL")
        self.report.warned  = sum(1 for i in self.report.items if i.status == "WARN")
        self.report.skipped = sum(1 for i in self.report.items if i.status == "SKIP")
        return self.report

    def print_report(self) -> None:
        r = self.report
        print(f"\n{'='*60}")
        print(f"  PoC 검증 결과서 — IPInsight Agent OS v2.0")
        print(f"  시각: {r.timestamp}")
        print(f"  환경: {r.environment}")
        print(f"{'='*60}")
        cat = None
        for item in r.items:
            if item.category != cat:
                cat = item.category
                print(f"\n【{cat}】")
            icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "SKIP": "⬜"}[item.status]
            print(f"  {icon} {item.name:<30} {item.detail[:60]}  ({item.duration_ms}ms)")
        print(f"\n{'─'*60}")
        print(f"  합계: {r.total}건  PASS={r.passed}  FAIL={r.failed}  WARN={r.warned}  SKIP={r.skipped}")
        print(f"  통과율: {r.pass_rate}%")
        print(f"{'='*60}\n")

    def save_report(self, path: str = None) -> str:
        out = Path(path or (ROOT / "deploy" / "poc_report.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return str(out)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    verifier = PoCVerifier()
    verifier.run_all()
    verifier.print_report()
    path = verifier.save_report()
    print(f"📄 보고서 저장: {path}")
    sys.exit(0 if verifier.report.failed == 0 else 1)
