"""IPInsight Streamlit MVP — G0~G10 기술사업화 프론트엔드
실행: streamlit run frontend/app.py
"""
from __future__ import annotations
import os, time, json
import requests
import streamlit as st

# ── 설정 ──────────────────────────────────────────────────────
API_URL = os.environ.get("IPINSIGHT_API", "http://localhost:8100")
PAGE_NAMES = {
    "🏠 홈": "home",
    "🔐 로그인": "login",
    "🔬 기술 분석": "analyze",
    "📊 가치평가": "valuation",
    "🗺️ 전체 로드맵": "roadmap",
    "📡 IP 분석": "ip",
    "⚙️ 운영 메트릭": "metrics",
}

st.set_page_config(
    page_title="IPInsight — 글로벌 기술사업화 OS",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 세션 초기화 ────────────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = ""
if "page" not in st.session_state:
    st.session_state.page = "home"
if "last_result" not in st.session_state:
    st.session_state.last_result = None


# ── API 헬퍼 ─────────────────────────────────────────────────
def _headers():
    h = {"Content-Type": "application/json"}
    if st.session_state.token:
        h["Authorization"] = f"Bearer {st.session_state.token}"
    return h


def api_get(path: str) -> dict | None:
    try:
        r = requests.get(f"{API_URL}{path}", headers=_headers(), timeout=15)
        if r.status_code == 200:
            return r.json()
        st.error(f"API 오류 {r.status_code}: {r.text[:200]}")
    except Exception as e:
        st.error(f"서버 연결 실패: {e}")
    return None


def api_post(path: str, body: dict) -> dict | None:
    try:
        r = requests.post(f"{API_URL}{path}", json=body, headers=_headers(), timeout=60)
        if r.status_code == 200:
            return r.json()
        st.error(f"API 오류 {r.status_code}: {r.text[:300]}")
    except Exception as e:
        st.error(f"서버 연결 실패: {e}")
    return None


# ── 사이드바 ──────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=IPInsight", width=200)
    st.markdown("### G0→G10 기술사업화 OS")

    if st.session_state.token:
        st.success("✅ 인증됨")
    else:
        st.warning("🔐 로그인 필요 (개발 모드는 자동 통과)")

    st.divider()
    choice = st.radio("메뉴", list(PAGE_NAMES.keys()), key="nav")
    st.session_state.page = PAGE_NAMES[choice]

    st.divider()
    health = api_get("/health")
    if health:
        st.caption(f"API v{health.get('version', '?')} ✅")
        for k, v in health.get("connectors", {}).items():
            icon = "🟢" if v else "🟡"
            st.caption(f"{icon} {k}")


# ═══════════════════════════════════════════════════════════════
# 페이지: 홈
# ═══════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    st.title("🔬 IPInsight — 글로벌 기술사업화 Agent OS")
    st.markdown("""
**G0~G10 전주기 + IP 4단계 라이프사이클** — WIPO Lab-to-Market 기반
13개 데이터 커넥터(EPO·OpenAlex·World Bank·FDA·ClinicalTrials 등)를 병렬 실행하여
TRL·특허·시장·규제·ESG·가치평가를 단일 파이프라인에서 처리합니다.
""")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("G-Stage", "G0~G10", "11단계")
    with col2:
        st.metric("데이터 커넥터", "13개", "병렬 실행")
    with col3:
        st.metric("AI 에이전트", "31개", "특화 도메인")
    with col4:
        st.metric("API 엔드포인트", "37+", "REST")

    st.divider()
    st.subheader("Stage Gate 맵")
    stages = api_get("/stages")
    if stages:
        cols = st.columns(4)
        for i, (stage_id, info) in enumerate(stages.items()):
            with cols[i % 4]:
                gate_color = {"Go": "🟢", "Hold": "🟡", "Kill": "🔴"}.get(
                    info.get("default_gate", ""), "⚪"
                )
                st.markdown(f"**{stage_id}** {gate_color}  \n{info.get('name','')}")


# ═══════════════════════════════════════════════════════════════
# 페이지: 로그인
# ═══════════════════════════════════════════════════════════════
elif st.session_state.page == "login":
    st.title("🔐 로그인")
    with st.form("login_form"):
        username = st.text_input("아이디", value="admin")
        password = st.text_input("비밀번호", type="password", value="")
        submitted = st.form_submit_button("로그인", type="primary")

    if submitted:
        result = api_post("/auth/token", {"username": username, "password": password})
        if result and "access_token" in result:
            st.session_state.token = result["access_token"]
            st.success("로그인 성공 — 30분 유효")
            time.sleep(1)
            st.rerun()
        else:
            st.error("로그인 실패")

    if st.session_state.token:
        if st.button("로그아웃"):
            st.session_state.token = ""
            st.rerun()

    st.info("개발 모드(`JWT_SECRET_KEY` 미설정)에서는 인증 없이 API 호출 가능")


# ═══════════════════════════════════════════════════════════════
# 페이지: 기술 분석 (단계별 실행)
# ═══════════════════════════════════════════════════════════════
elif st.session_state.page == "analyze":
    st.title("🔬 기술 분석 — G-Stage 실행")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("기술 정보 입력")
        tech_id = st.text_input("기술 ID", value="DEMO-001")
        tech_name = st.text_input("기술명", value="스마트팜 수확량 예측 AI")
        trl = st.slider("현재 TRL", 1, 9, 4)
        ipc = st.text_input("IPC 코드 (쉼표 구분)", value="A01G,G06N")
        sector = st.selectbox("산업 분야", ["AgTech", "BioTech", "ICT", "에너지", "제조", "의료기기", "기타"])
        markets = st.multiselect("목표 시장", ["KR", "US", "EP", "JP", "CN", "SG"], default=["KR", "US"])

    with col_right:
        st.subheader("실행 스테이지")
        stage_n = st.selectbox(
            "단계 선택",
            options=list(range(11)),
            format_func=lambda n: f"G{n} — {['발굴','TRL평가','시장스캔','IP전략','팀역량','비즈니스모델','가치평가','규제인증','기술이전','딜구조','사업화출구'][n]}",
        )

        run_single = st.button("▶ 선택 단계 실행", type="primary")
        run_all    = st.button("⚡ 전체 G0~G10 실행 (비동기)")

    if run_single:
        with st.spinner(f"G{stage_n} 실행 중..."):
            result = api_post(f"/stage/{stage_n}", {
                "tech_id": tech_id,
                "input_data": {
                    "tech_name": tech_name,
                    "trl": trl,
                    "ipc_codes": [c.strip() for c in ipc.split(",")],
                    "industry_sector": sector,
                    "target_markets": markets,
                },
            })
        if result:
            st.session_state.last_result = result
            st.success(f"G{stage_n} 완료")

    if run_all:
        with st.spinner("비동기 Job 제출 중..."):
            job = api_post("/analyze/async", {
                "tech_id": tech_id,
                "input_data": {"tech_name": tech_name, "trl": trl},
            })
        if job:
            job_id = job.get("job_id", "")
            st.info(f"Job `{job_id}` 제출 완료 — 운영 메트릭 페이지에서 상태 확인")

    if st.session_state.last_result:
        st.divider()
        st.subheader("실행 결과")
        res = st.session_state.last_result
        if isinstance(res, dict):
            gate = res.get("gate", "")
            gate_icon = {"Go": "🟢", "Hold": "🟡", "Kill": "🔴"}.get(gate, "⚪")
            score = res.get("score", 0)

            c1, c2, c3 = st.columns(3)
            c1.metric("Gate 판정", f"{gate_icon} {gate}")
            c2.metric("종합 점수", f"{score:.1f}")
            c3.metric("스테이지", res.get("stage", ""))

            if res.get("next_actions"):
                st.subheader("다음 액션")
                for action in res["next_actions"]:
                    st.markdown(f"- {action}")

            if res.get("warnings"):
                st.warning("⚠️ 경고\n" + "\n".join(res["warnings"]))

            with st.expander("전체 JSON 결과 보기"):
                st.json(res)


# ═══════════════════════════════════════════════════════════════
# 페이지: 가치평가
# ═══════════════════════════════════════════════════════════════
elif st.session_state.page == "valuation":
    st.title("📊 기술 가치평가 (DCF · CCA · ROA)")

    col1, col2 = st.columns(2)
    with col1:
        tech_id = st.text_input("기술 ID", value="DEMO-001", key="val_id")
        method  = st.selectbox("평가 방법", ["dcf", "cca", "roa"])
        discount= st.slider("할인율 (%)", 5, 40, 15) / 100
        royalty = st.slider("로열티율 (%)", 1, 20, 5) / 100

    with col2:
        st.subheader("연도별 매출 예측 (USD)")
        years = list(range(2025, 2030))
        revenues = {}
        for y in years:
            revenues[str(y)] = st.number_input(
                f"{y}년", min_value=0, value=int(1e6 * (y - 2024)), step=100_000, key=f"rev_{y}"
            )

    if st.button("▶ 가치평가 실행", type="primary"):
        with st.spinner("가치평가 중..."):
            result = api_post("/valuation/dcf", {
                "tech_id": tech_id,
                "revenue_forecast": revenues,
                "discount_rate": discount,
                "royalty_rate": royalty,
                "method": method,
            })
        if result:
            st.subheader("평가 결과")
            out = result.get("output_doc", result)
            val = out.get("valuation_usd") or out.get("npv_usd") or out.get("value_usd", 0)
            st.metric("추정 기술 가치", f"${val:,.0f}" if val else "산출 불가")
            with st.expander("상세 결과"):
                st.json(result)


# ═══════════════════════════════════════════════════════════════
# 페이지: 전체 로드맵
# ═══════════════════════════════════════════════════════════════
elif st.session_state.page == "roadmap":
    st.title("🗺️ G0→G10 전체 로드맵")

    with st.form("roadmap_form"):
        col1, col2 = st.columns(2)
        with col1:
            tech_id   = st.text_input("기술 ID", "DEMO-001")
            tech_name = st.text_input("기술명", "스마트팜 AI")
            tech_type = st.selectbox("기술 유형", ["general", "biotech", "ICT", "device", "material"])
        with col2:
            region    = st.selectbox("주요 목표 국가", ["KOR", "USA", "EU", "JPN", "CHN", "SGP"])
            trl_cur   = st.slider("현재 TRL", 1, 9, 3)
            trl_tgt   = st.slider("목표 TRL", 1, 9, 9)

        submitted = st.form_submit_button("⚡ 로드맵 생성", type="primary")

    if submitted:
        with st.spinner("G0~G10 로드맵 생성 중... (30~60초 소요)"):
            result = api_post("/roadmap/full", {
                "tech_id": tech_id,
                "tech_name": tech_name,
                "tech_type": tech_type,
                "region": region,
                "trl_current": trl_cur,
                "trl_target": trl_tgt,
            })
        if result:
            stages = result.get("stages", {})
            if stages:
                import plotly.graph_objects as go

                x = list(stages.keys())
                y = [v.get("score", 0) for v in stages.values()]
                colors = [
                    "#22c55e" if v.get("gate") == "Go" else
                    "#eab308" if v.get("gate") == "Hold" else
                    "#ef4444" for v in stages.values()
                ]
                fig = go.Figure(go.Bar(
                    x=x, y=y, marker_color=colors, text=[f"{s:.1f}" for s in y], textposition="auto"
                ))
                fig.update_layout(title="G-Stage Gate 결과", xaxis_title="스테이지", yaxis_title="점수", height=350)
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("단계별 결과")
                for sid, sdata in stages.items():
                    gate  = sdata.get("gate", "")
                    score = sdata.get("score", 0)
                    icon  = "🟢" if gate == "Go" else "🟡" if gate == "Hold" else "🔴"
                    with st.expander(f"{icon} {sid} — {gate} ({score:.1f}점)"):
                        st.json(sdata)
            else:
                st.json(result)


# ═══════════════════════════════════════════════════════════════
# 페이지: IP 분석
# ═══════════════════════════════════════════════════════════════
elif st.session_state.page == "ip":
    st.title("📡 IP 전주기 분석")

    tab1, tab2 = st.tabs(["특허 FTO 분석", "경쟁사 모니터링"])

    with tab1:
        tech_id  = st.text_input("기술 ID", "DEMO-001", key="ip_id")
        tech_name = st.text_input("기술명", "스마트팜 AI", key="ip_name")
        ipc = st.text_input("IPC/CPC 코드", "A01G,G06N")
        trl = st.slider("TRL", 1, 9, 4, key="ip_trl")

        if st.button("▶ IP 전주기 분석 실행", type="primary"):
            with st.spinner("분석 중..."):
                result = api_post("/ip/full-lifecycle", {
                    "tech_id": tech_id,
                    "tech_name": tech_name,
                    "ipc_codes": [c.strip() for c in ipc.split(",")],
                    "cpc_codes": [c.strip() for c in ipc.split(",")],
                    "trl": trl,
                })
            if result:
                st.success("분석 완료")
                with st.expander("결과 보기"):
                    st.json(result)

    with tab2:
        comp_id = st.text_input("기술 ID", "DEMO-001", key="comp_id")
        if st.button("▶ 경쟁사 동향 조회"):
            with st.spinner("조회 중..."):
                result = api_get(f"/result/{comp_id}")
            if result:
                st.json(result)


# ═══════════════════════════════════════════════════════════════
# 페이지: 운영 메트릭
# ═══════════════════════════════════════════════════════════════
elif st.session_state.page == "metrics":
    st.title("⚙️ 운영 메트릭 · Job 모니터")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("API 메트릭")
        if st.button("🔄 새로고침"):
            pass  # rerun triggered by state change
        m = api_get("/metrics")
        if m:
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("총 요청", m.get("requests", 0))
            cc2.metric("오류율", f"{m.get('error_rate', 0):.1f}%")
            cc3.metric("평균 응답", f"{m.get('avg_ms', 0):.0f}ms")

            st.subheader("최근 요청 10건")
            recent = m.get("recent_10", [])
            if recent:
                import pandas as pd
                df = pd.DataFrame(recent)
                st.dataframe(df, use_container_width=True)
        else:
            st.info("메트릭 조회 실패 (인증 필요할 수 있음)")

    with col2:
        st.subheader("Job 상태 조회")
        job_id = st.text_input("Job ID", placeholder="8자리 UUID")
        if st.button("📋 Job 조회") and job_id:
            job = api_get(f"/jobs/{job_id}")
            if job:
                status = job.get("status", "")
                icon = {"queued": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(status, "❓")
                st.metric("상태", f"{icon} {status}")
                if job.get("result"):
                    with st.expander("결과 보기"):
                        st.json(job["result"])
                if job.get("error"):
                    st.error(f"오류: {job['error']}")
