"""IPInsight — 글로벌 기술사업화 Agent OS (UX v2.1)
실행: streamlit run frontend/app.py
"""
from __future__ import annotations
import os, time, json, re
import requests
import streamlit as st

# ── 설정 ─────────────────────────────────────────────────────────
API_URL = os.environ.get("IPINSIGHT_API", "http://localhost:8001")

STAGE_META = {
    0:  ("G0",  "기술발굴",   "🔭"),
    1:  ("G1",  "IP 구조화",  "📋"),
    2:  ("G2",  "TRL 평가",   "🧪"),
    3:  ("G3",  "시장성",     "🌐"),
    4:  ("G4",  "고객검증",   "🤝"),
    5:  ("G5",  "BM 설계",    "💼"),
    6:  ("G6",  "가치평가",   "💰"),
    7:  ("G7",  "PoC 실증",   "🔬"),
    8:  ("G8",  "MRL/ARL",   "📊"),
    9:  ("G9",  "거래·투자",  "🤝"),
    10: ("G10", "성과관리",   "📈"),
}

GATE_NEXT = {
    "Go":   {"color": "success", "icon": "🟢", "label": "Go — 다음 단계 진행"},
    "Hold": {"color": "warning", "icon": "🟡", "label": "Hold — 조건 충족 후 재평가"},
    "Kill": {"color": "error",   "icon": "🔴", "label": "Kill — 피벗 또는 중단 검토"},
}

st.set_page_config(
    page_title="IPInsight — 기술사업화 OS",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS 커스텀 ────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── 전역 레이아웃 ── */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── 랜딩 레이아웃 ── */
.landing-wrap {
  display: flex; height: 100vh; overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* 좌측 패널 */
.left-panel {
  width: 260px; min-width: 260px; background: #171717;
  border-right: 1px solid #2a2a2a; display: flex;
  flex-direction: column; padding: 0; overflow: hidden;
}
.lp-header {
  padding: 18px 16px 10px;
  display: flex; align-items: center; gap: 10px;
}
.lp-logo { font-size: 20px; }
.lp-brand { font-size: 15px; font-weight: 700; color: #f0f0f0; }
.lp-sub { font-size: 10px; color: #666; margin-top: 1px; }
.lp-new-btn {
  margin: 8px 12px 4px;
  background: #2563eb; color: #fff; border: none;
  border-radius: 8px; padding: 9px 14px; font-size: 13px;
  font-weight: 600; cursor: pointer; display: flex; align-items: center;
  gap: 6px; width: calc(100% - 24px);
  transition: background .15s;
}
.lp-new-btn:hover { background: #1d4ed8; }
.lp-section-title {
  font-size: 10px; font-weight: 700; color: #555;
  text-transform: uppercase; letter-spacing: .08em;
  padding: 14px 16px 4px;
}
.lp-item {
  padding: 8px 16px; font-size: 12px; color: #aaa; cursor: pointer;
  border-radius: 6px; margin: 1px 8px; display: flex;
  align-items: center; gap: 8px; transition: background .1s;
}
.lp-item:hover { background: #242424; color: #e0e0e0; }
.lp-item-icon { font-size: 13px; opacity: .7; }
.lp-item-label { flex:1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.lp-item-badge {
  background: #2a2a2a; color: #666; font-size: 9px;
  padding: 2px 6px; border-radius: 4px;
}
.lp-divider { border:none; border-top: 1px solid #2a2a2a; margin: 8px 0; }
.lp-bottom {
  padding: 12px; margin-top: auto;
  border-top: 1px solid #2a2a2a;
}
.lp-api-status {
  font-size: 10px; color: #555; display: flex; align-items: center; gap: 6px;
}

/* 우측 메인 */
.right-panel {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background: #1a1a1a; overflow-y: auto; padding: 40px 20px;
}
.greeting-area { text-align: center; max-width: 700px; width: 100%; }
.greeting-title {
  font-size: 32px; font-weight: 700; color: #f0f0f0;
  margin-bottom: 6px; line-height: 1.3;
}
.greeting-sub {
  font-size: 14px; color: #777; margin-bottom: 36px;
}
/* 입력 박스 */
.input-box-wrap {
  background: #242424; border: 1px solid #333; border-radius: 14px;
  padding: 16px 20px 10px; max-width: 700px; width: 100%;
  margin: 0 auto 20px;
}
.input-box-wrap:focus-within {
  border-color: #2563eb; box-shadow: 0 0 0 2px #2563eb22;
}
/* 파일 드롭 힌트 */
.drop-hint {
  font-size: 11px; color: #555; text-align: center;
  margin: 6px 0 4px; display: flex; align-items: center;
  justify-content: center; gap: 4px;
}
/* 예시 칩 */
.chips-row {
  display: flex; flex-wrap: wrap; gap: 8px;
  justify-content: center; max-width: 700px;
  margin: 0 auto 32px;
}
.chip {
  background: #242424; border: 1px solid #333; border-radius: 20px;
  padding: 6px 14px; font-size: 12px; color: #aaa; cursor: pointer;
  transition: all .15s; display: flex; align-items: center; gap: 5px;
}
.chip:hover { background: #2a2a2a; border-color: #2563eb; color: #60a5fa; }
/* 입력 타입 탭 */
.type-tabs {
  display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap;
}
.type-tab {
  background: #1e1e1e; border: 1px solid #333; border-radius: 6px;
  padding: 5px 12px; font-size: 11px; color: #888; cursor: pointer;
  transition: all .15s;
}
.type-tab.active, .type-tab:hover {
  background: #1e3a5f; border-color: #2563eb; color: #60a5fa;
}
/* 최근 기술 카드 */
.recent-cards {
  display: flex; gap: 12px; flex-wrap: wrap;
  justify-content: center; max-width: 700px; margin: 0 auto;
}
.r-card {
  background: #242424; border: 1px solid #333; border-radius: 10px;
  padding: 14px 16px; width: 180px; cursor: pointer; transition: all .15s;
}
.r-card:hover { border-color: #2563eb; background: #1e2a3a; }
.r-card-icon { font-size: 20px; margin-bottom: 6px; }
.r-card-title { font-size: 12px; font-weight: 600; color: #d0d0d0; margin-bottom: 3px; }
.r-card-sub { font-size: 10px; color: #666; }

/* ── 이후 페이지용 (inner-app) ── */
.inner-app [data-testid="stSidebar"] { display: flex !important; }

/* G-Stage 진행 표시줄 */
.stage-bar { display:flex; gap:4px; padding:10px 0 14px; overflow-x:auto; }
.stage-node { display:flex; flex-direction:column; align-items:center;
              min-width:62px; cursor:pointer; }
.stage-circle { width:34px; height:34px; border-radius:50%; display:flex;
                align-items:center; justify-content:center; font-size:12px;
                font-weight:700; border:2px solid; transition:.15s; }
.stage-done   .stage-circle { background:#16a34a22; border-color:#4ade80; color:#4ade80; }
.stage-active .stage-circle { background:#2563eb33; border-color:#60a5fa; color:#60a5fa; }
.stage-locked .stage-circle { background:#1e293b; border-color:#334155; color:#64748b; }
.stage-kill   .stage-circle { background:#7f1d1d22; border-color:#f87171; color:#f87171; }
.stage-label  { font-size:9px; margin-top:3px; text-align:center;
                color:#94a3b8; max-width:60px; line-height:1.2; }
.stage-connector { flex:1; height:2px; background:#334155;
                   margin-top:17px; min-width:8px; }
/* Gate 행동 카드 */
.gate-card { border-radius:8px; padding:14px 16px; margin:12px 0; }
.gate-go   { background:#16a34a18; border:1px solid #16a34a50; }
.gate-hold { background:#ca8a0418; border:1px solid #ca8a0450; }
.gate-kill { background:#dc262618; border:1px solid #dc262650; }
/* 컨텍스트 배너 */
.ctx-banner { background:#1e293b; border:1px solid #334155; border-radius:8px;
              padding:8px 14px; margin-bottom:12px; display:flex;
              align-items:center; gap:10px; font-size:12px; }
/* BM 캔버스 그리드 */
.bm-block { background:#1e293b; border:1px solid #334155; border-radius:7px;
            padding:10px 12px; min-height:80px; }
.bm-title { font-size:10px; font-weight:700; color:#94a3b8;
            text-transform:uppercase; margin-bottom:6px; letter-spacing:.04em; }
</style>
""", unsafe_allow_html=True)


# ── 세션 초기화 ──────────────────────────────────────────────────
_DEFAULTS = {
    "token": "", "page": "home",
    "tech_id": "", "tech_name": "",
    "trl": 4, "ipc": "", "sector": "",
    "stage_gates": {},
    "last_result": None, "last_stage": None,
    "g4_data": {}, "g5_data": {},
    "recent_techs": [           # 최근 분석 기술 목록
        {"id": "DEMO-001", "name": "스마트팜 수확량 예측 AI",  "trl": 4, "icon": "🌱"},
        {"id": "DEMO-002", "name": "차세대 리튬-황 배터리",     "trl": 6, "icon": "⚡"},
        {"id": "DEMO-003", "name": "AI 기반 암 진단 플랫폼",   "trl": 5, "icon": "🔬"},
    ],
    "input_mode": "text",       # text | patent_no | paper | bizplan | file
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── API 헬퍼 ─────────────────────────────────────────────────────
def _headers():
    h = {"Content-Type": "application/json"}
    if st.session_state.token:
        h["Authorization"] = f"Bearer {st.session_state.token}"
    return h

def api_get(path: str, silent: bool = False) -> dict | None:
    try:
        r = requests.get(f"{API_URL}{path}", headers=_headers(), timeout=15)
        if r.status_code == 200:
            return r.json()
        if not silent:
            st.error(f"API {r.status_code}: {r.text[:200]}")
    except Exception as e:
        if not silent:
            st.error(f"서버 연결 실패: {e}")
    return None

def api_post(path: str, body: dict, silent: bool = False) -> dict | None:
    try:
        r = requests.post(f"{API_URL}{path}", json=body, headers=_headers(), timeout=90)
        if r.status_code == 200:
            return r.json()
        if not silent:
            st.error(f"API {r.status_code}: {r.text[:300]}")
    except Exception as e:
        if not silent:
            st.error(f"서버 연결 실패: {e}")
    return None


# ── 공통 컴포넌트 ─────────────────────────────────────────────────

def render_stage_bar(current: int | None = None):
    """G0~G10 진행 표시줄 — 전 화면 공통 렌더링"""
    gates = st.session_state.stage_gates
    html = '<div class="stage-bar">'
    for n, (gid, name, icon) in STAGE_META.items():
        info = gates.get(n, {})
        gate = info.get("gate", "")
        if gate == "Kill":
            cls = "stage-kill"
        elif gate in ("Go", "Hold"):
            cls = "stage-done"
        elif n == current:
            cls = "stage-active"
        else:
            cls = "stage-locked"
        score_txt = f"({info['score']:.0f})" if info.get("score") else ""
        html += f'''
        <div class="stage-node {cls}">
          <div class="stage-circle">{icon}</div>
          <div class="stage-label">{gid}<br>{name}<br><span style="color:#60a5fa;font-size:8px">{score_txt}</span></div>
        </div>'''
        if n < 10:
            html += '<div class="stage-connector"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_context_banner():
    """현재 기술 컨텍스트 배너 — 1회 입력 원칙"""
    tid = st.session_state.tech_id
    tname = st.session_state.tech_name
    trl = st.session_state.trl
    completed = sum(1 for g in st.session_state.stage_gates.values() if g.get("gate") == "Go")
    st.markdown(
        f'<div class="ctx-banner">🔬 <strong>{tname}</strong>'
        f'&nbsp;·&nbsp;<code>{tid}</code>'
        f'&nbsp;·&nbsp;TRL {trl}'
        f'&nbsp;·&nbsp;완료 단계 {completed}/11</div>',
        unsafe_allow_html=True,
    )


def render_gate_card(gate: str, score: float, stage_label: str, next_actions: list[str]):
    """Gate 판정 → 다음 행동 카드"""
    meta = GATE_NEXT.get(gate, GATE_NEXT["Hold"])
    css  = {"Go": "gate-go", "Hold": "gate-hold", "Kill": "gate-kill"}.get(gate, "gate-hold")
    actions_html = "".join(f"<li>{a}</li>" for a in next_actions[:3])
    st.markdown(f"""
    <div class="gate-card {css}">
      <div style="font-size:15px;font-weight:700;margin-bottom:6px;">
        {meta['icon']} {stage_label} — {meta['label']} &nbsp;
        <span style="font-size:12px;font-weight:400;opacity:.7">점수 {score:.1f}</span>
      </div>
      <ul style="margin:0;padding-left:18px;font-size:12px;opacity:.85">{actions_html}</ul>
    </div>
    """, unsafe_allow_html=True)


def _save_gate(stage_num: int, result: dict):
    """Gate 결과를 세션에 저장"""
    gate  = result.get("gate", "")
    score = float(result.get("score", 0))
    st.session_state.stage_gates[stage_num] = {"gate": gate, "score": score}
    st.session_state.last_result = result
    st.session_state.last_stage  = stage_num


# ── 홈 화면 이외에서는 상단 네비 바 렌더링 ───────────────────────
def render_topnav():
    """홈 이외 페이지에서 상단 고정 네비게이션"""
    health = api_get("/health", silent=True)
    api_ok = health is not None
    tid  = st.session_state.tech_id  or "–"
    name = st.session_state.tech_name or "기술 미선택"
    cols = st.columns([1, 4, 1])
    with cols[0]:
        if st.button("⬅ 홈", key="nav_home"):
            st.session_state.page = "home"; st.rerun()
    with cols[1]:
        st.markdown(
            f"<div style='font-size:12px;color:#94a3b8;padding:6px 0'>"
            f"🔬 <b style='color:#e2e8f0'>{name}</b>"
            f" &nbsp;·&nbsp; <code>{tid}</code>"
            f" &nbsp;·&nbsp; TRL {st.session_state.trl}</div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        st.caption(f"{'✅ API' if api_ok else '🔴 API 오프라인'}")
    st.divider()

def render_sidenav():
    """홈 이외 페이지 왼쪽 네비게이션 (st.sidebar 대신 컬럼 사용)"""
    nav_items = [
        ("🏠", "워크스페이스",    "workspace"),
        ("📡", "IP 분석 허브",    "ip_hub"),
        ("🗺️", "전체 로드맵",     "roadmap"),
        None,
        ("🤝", "G4 인터뷰 보드", "interviews"),
        ("💼", "G5 BM 캔버스",   "bm"),
        ("💰", "G6 가치평가",    "valuation"),
        None,
        ("📈", "G10 KPI",        "kpi"),
        ("📄", "보고서 센터",     "reports"),
        ("⚙️", "관리자 콘솔",     "admin"),
    ]
    st.markdown("**IPInsight**")
    st.caption("기술사업화 OS")
    st.divider()
    for item in nav_items:
        if item is None:
            st.markdown("<hr style='margin:6px 0;border-color:#334155'>", unsafe_allow_html=True)
            continue
        icon, label, pg = item
        active = st.session_state.page == pg
        style = "primary" if active else "secondary"
        if st.button(f"{icon} {label}", use_container_width=True, key=f"nav_{pg}", type=style):
            st.session_state.page = pg; st.rerun()


# ── 홈 흐름 세션 초기화 ──────────────────────────────────────────
for _k, _v in {
    "home_step":       1,          # 1=입력  2=단계추천  3=추가입력+실행
    "home_text":       "",
    "home_filename":   "",
    "home_trl":        4,
    "home_rec_stages": [],         # 추천 단계 목록 [{stage, reason, priority}]
    "home_sel_stage":  None,       # 사용자가 선택한 단계 번호
    "home_extra":      "",         # 추가 보완 자료 텍스트
    "home_result":     None,       # 분석 결과
    "home_stopped":    False,      # 중간 중단 여부
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

def _home_reset():
    for k in ["home_step","home_text","home_filename","home_trl",
              "home_rec_stages","home_sel_stage","home_extra","home_result","home_stopped"]:
        del st.session_state[k]
    st.rerun()

def _recommend_stages(text: str, trl: int, filename: str) -> list[dict]:
    """입력 텍스트/파일 기반 추천 단계 생성 (API 또는 규칙 기반)"""
    # 키워드 기반 우선순위 규칙
    text_lower = (text + filename).lower()
    stages = []
    if any(w in text_lower for w in ["청구항","claim","ipc","특허","patent","명세"]):
        stages += [
            {"stage":1,"label":"G1 IP 구조화","icon":"📋","reason":"특허 텍스트 감지 — PCML 청구항 구조 분석","priority":"🔴 필수"},
            {"stage":2,"label":"G2 TRL 평가","icon":"🧪","reason":"기술 성숙도 기준선 확인","priority":"🟠 권장"},
            {"stage":3,"label":"G3 시장성 분석","icon":"🌐","reason":"특허 기반 시장 규모 추정","priority":"🟡 선택"},
        ]
    elif any(w in text_lower for w in ["abstract","doi","arxiv","journal","학술","논문","paper"]):
        stages += [
            {"stage":2,"label":"G2 TRL 평가","icon":"🧪","reason":"논문 기반 TRL 현황 평가","priority":"🔴 필수"},
            {"stage":1,"label":"G1 IP 구조화","icon":"📋","reason":"논문 기술의 특허 가능성 검토","priority":"🟠 권장"},
            {"stage":3,"label":"G3 시장성 분석","icon":"🌐","reason":"연구 주제의 산업화 가능성","priority":"🟡 선택"},
        ]
    elif any(w in text_lower for w in ["시장","market","tam","sam","som","보고서","report"]):
        stages += [
            {"stage":3,"label":"G3 시장성 분석","icon":"🌐","reason":"시장보고서 기반 TAM/SAM 분석","priority":"🔴 필수"},
            {"stage":5,"label":"G5 BM 설계","icon":"💼","reason":"시장 분석 → 비즈니스 모델 도출","priority":"🟠 권장"},
            {"stage":6,"label":"G6 가치평가","icon":"💰","reason":"시장 규모 기반 기술가치 산정","priority":"🟡 선택"},
        ]
    elif any(w in text_lower for w in ["사업","biz","계획","revenue","수익","고객","customer"]):
        stages += [
            {"stage":5,"label":"G5 BM 설계","icon":"💼","reason":"사업계획서 기반 BM 검증","priority":"🔴 필수"},
            {"stage":4,"label":"G4 고객검증","icon":"🤝","reason":"JTBD 고객 인터뷰 설계","priority":"🟠 권장"},
            {"stage":6,"label":"G6 가치평가","icon":"💰","reason":"사업계획 기반 투자가치 산정","priority":"🟡 선택"},
        ]
    else:
        stages += [
            {"stage":0,"label":"G0 기술발굴","icon":"🔭","reason":"기술 기본 정보 등록 및 분류","priority":"🔴 필수"},
            {"stage":1,"label":"G1 IP 구조화","icon":"📋","reason":"IP 포트폴리오 전략 수립","priority":"🟠 권장"},
            {"stage":2,"label":"G2 TRL 평가","icon":"🧪","reason":"TRL 기준 사업화 준비도 평가","priority":"🟡 선택"},
        ]

    # TRL 기반 추가 추천
    if trl >= 7:
        stages.insert(0, {"stage":7,"label":"G7 PoC 실증","icon":"🔬",
                          "reason":f"TRL {trl} — PoC 단계 진입 가능","priority":"🔴 필수"})
    elif trl >= 5:
        stages.insert(0, {"stage":4,"label":"G4 고객검증","icon":"🤝",
                          "reason":f"TRL {trl} — 고객검증 적기","priority":"🔴 필수"})
    return stages[:5]

# ════════════════════════════════════════════════════════════════
# HOME — Claude 스타일 랜딩 화면 (3단계 위저드)
# ════════════════════════════════════════════════════════════════
if st.session_state.page == "home":

    health = api_get("/health", silent=True)
    api_ok = health is not None

    left_col, right_col = st.columns([1, 3], gap="small")

    # ──────────── 좌측 패널 ────────────
    with left_col:
        # 브랜드
        st.markdown(
            "<div style='padding:8px 0 6px;'>"
            "<span style='font-size:22px'>🔬</span> "
            "<span style='font-size:16px;font-weight:700'>IPInsight</span><br>"
            "<span style='font-size:10px;color:#888'>글로벌 기술사업화 Agent OS</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # 새 분석 버튼
        if st.button("✏️  새 기술 분석", use_container_width=True, type="primary", key="home_new"):
            st.session_state.tech_id   = ""
            st.session_state.tech_name = ""
            st.session_state.trl       = 4
            st.session_state.stage_gates = {}
            st.session_state.page      = "home"
            st.rerun()

        st.markdown(
            "<p style='font-size:10px;font-weight:700;color:#555;"
            "text-transform:uppercase;letter-spacing:.08em;"
            "padding:14px 4px 4px;margin:0'>프로젝트</p>",
            unsafe_allow_html=True,
        )

        # 프로젝트 유형 메뉴
        project_items = [
            ("📋", "특허 포트폴리오"),
            ("🏭", "기술 이전 프로젝트"),
            ("🚀", "스타트업 사업화"),
            ("🔬", "R&D 상용화"),
        ]
        for icon, label in project_items:
            st.markdown(
                f"<div style='padding:7px 6px;font-size:12px;color:#888;"
                f"display:flex;align-items:center;gap:8px;cursor:pointer;"
                f"border-radius:6px;margin:1px 0'>"
                f"<span>{icon}</span><span>{label}</span></div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<p style='font-size:10px;font-weight:700;color:#555;"
            "text-transform:uppercase;letter-spacing:.08em;"
            "padding:14px 4px 4px;margin:0'>최근 분석</p>",
            unsafe_allow_html=True,
        )

        # 최근 기술 목록
        for tech in st.session_state.recent_techs:
            btn_label = f"{tech['icon']} {tech['name'][:14]}{'…' if len(tech['name'])>14 else ''}"
            if st.button(btn_label, use_container_width=True, key=f"recent_{tech['id']}"):
                st.session_state.tech_id   = tech["id"]
                st.session_state.tech_name = tech["name"]
                st.session_state.trl       = tech["trl"]
                st.session_state.page      = "workspace"
                st.rerun()

        # 하단 상태
        st.markdown("<hr style='border-color:#2a2a2a;margin:20px 0 8px'>", unsafe_allow_html=True)
        status_bg = "#14532d" if api_ok else "#7f1d1d"
        status_txt = "🟢 API 연결" if api_ok else "🔴 API 오프라인"
        st.markdown(
            f"<div style='background:{status_bg};border-radius:6px;padding:6px 10px;"
            f"font-size:11px;color:#e2e8f0;text-align:center;margin-top:4px'>{status_txt}</div>",
            unsafe_allow_html=True,
        )
        if st.session_state.token:
            if st.button("로그아웃", use_container_width=True, key="logout_home"):
                st.session_state.token = ""; st.rerun()
        else:
            if st.button("🔐 로그인", use_container_width=True, key="login_home"):
                st.session_state.page = "admin"; st.rerun()

    # ──────────── 우측 패널 (3단계 위저드) ────────────
    with right_col:
        step = st.session_state.home_step

        # ── 스텝 진행 표시 ──────────────────────────────────────────
        STEPS = [("① 자료 입력", "특허·논문·사업계획서"), ("② 단계 추천", "최적 경로 선택"), ("③ 실행·리포팅", "분석 후 보고서")]
        prog_html = (
            "<div style='display:flex;align-items:stretch;gap:0;margin-bottom:32px;margin-top:20px;"
            "border-radius:12px;overflow:hidden;border:1px solid #333'>"
        )
        for i, (s_label, s_sub) in enumerate(STEPS, 1):
            active = (i == step)
            done   = (i < step)
            bg     = "linear-gradient(135deg,#1d4ed8,#2563eb)" if active else ("linear-gradient(135deg,#14532d,#16a34a)" if done else "#1a1a1a")
            opacity = "1" if (active or done) else "0.5"
            icon   = "✓" if done else str(i)
            prog_html += (
                f"<div style='flex:1;padding:14px 16px;text-align:center;"
                f"background:{bg};opacity:{opacity};position:relative'>"
                f"<div style='font-size:18px;font-weight:800;color:#fff'>{icon}</div>"
                f"<div style='font-size:13px;font-weight:700;color:#fff;margin-top:2px'>{s_label}</div>"
                f"<div style='font-size:10px;color:rgba(255,255,255,.65);margin-top:2px'>{s_sub}</div>"
                f"</div>"
            )
            if i < 3:
                prog_html += "<div style='width:1px;background:#333'></div>"
        prog_html += "</div>"
        st.markdown(prog_html, unsafe_allow_html=True)

        # ════════════════════════════════
        # STEP 1 — 자료 입력
        # ════════════════════════════════
        if step == 1:
            st.markdown(
                "<div style='text-align:center;margin-bottom:24px'>"
                "<div style='font-size:30px;font-weight:700;line-height:1.3'>"
                "기술의 가치를 발견하세요</div>"
                "<div style='font-size:13px;color:#888;margin-top:6px'>"
                "텍스트 또는 파일을 입력하면 최적의 사업화 경로를 추천해 드립니다</div>"
                "</div>",
                unsafe_allow_html=True,
            )

            # 입력 탭: 텍스트 / 파일
            tab_text, tab_file = st.tabs(["✏️ 텍스트 입력", "📎 파일 업로드"])

            with tab_text:
                text_val = st.text_area(
                    "내용",
                    placeholder=(
                        "아래 중 무엇이든 자유롭게 붙여넣으세요:\n\n"
                        "• 특허 청구항 또는 명세서\n"
                        "• 논문 제목 + 초록 (Abstract)\n"
                        "• 기술 개요 또는 기술명\n"
                        "• 사업계획서 요약\n"
                        "• 시장보고서 핵심 내용\n\n"
                        "예시:\n"
                        "청구항 1: 딥러닝 기반 작물 수확량 예측 방법으로서, IoT 센서로부터 수집된..."
                    ),
                    height=200,
                    label_visibility="collapsed",
                    key="step1_text",
                )

            with tab_file:
                st.markdown(
                    "<div style='font-size:12px;color:#888;margin-bottom:8px'>"
                    "특허명세서 · 논문 · 사업계획서 · 시장보고서 등</div>",
                    unsafe_allow_html=True,
                )
                uploaded = st.file_uploader(
                    "파일",
                    type=["pdf","txt","docx","hwp","xlsx","pptx","png","jpg"],
                    label_visibility="collapsed",
                    key="step1_file",
                    help="PDF, DOCX, HWP, XLSX, PPTX, TXT, 이미지 지원",
                )
                if uploaded:
                    st.success(f"✅ {uploaded.name} ({uploaded.size//1024}KB) 업로드됨")
                    st.caption("파일 내용은 분석 시 자동 추출됩니다.")

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # 기술명 + TRL
            c1, c2 = st.columns([2, 1])
            tech_name_in = c1.text_input(
                "기술명 (선택 · 자동 추출 가능)",
                placeholder="예: 스마트팜 수확량 예측 AI",
                key="step1_name",
            )
            trl_in = c2.select_slider(
                "현재 TRL",
                options=list(range(1, 10)),
                value=st.session_state.home_trl,
                format_func=lambda x: f"TRL {x}",
                key="step1_trl",
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("다음 — 추천 단계 확인 →", type="primary",
                         use_container_width=True, key="step1_next"):
                text_in   = st.session_state.get("step1_text", "")
                file_name = uploaded.name if (uploaded := st.session_state.get("step1_file")) else ""
                if not text_in.strip() and not file_name:
                    st.warning("텍스트를 입력하거나 파일을 업로드해 주세요.")
                else:
                    st.session_state.home_text     = text_in.strip()
                    st.session_state.home_filename = file_name
                    st.session_state.home_trl      = trl_in
                    st.session_state.tech_name     = tech_name_in.strip() or text_in[:30].replace("\n"," ") or file_name or "분석 기술"
                    st.session_state.home_rec_stages = _recommend_stages(text_in, trl_in, file_name)
                    st.session_state.home_step     = 2
                    st.rerun()

            # 빠른 예시 칩
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:11px;color:#555;text-align:center;margin-bottom:8px'>빠른 예시로 시작</div>",
                        unsafe_allow_html=True)
            EXAMPLES = [
                ("🌱", "스마트팜 수확량 예측 AI", "청구항 1: 딥러닝 기반 작물 수확량 예측 방법으로서, IoT 센서 데이터와 기상 정보를 결합하여...", 4),
                ("⚡", "차세대 리튬-황 배터리",   "본 발명은 황화리튬 복합 양극재를 이용한 고에너지밀도 배터리 셀에 관한 것으로...", 5),
                ("🧬", "mRNA 백신 전달체",       "Abstract: A novel lipid nanoparticle formulation for efficient mRNA delivery...", 6),
                ("🤖", "협동로봇 안전 제어",      "시장보고서 요약: 글로벌 협동로봇 시장은 2027년 95억 달러 규모로 성장 예상...", 3),
            ]
            ex_cols = st.columns(4)
            for i, (icon, ex_name, ex_text, ex_trl) in enumerate(EXAMPLES):
                with ex_cols[i]:
                    if st.button(f"{icon}\n{ex_name}", use_container_width=True, key=f"ex_{i}"):
                        import time as _t
                        st.session_state.home_text      = ex_text
                        st.session_state.home_trl       = ex_trl
                        st.session_state.tech_name      = ex_name
                        st.session_state.tech_id        = f"DEMO-{i+10}"
                        st.session_state.home_rec_stages = _recommend_stages(ex_text, ex_trl, "")
                        st.session_state.home_step      = 2
                        new_r = {"id": f"DEMO-{i+10}", "name": ex_name, "trl": ex_trl, "icon": icon}
                        st.session_state.recent_techs   = [new_r] + [r for r in st.session_state.recent_techs if r["id"] != f"DEMO-{i+10}"][:4]
                        st.rerun()

        # ════════════════════════════════
        # STEP 2 — 단계 추천 & 선택
        # ════════════════════════════════
        elif step == 2:
            name = st.session_state.tech_name or "입력 기술"
            trl  = st.session_state.home_trl
            recs = st.session_state.home_rec_stages

            st.markdown(
                f"<div style='margin-bottom:20px'>"
                f"<div style='font-size:22px;font-weight:700'>📊 분석 단계 추천</div>"
                f"<div style='font-size:13px;color:#888;margin-top:4px'>"
                f"<b style='color:#e2e8f0'>{name}</b> · TRL {trl} — 입력 자료를 분석한 결과입니다</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # 입력 자료 미리보기
            preview = st.session_state.home_text[:120] or st.session_state.home_filename or ""
            if preview:
                st.markdown(
                    f"<div style='background:#2a2a2a;border:1px solid #333;border-radius:8px;"
                    f"padding:10px 14px;font-size:11px;color:#888;margin-bottom:16px'>"
                    f"📄 입력 자료 미리보기: {preview}{'…' if len(preview)>=120 else ''}</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("**추천 분석 경로** — 클릭하여 선택하세요")

            # 추천 단계 카드
            sel = st.session_state.home_sel_stage
            for rec in recs:
                is_sel = (sel == rec["stage"])
                border = "#2563eb" if is_sel else "#333"
                bg     = "#1e2a3a" if is_sel else "#242424"
                badge_col = {"🔴 필수":"#7f1d1d","🟠 권장":"#7c3a00","🟡 선택":"#713f12"}.get(rec["priority"],"#1e293b")
                st.markdown(
                    f"<div style='background:{bg};border:1.5px solid {border};"
                    f"border-radius:10px;padding:14px 16px;margin-bottom:8px;"
                    f"cursor:pointer;transition:all .15s'>"
                    f"<div style='display:flex;align-items:center;gap:10px'>"
                    f"<span style='font-size:22px'>{rec['icon']}</span>"
                    f"<div style='flex:1'>"
                    f"<div style='font-size:14px;font-weight:700'>{rec['label']}"
                    f"{'  ✓' if is_sel else ''}</div>"
                    f"<div style='font-size:11px;color:#888;margin-top:2px'>{rec['reason']}</div>"
                    f"</div>"
                    f"<span style='background:{badge_col};color:#e2e8f0;font-size:10px;"
                    f"padding:3px 8px;border-radius:4px;font-weight:600'>{rec['priority']}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"이 단계 선택", key=f"sel_{rec['stage']}",
                             type="primary" if is_sel else "secondary",
                             use_container_width=False):
                    st.session_state.home_sel_stage = rec["stage"]
                    st.rerun()

            # 직접 선택
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            all_stages = [f"G{n} {STAGE_META[n][1]}" for n in range(11)]
            custom = st.selectbox("또는 원하는 단계 직접 선택", ["— 추천 중에서 선택 —"] + all_stages,
                                  key="step2_custom")
            if custom != "— 추천 중에서 선택 —":
                st.session_state.home_sel_stage = int(custom[1])

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            c_back, c_next = st.columns(2)
            if c_back.button("← 뒤로", use_container_width=True, key="step2_back"):
                st.session_state.home_step = 1; st.rerun()
            if c_next.button("다음 — 추가 입력 →", type="primary",
                              use_container_width=True, key="step2_next"):
                if st.session_state.home_sel_stage is None:
                    st.warning("분석할 단계를 선택해 주세요.")
                else:
                    st.session_state.home_step = 3; st.rerun()

        # ════════════════════════════════
        # STEP 3 — 추가 입력 · 실행 · 중단 리포팅
        # ════════════════════════════════
        elif step == 3:
            sel_n   = st.session_state.home_sel_stage
            sel_rec = next((r for r in st.session_state.home_rec_stages if r["stage"] == sel_n), None)
            sel_label = sel_rec["label"] if sel_rec else f"G{sel_n}"
            sel_icon  = sel_rec["icon"]  if sel_rec else "🔬"
            name = st.session_state.tech_name or "기술"

            st.markdown(
                f"<div style='margin-bottom:20px'>"
                f"<div style='font-size:22px;font-weight:700'>{sel_icon} {sel_label} 분석 준비</div>"
                f"<div style='font-size:13px;color:#888;margin-top:4px'>"
                f"<b style='color:#e2e8f0'>{name}</b> — 추가 자료를 보완하면 분석 품질이 높아집니다</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # 기존 입력 요약
            col_a, col_b = st.columns(2)
            col_a.markdown(
                f"<div style='background:#242424;border:1px solid #333;border-radius:8px;"
                f"padding:10px 14px;font-size:11px'>"
                f"<b>입력 자료</b><br>"
                f"<span style='color:#888'>{(st.session_state.home_text[:80] + '…') if st.session_state.home_text else st.session_state.home_filename or '–'}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            col_b.markdown(
                f"<div style='background:#242424;border:1px solid #333;border-radius:8px;"
                f"padding:10px 14px;font-size:11px'>"
                f"<b>선택 단계</b><br>"
                f"<span style='color:#60a5fa'>{sel_icon} {sel_label}</span> · TRL {st.session_state.home_trl}"
                f"</div>",
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # 단계별 추가 입력 필드
            STAGE_EXTRA = {
                0: ("기술 분류 / IPC 코드 (선택)", "예: A01G, G06N"),
                1: ("선행특허 번호 또는 경쟁사 특허 (선택)", "예: KR10-2020-0123456, US10123456"),
                2: ("개발 이력 / TRL 근거 자료 (선택)", "예: 2023 논문 게재, 시제품 제작 완료"),
                3: ("목표 시장 국가 / 산업 섹터 (선택)", "예: 국내 온실 농가, 동남아 AgTech"),
                4: ("인터뷰 대상 고객 유형 (선택)", "예: 중소 온실 농가, 대형 농업법인"),
                5: ("수익 모델 / 가격 전략 (선택)", "예: SaaS 월 구독 200만원, 로열티 5%"),
                6: ("매출 예측 데이터 (선택)", "예: 2025년 5억, 2026년 15억, 2027년 40억"),
                7: ("PoC 대상 기업 / 기관 (선택)", "예: 넥스트팜, 그린플러스, KIST"),
                8: ("인증 목표 국가 / 규격 (선택)", "예: CE, FDA 510(k), KC 인증"),
                9: ("잠재 투자자 / 라이선시 (선택)", "예: 카카오벤처스, LG화학"),
                10:("성과 지표 기준값 (선택)", "예: 매출 목표 50억, 고객 수 100개사"),
            }
            extra_label, extra_ph = STAGE_EXTRA.get(sel_n, ("추가 자료 (선택)", "관련 자료 입력"))
            extra_text = st.text_area(
                extra_label,
                placeholder=extra_ph,
                height=100,
                value=st.session_state.home_extra,
                key="step3_extra",
            )

            # 추가 파일
            extra_file = st.file_uploader(
                "보완 자료 파일 추가 (선택)",
                type=["pdf","docx","txt","xlsx"],
                key="step3_file",
                label_visibility="visible",
            )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            # 버튼 3개
            b_back, b_run, b_stop = st.columns([1, 2, 1])

            if b_back.button("← 뒤로", use_container_width=True, key="step3_back"):
                st.session_state.home_step = 2; st.rerun()

            if b_run.button("🚀 분석 실행", type="primary",
                             use_container_width=True, key="step3_run"):
                st.session_state.home_extra = st.session_state.get("step3_extra","")
                import time as _t
                auto_id = f"TECH-{int(_t.time())%100000}"
                st.session_state.tech_id     = auto_id
                st.session_state.trl         = st.session_state.home_trl
                st.session_state.stage_gates = {}
                new_r = {"id": auto_id, "name": st.session_state.tech_name,
                         "trl": st.session_state.home_trl, "icon": sel_icon}
                st.session_state.recent_techs = [new_r] + st.session_state.recent_techs[:4]

                # 단계별 이동
                _PAGE_MAP = {0:"workspace",1:"ip_hub",2:"ip_hub",3:"ip_hub",
                             4:"interviews",5:"bm",6:"valuation",
                             7:"workspace",8:"workspace",9:"workspace",10:"kpi"}
                st.session_state.page = _PAGE_MAP.get(sel_n, "workspace")
                st.rerun()

            if b_stop.button("⏸ 지금 리포팅", use_container_width=True, key="step3_stop"):
                st.session_state.home_stopped = True

            # 중간 중단 리포트
            if st.session_state.home_stopped:
                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
                st.markdown("---")
                st.subheader("📄 중간 리포트")
                st.markdown(
                    f"**기술명**: {st.session_state.tech_name}  \n"
                    f"**TRL**: {st.session_state.home_trl}  \n"
                    f"**선택 단계**: {sel_icon} {sel_label}  \n"
                    f"**입력 자료 요약**: {st.session_state.home_text[:200] or st.session_state.home_filename or '–'}  \n"
                    f"**추가 자료**: {extra_text or '–'}"
                )
                st.info(
                    f"💡 **추천 경로 요약**\n\n"
                    + "\n".join(
                        f"- {r['icon']} {r['label']}: {r['reason']} ({r['priority']})"
                        for r in st.session_state.home_rec_stages
                    )
                )
                # 다운로드
                report_txt = (
                    f"IPInsight 중간 리포트\n"
                    f"{'='*40}\n"
                    f"기술명: {st.session_state.tech_name}\n"
                    f"TRL: {st.session_state.home_trl}\n"
                    f"선택 단계: {sel_label}\n"
                    f"입력 자료:\n{st.session_state.home_text or st.session_state.home_filename}\n\n"
                    f"추가 자료:\n{extra_text}\n\n"
                    f"추천 분석 경로:\n"
                    + "\n".join(f"- {r['label']}: {r['reason']}" for r in st.session_state.home_rec_stages)
                )
                st.download_button(
                    "📥 중간 리포트 다운로드 (.txt)",
                    data=report_txt.encode("utf-8"),
                    file_name=f"ipinsight_report_{st.session_state.tech_name[:10]}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
                c1, c2 = st.columns(2)
                if c1.button("▶ 분석 계속하기", use_container_width=True, type="primary"):
                    st.session_state.home_stopped = False; st.rerun()
                if c2.button("🔄 처음부터 다시", use_container_width=True):
                    _home_reset()


# ════════════════════════════════════════════════════════════════
# S01 — 기술 워크스페이스 (메인 허브)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "workspace":
    render_topnav()
    render_context_banner()
    st.title("🏠 기술 워크스페이스")
    render_stage_bar()

    st.divider()

    # KPI 요약 (상단 4개)
    c1, c2, c3, c4 = st.columns(4)
    completed = sum(1 for g in st.session_state.stage_gates.values() if g.get("gate") == "Go")
    kills     = sum(1 for g in st.session_state.stage_gates.values() if g.get("gate") == "Kill")
    avg_score = (sum(g.get("score", 0) for g in st.session_state.stage_gates.values())
                 / max(len(st.session_state.stage_gates), 1))
    alerts_d  = api_get(f"/g10/kpi/{st.session_state.tech_id}/alerts", silent=True)
    alert_cnt = alerts_d.get("alert_count", 0) if alerts_d else 0
    c1.metric("완료 단계", f"{completed}/11", "Go 판정")
    c2.metric("평균 점수", f"{avg_score:.1f}", "0~100점")
    c3.metric("Kill 단계", kills, "재검토 필요" if kills else "없음")
    c4.metric("KPI 알림", alert_cnt, "🚨" if alert_cnt else "정상")

    st.divider()

    # 단계별 상태 카드
    st.subheader("단계별 진행 현황")
    cols = st.columns(4)
    for n, (gid, name, icon) in STAGE_META.items():
        info  = st.session_state.stage_gates.get(n, {})
        gate  = info.get("gate", "미실행")
        score = info.get("score", 0)
        gate_icon = {"Go":"🟢","Hold":"🟡","Kill":"🔴","미실행":"⚪"}.get(gate,"⚪")
        with cols[n % 4]:
            st.markdown(
                f"**{icon} {gid} {name}**  \n"
                f"{gate_icon} {gate}"
                + (f" · {score:.0f}점" if gate != "미실행" else ""),
            )

    # 3단 파이프라인 빠른 실행 (G1→G2→G3)
    st.divider()
    with st.expander("⚡ G1→G2→G3 연속 분석 (특허→PCML→SCR→시장성)", expanded=False):
        st.caption("특허 텍스트 하나로 G1 PCML · G2 SCR · G3 시장성을 한 번에 분석합니다.")
        pipeline_text = st.text_area(
            "특허 텍스트 또는 기술 설명",
            value=st.session_state.get("home_text", ""),
            height=120,
            key="ws_pipeline_text",
            placeholder="청구항 또는 기술 요약을 붙여넣으세요…",
        )
        c_tam, c_grow, c_mkt = st.columns(3)
        ws_tam   = c_tam.number_input("TAM (USD)", value=500_000_000, step=100_000_000, format="%d", key="ws_tam")
        ws_grow  = c_grow.number_input("성장률 (%)", value=8.0, step=1.0, key="ws_grow")
        ws_mkt   = c_mkt.text_input("목표 시장", value="글로벌 B2B 기술 라이선싱", key="ws_mkt")
        if st.button("🚀 3단 파이프라인 실행", type="primary", key="ws_chain_run"):
            if not pipeline_text.strip():
                st.warning("특허 텍스트를 입력하세요.")
            else:
                with st.spinner("G1 PCML → G2 SCR → G3 시장성 분석 중…"):
                    resp = api_post("/ip/analyze-chain-extended", {
                        "patent_text": pipeline_text,
                        "tech_id": st.session_state.tech_id or "WS-CHAIN",
                        "tech_name": st.session_state.tech_name or "분석 기술",
                        "tam_usd": ws_tam,
                        "growth_rate_pct": ws_grow,
                        "target_market": ws_mkt,
                    })
                if resp:
                    chain = resp.get("chain", {})
                    scores = resp.get("pipeline_scores", {})
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric("PCML (G1)", f"{scores.get('pcml',0):.0f}점", chain.get('step2_pcml',{}).get('gate',''))
                    sc2.metric("SCR (G2)", f"{scores.get('scr',0):.0f}점", chain.get('step3_scr',{}).get('gate',''))
                    sc3.metric("시장성 (G3)", f"{scores.get('g3',0):.0f}점", chain.get('step4_g3',{}).get('gate',''))
                    sc4.metric("종합 점수", f"{scores.get('composite',0):.0f}점", resp.get('overall_gate',''))
                    # stage_gates 업데이트
                    for stage_n, step_key in [(1,'step2_pcml'),(2,'step3_scr'),(3,'step4_g3')]:
                        s = chain.get(step_key, {})
                        if s.get('gate'):
                            st.session_state.stage_gates[stage_n] = {
                                "gate": s['gate'], "score": s['score']
                            }
                    st.session_state.last_result = {"gate": resp.get('overall_gate',''), "score": scores.get('composite',0), "next_actions": resp.get('next_steps',[])}
                    st.session_state.last_stage  = 3
                    # 다음 단계 안내
                    next_steps = resp.get("next_steps", [])
                    if next_steps:
                        st.markdown("**권장 다음 단계:**")
                        for ns in next_steps[:3]:
                            st.markdown(f"- {ns}")
                else:
                    st.error("파이프라인 실행 실패 — API 서버 상태를 확인하세요.")

    # 마지막 결과 Gate 카드
    if st.session_state.last_result and st.session_state.last_stage is not None:
        st.divider()
        r  = st.session_state.last_result
        sn = st.session_state.last_stage
        gid, name, _ = STAGE_META.get(sn, ("G?", "?", "?"))
        render_gate_card(
            gate=r.get("gate",""),
            score=float(r.get("score",0)),
            stage_label=f"{gid} {name}",
            next_actions=r.get("next_actions",[]),
        )

        # Gate → 다음 단계 버튼
        gate = r.get("gate","")
        if gate == "Go" and sn < 10:
            next_n = sn + 1
            next_name = STAGE_META[next_n][1]
            if st.button(f"▶ {STAGE_META[next_n][2]} G{next_n} {next_name} 시작", type="primary"):
                page_map = {4:"interviews", 5:"bm", 6:"valuation", 10:"kpi"}
                st.session_state.page = page_map.get(next_n, "workspace")
                st.rerun()
        elif gate == "Kill":
            col_a, col_b = st.columns(2)
            if col_a.button("🔄 G0 재진입 (Pivot)"):
                st.session_state.page = "workspace"
            if col_b.button("📄 IP 라이선싱 검토"):
                st.session_state.page = "ip_hub"


# ════════════════════════════════════════════════════════════════
# S03 — IP 분석 허브 (PCML + SCR 체인 통합)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "ip_hub":
    render_topnav()
    render_context_banner()
    st.title("📡 IP 분석 허브")
    render_stage_bar(current=1)

    tab_chain, tab_extended, tab_lifecycle, tab_fto = st.tabs(
        ["⚡ G1+G2 체인", "🚀 G1→G2→G3 통합", "🔄 IP 전주기", "🔍 FTO · 경쟁사"]
    )

    with tab_chain:
        st.subheader("특허 → PCML → SCR 1클릭 체인")
        st.caption("특허번호 또는 청구항 텍스트를 입력하면 PCML v2.0 → SCR 신규성 스크리닝까지 자동 실행합니다.")

        input_mode = st.radio("입력 방식", ["특허 텍스트 직접 입력", "특허번호 (KIPRIS 조회)"], horizontal=True)

        if input_mode == "특허번호 (KIPRIS 조회)":
            patent_id = st.text_input("특허번호", placeholder="KR10-2023-0001234")
            patent_text = ""
        else:
            patent_id = ""
            patent_text = st.text_area(
                "특허 청구항 + 명세서",
                height=160,
                placeholder="청구항 1: ...\n\n[발명의 설명]\n본 발명은...",
                value=st.session_state.get("_ip_text", ""),
            )
            st.session_state["_ip_text"] = patent_text

        scope = st.radio("분석 범위", ["basic (빠름)", "full (정밀)"], horizontal=True)
        scope_val = "full" if "full" in scope else "basic"

        if st.button("⚡ PCML+SCR 체인 실행", type="primary",
                     disabled=(not patent_id and not patent_text)):
            with st.spinner("PCML v2.0 분석 → SCR 신규성 스크리닝 중... (30~60초)"):
                result = api_post("/ip/analyze-chain", {
                    "patent_id":   patent_id,
                    "patent_text": patent_text,
                    "tech_id":     st.session_state.tech_id,
                    "scope":       scope_val,
                })
            if result:
                chain = result.get("chain", {})
                pcml  = chain.get("step2_pcml", {})
                scr   = chain.get("step3_scr",  {})

                c1, c2, c3 = st.columns(3)
                c1.metric("PCML Gate",   pcml.get("gate","–"),  f"점수 {pcml.get('score',0):.1f}")
                c2.metric("SCR 신규성",  scr.get("novelty","–"), scr.get("gate","–"))
                c3.metric("종합 판정",   result.get("overall_gate","–"))

                cc = result.get("consistency_check", {})
                if not cc.get("consistent", True):
                    st.warning(f"⚠️ PCML/SCR 괴리 {cc.get('gap',0):.0f}점 — {cc.get('reason','')}")

                warns = result.get("warnings", [])
                if warns:
                    st.info("ℹ️ " + " · ".join(warns))

                # Gate 행동 카드
                overall_gate = result.get("overall_gate", "")
                render_gate_card(
                    gate=overall_gate,
                    score=float(scr.get("score", pcml.get("score", 0))),
                    stage_label="G1 IP 분석 체인",
                    next_actions=result.get("next_steps", []),
                )
                _save_gate(1, {"gate": overall_gate,
                               "score": scr.get("score", pcml.get("score", 0)),
                               "next_actions": result.get("next_steps", [])})

                with st.expander("전체 분석 결과 JSON"):
                    st.json(result)

    with tab_extended:
        st.subheader("G1 PCML → G2 SCR → G3 시장성 통합 분석")
        st.caption("특허 텍스트 하나로 IP 구조화·신규성·시장성을 한 번에 평가합니다.")

        ext_text = st.text_area(
            "특허 텍스트 또는 기술 설명",
            height=140,
            placeholder="청구항 1: 딥러닝 기반 작물 수확량 예측 방법으로서...",
            key="ext_patent_text",
        )
        ec1, ec2, ec3 = st.columns(3)
        ext_tam    = ec1.number_input("TAM (USD)", value=500_000_000, step=100_000_000, format="%d", key="ext_tam")
        ext_growth = ec2.number_input("성장률 (%)", value=8.0, step=1.0, key="ext_growth")
        ext_mkt    = ec3.text_input("목표 시장", value="글로벌 B2B 기술 라이선싱", key="ext_mkt")

        if st.button("🚀 G1→G2→G3 통합 분석 실행", type="primary",
                     disabled=not ext_text.strip(), key="ext_run"):
            with st.spinner("G1 PCML → G2 SCR → G3 시장성 분석 중… (약 60초)"):
                ext_result = api_post("/ip/analyze-chain-extended", {
                    "patent_text":    ext_text,
                    "tech_id":        st.session_state.tech_id or "EXT",
                    "tech_name":      st.session_state.tech_name or "분석 기술",
                    "tam_usd":        ext_tam,
                    "growth_rate_pct": ext_growth,
                    "target_market":  ext_mkt,
                })
            if ext_result:
                chain  = ext_result.get("chain", {})
                scores = ext_result.get("pipeline_scores", {})
                pcml_s = chain.get("step2_pcml", {})
                scr_s  = chain.get("step3_scr", {})
                g3_s   = chain.get("step4_g3", {})

                # 점수 게이지 4개
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("📋 G1 PCML", f"{scores.get('pcml',0):.0f}점", pcml_s.get('gate',''))
                mc2.metric("🧪 G2 SCR",  f"{scores.get('scr',0):.0f}점",  scr_s.get('gate',''))
                mc3.metric("🌐 G3 시장", f"{scores.get('g3',0):.0f}점",   g3_s.get('gate',''))
                mc4.metric("⭐ 종합",    f"{scores.get('composite',0):.0f}점", ext_result.get('overall_gate',''))

                # 화이트스페이스 카드
                white_space = scr_s.get("white_space", [])
                if white_space:
                    st.markdown("**🔭 화이트스페이스 (진입 가능 공백 영역)**")
                    ws_cols = st.columns(min(len(white_space), 3))
                    for wi, ws in enumerate(white_space[:3]):
                        ws_label = ws.get("area", ws) if isinstance(ws, dict) else str(ws)
                        ws_cols[wi % 3].markdown(
                            f"<div style='background:#1e2a1e;border:1px solid #16a34a;"
                            f"border-radius:8px;padding:10px 12px;font-size:12px'>"
                            f"<b style='color:#4ade80'>🌱 {ws_label}</b></div>",
                            unsafe_allow_html=True,
                        )

                # G3 시장 요약
                st.markdown("**📊 G3 시장성 요약**")
                g3c1, g3c2, g3c3 = st.columns(3)
                g3c1.metric("TAM", f"${ext_tam/1e6:.0f}M")
                g3c2.metric("성장률", f"{ext_growth:.1f}%/yr")
                g3c3.metric("경쟁사 분석", f"{g3_s.get('competitors_analyzed',0)}개사")

                # 다음 단계
                next_steps = ext_result.get("next_steps", [])
                if next_steps:
                    st.markdown("**🗺 권장 다음 단계**")
                    for ns in next_steps[:5]:
                        st.markdown(f"- {ns}")

                # stage_gates 업데이트
                for sn, sk, score_key in [(1,'step2_pcml','pcml'),(2,'step3_scr','scr'),(3,'step4_g3','g3')]:
                    s = chain.get(sk, {})
                    if s.get('gate'):
                        st.session_state.stage_gates[sn] = {"gate": s['gate'], "score": scores.get(score_key, 0)}
                _save_gate(1, {"gate": ext_result.get('overall_gate',''), "score": scores.get('composite',0), "next_actions": next_steps})

                with st.expander("전체 JSON"):
                    st.json(ext_result)
            else:
                st.error("분석 실패 — API 서버를 확인하세요.")

    with tab_lifecycle:
        st.subheader("IP 4단계 전주기 분석")
        ipc = st.text_input("IPC/CPC 코드", value=st.session_state.ipc)
        if st.button("▶ IP 전주기 실행", type="primary"):
            with st.spinner("분석 중..."):
                result = api_post("/ip/full-lifecycle", {
                    "tech_id":   st.session_state.tech_id,
                    "tech_name": st.session_state.tech_name,
                    "ipc_codes": [c.strip() for c in ipc.split(",")],
                    "cpc_codes": [c.strip() for c in ipc.split(",")],
                    "trl":       st.session_state.trl,
                })
            if result:
                st.success("IP 전주기 분석 완료")
                with st.expander("결과 보기"):
                    st.json(result)

    with tab_fto:
        st.subheader("경쟁사·침해 모니터링")
        if st.button("▶ 경쟁사 동향 조회"):
            result = api_get(f"/result/{st.session_state.tech_id}")
            if result:
                st.json(result)
            else:
                st.info("아직 분석 결과가 없습니다. IP 전주기 분석을 먼저 실행하세요.")


# ════════════════════════════════════════════════════════════════
# S04 — G4 인터뷰 보드 (칸반 + JTBD + LoI)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "interviews":
    render_topnav()
    render_context_banner()
    st.title("🤝 G4 고객검증 — NSF I-Corps 인터뷰 보드")
    render_stage_bar(current=4)

    # 진행 현황 요약
    data = api_get(f"/g4/interviews/{st.session_state.tech_id}", silent=True)
    meta = data.get("meta", {}) if data else {}
    total  = meta.get("total_interviews", 0)
    loi_c  = meta.get("loi_interested", 0)
    poc_c  = meta.get("poc_interested", 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 인터뷰", total, "목표 100건")
    c2.metric("LoI 의향", loi_c, "1건 이상 시 LoI 생성 가능")
    c3.metric("PoC 의향", poc_c)
    c4.metric("달성율", f"{min(total/100*100,100):.0f}%")
    st.progress(min(total/100, 1.0), text=f"NSF I-Corps: {total}/100건")

    # Gate 자동 판정 표시
    if total >= 20 and loi_c >= 1:
        render_gate_card("Go", min(total, 100),
                         "G4 고객검증", ["G5 BM 설계로 진행", f"LoI {loi_c}건 확보 — 서명 절차 진행"])
        _save_gate(4, {"gate":"Go","score":min(total,100),"next_actions":["G5 BM 설계"]})
    elif total >= 5:
        render_gate_card("Hold", total,
                         "G4 고객검증", [f"인터뷰 {100-total}건 추가 필요", "LoI 의향자 발굴"])
    else:
        st.info("📋 인터뷰 5건 이상 시 Gate 판정이 시작됩니다.")

    st.divider()
    tab_add, tab_board, tab_loi = st.tabs(["➕ 인터뷰 추가", "📋 인터뷰 보드", "📄 LoI 생성"])

    with tab_add:
        with st.form("interview_form"):
            col1, col2 = st.columns(2)
            with col1:
                customer_type = st.selectbox("고객 유형",
                    ["기업", "병원", "대학", "정부기관", "스타트업", "개인"])
                pain_point = st.text_area("Pain Point", height=90,
                    placeholder="고객이 겪는 핵심 문제를 구체적으로...")
                jtbd = st.text_area("JTBD (해결하려는 과업)", height=90,
                    placeholder="고객이 이 기술로 달성하려는 목표...")
            with col2:
                wtp = st.number_input("지불 의향 (원/월)", min_value=0,
                                       value=100_000, step=10_000)
                loi_yn  = st.checkbox("LoI 서명 의향 있음")
                poc_yn  = st.checkbox("PoC 참여 의향 있음")
                idate   = st.date_input("인터뷰 날짜")
                iviewer = st.text_input("인터뷰어", value="연구자")
            if st.form_submit_button("✅ 인터뷰 저장", type="primary"):
                result = api_post("/g4/interviews", {
                    "tech_id": st.session_state.tech_id,
                    "interviews": [{"customer_type": customer_type,
                                    "pain_point": pain_point, "jtbd": jtbd,
                                    "willingness_to_pay_krw": wtp,
                                    "loi_interest": loi_yn, "poc_interest": poc_yn,
                                    "interview_date": str(idate),
                                    "interviewer": iviewer}],
                })
                if result:
                    new_total = result.get("total_interviews", 0)
                    st.success(f"저장 완료 — 누적 {new_total}건")
                    if loi_yn:
                        st.session_state.g4_data["loi_count"] = \
                            st.session_state.g4_data.get("loi_count", 0) + 1
                    if new_total >= 100:
                        st.balloons()
                    st.rerun()

    with tab_board:
        if data and data.get("interviews"):
            import pandas as pd
            interviews = data["interviews"]

            # 칸반 3열
            todo  = [i for i in interviews if not i.get("loi_interest") and not i.get("poc_interest")]
            inter = [i for i in interviews if i.get("poc_interest")]
            done  = [i for i in interviews if i.get("loi_interest")]

            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown(f"**🗂 일반 인터뷰** ({len(todo)}건)")
                for iv in todo[:5]:
                    st.markdown(
                        f"<div style='background:#1e293b;border:1px solid #334155;"
                        f"border-radius:6px;padding:8px;margin:4px 0;font-size:11px'>"
                        f"<b>{iv.get('customer_type','')}</b><br>{iv.get('pain_point','')[:60]}...</div>",
                        unsafe_allow_html=True,
                    )
            with k2:
                st.markdown(f"**🔬 PoC 관심** ({len(inter)}건)")
                for iv in inter[:5]:
                    st.markdown(
                        f"<div style='background:#1e3a5f;border:1px solid #2563eb55;"
                        f"border-radius:6px;padding:8px;margin:4px 0;font-size:11px'>"
                        f"<b>{iv.get('customer_type','')}</b><br>{iv.get('pain_point','')[:60]}...</div>",
                        unsafe_allow_html=True,
                    )
            with k3:
                st.markdown(f"**📝 LoI 의향** ({len(done)}건)")
                for iv in done[:5]:
                    st.markdown(
                        f"<div style='background:#14532d22;border:1px solid #16a34a55;"
                        f"border-radius:6px;padding:8px;margin:4px 0;font-size:11px'>"
                        f"<b>{iv.get('customer_type','')}</b><br>{iv.get('pain_point','')[:60]}...</div>",
                        unsafe_allow_html=True,
                    )

            # JTBD 분석
            jtbd_data = data.get("jtbd_analysis", {})
            if jtbd_data:
                st.divider()
                st.subheader("JTBD 분석 결과")
                pains = jtbd_data.get("top_pain_points", [])
                if pains:
                    for p in pains[:5]:
                        st.markdown(f"• {p}")
        else:
            st.info("인터뷰 기록이 없습니다. '인터뷰 추가' 탭에서 시작하세요.")

    with tab_loi:
        st.subheader("LoI 도입의향서 자동 생성")
        if loi_c == 0:
            st.warning("LoI 서명 의향자가 없습니다. 인터뷰 추가 시 'LoI 서명 의향 있음'을 체크해 주세요.")
        else:
            st.success(f"✅ LoI 의향자 {loi_c}명 — 도입의향서 생성 가능합니다.")
        org  = st.text_input("발행 기관명", "KAIST 기술사업화팀")
        tname_loi = st.text_input("기술명", st.session_state.tech_name)
        if st.button("📄 LoI 자동 생성", type="primary", disabled=(loi_c == 0)):
            result = api_post("/g4/loi-template", {
                "tech_id": st.session_state.tech_id,
                "org_name": org, "tech_name": tname_loi,
            })
            if result:
                with st.expander("📄 LoI 내용", expanded=True):
                    st.json(result.get("loi_template", result))


# ════════════════════════════════════════════════════════════════
# S05 — G5 BM 캔버스 (9블록 + Unit Economics + 로드맵)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "bm":
    render_topnav()
    render_context_banner()
    st.title("💼 G5 BM 캔버스")
    render_stage_bar(current=5)

    # G4 데이터 자동 인계
    g4 = st.session_state.g4_data
    if g4:
        st.info(f"✅ G4 데이터 자동 인계됨 — LoI {g4.get('loi_count',0)}건 · 인터뷰 {g4.get('interview_count',0)}건")

    tab_bm, tab_ue, tab_rm = st.tabs(["🎨 BM Canvas", "💰 Unit Economics", "🗺️ 사업화 로드맵"])

    with tab_bm:
        col1, col2 = st.columns([1, 1])
        with col1:
            tname_bm   = st.text_input("기술명", st.session_state.tech_name, key="bm_tn")
            model_type = st.selectbox("BM 유형", ["SaaS", "라이선싱", "서비스", "제조판매", "플랫폼"])
            target_mkt = st.text_input("목표 시장", "국내 스마트팜 온실 농가")
        with col2:
            loi_count = st.number_input("LoI 수",       min_value=0, value=g4.get("loi_count",0))
            poc_req   = st.number_input("PoC 요청 수",  min_value=0, value=g4.get("poc_requests",0))
            trl_bm    = st.slider("현재 TRL", 1, 9, st.session_state.trl, key="bm_trl")

        if st.button("⚡ BM 분석 실행 (로드맵·SMK 자동 생성)", type="primary"):
            with st.spinner("G5 BM 분석 중..."):
                result = api_post("/g5/assess", {
                    "tech_id": st.session_state.tech_id,
                    "input_data": {"tech_name": tname_bm, "model_type": model_type,
                                   "target_market": target_mkt, "loi_count": loi_count,
                                   "poc_requests": poc_req, "trl": trl_bm},
                })
            if result:
                _save_gate(5, result)
                st.session_state.g5_data = result.get("output_doc", {})
                render_gate_card(result.get("gate",""), float(result.get("score",0)),
                                 "G5 BM 설계", result.get("next_actions",[]))

                out    = result.get("output_doc", {})
                canvas = out.get("canvas", {})

                if canvas:
                    st.subheader("Business Model Canvas")
                    # 9블록 레이아웃
                    BM_BLOCKS = [
                        ("핵심 파트너", "key_partners"),
                        ("핵심 활동",   "key_activities"),
                        ("가치 제안",   "value_propositions"),
                        ("고객 관계",   "customer_relationships"),
                        ("고객 세그먼트","customer_segments"),
                        ("핵심 자원",   "key_resources"),
                        ("채널",        "channels"),
                        ("비용 구조",   "cost_structure"),
                        ("수익 흐름",   "revenue_streams"),
                    ]
                    row1 = st.columns(5)
                    row2 = st.columns(2)
                    positions = [
                        (row1[0],"핵심 파트너","key_partners"),
                        (row1[1],"핵심 활동","key_activities"),
                        (row1[2],"가치 제안","value_propositions"),
                        (row1[3],"고객 관계","customer_relationships"),
                        (row1[4],"고객 세그먼트","customer_segments"),
                    ]
                    for col, title, key in positions:
                        items = canvas.get(key, [])
                        items = items if isinstance(items, list) else [items]
                        col.markdown(
                            f"<div class='bm-block'><div class='bm-title'>{title}</div>"
                            + "".join(f"<div style='font-size:11px;margin:2px 0'>• {i}</div>"
                                      for i in items[:3])
                            + "</div>",
                            unsafe_allow_html=True,
                        )
                    c_cost, c_rev = st.columns(2)
                    for col, title, key in [
                        (c_cost,"비용 구조","cost_structure"),
                        (c_rev, "수익 흐름","revenue_streams"),
                    ]:
                        items = canvas.get(key, [])
                        items = items if isinstance(items, list) else [items]
                        col.markdown(
                            f"<div class='bm-block'><div class='bm-title'>{title}</div>"
                            + "".join(f"<div style='font-size:11px;margin:2px 0'>• {i}</div>"
                                      for i in items[:3])
                            + "</div>",
                            unsafe_allow_html=True,
                        )

                if out.get("smk_triggered"):
                    st.success("✅ SMK(사업화시장키트) 자동 생성 완료")

                with st.expander("전체 결과 JSON"):
                    st.json(result)

    with tab_ue:
        st.subheader("Unit Economics 분석")
        col1, col2 = st.columns(2)
        with col1:
            cac   = st.number_input("CAC (원)",  min_value=0, value=500_000, step=50_000)
            ltv   = st.number_input("LTV (원)",  min_value=0, value=3_000_000, step=100_000)
            churn = st.slider("Churn율 (%/월)", 0.0, 30.0, 5.0)
        with col2:
            arpu = st.number_input("ARPU (원/월)", min_value=0, value=200_000, step=10_000)
            gm   = st.slider("Gross Margin (%)", 0, 100, 70)

        # 실시간 계산
        ltv_cac  = ltv / max(cac, 1)
        payback  = cac / max(arpu * gm / 100, 1)
        m1, m2, m3 = st.columns(3)
        m1.metric("LTV/CAC",       f"{ltv_cac:.1f}x",
                  "✅ 양호" if ltv_cac >= 3 else "⚠️ 개선 필요")
        m2.metric("Payback 기간",  f"{payback:.1f}개월",
                  "✅ 양호" if payback <= 12 else "⚠️ 개선 필요")
        m3.metric("Gross Margin",  f"{gm}%",
                  "✅ 양호" if gm >= 60 else "⚠️ 개선 필요")

        if st.button("📊 상세 분석 (API)", key="ue_api"):
            r = api_post("/execution/unit-economics", {
                "tech_id": st.session_state.tech_id,
                "input_data": {"cac_krw": cac, "ltv_krw": ltv, "churn_rate_pct": churn,
                               "arpu_krw": arpu, "gross_margin_pct": gm},
            })
            if r:
                with st.expander("상세 분석 결과"):
                    st.json(r)

    with tab_rm:
        st.subheader("사업화 로드맵")
        trl_cur = st.slider("현재 TRL", 1, 9, st.session_state.trl, key="rm_cur")
        trl_tgt = st.slider("목표 TRL", trl_cur, 9, 9, key="rm_tgt")
        if st.button("🗺️ 로드맵 생성", type="primary", key="rm_gen"):
            with st.spinner("사업화 로드맵 생성 중..."):
                r = api_post("/g5/roadmap", {
                    "tech_id": st.session_state.tech_id,
                    "input_data": {"tech_name": st.session_state.tech_name,
                                   "trl_current": trl_cur, "trl_target": trl_tgt},
                })
            if r:
                out = r.get("output_doc", r)
                ms = out.get("milestones", [])
                if ms:
                    import pandas as pd
                    st.dataframe(pd.DataFrame(ms), use_container_width=True)
                with st.expander("전체 JSON"):
                    st.json(r)


# ════════════════════════════════════════════════════════════════
# G6 가치평가
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "valuation":
    render_topnav()
    render_context_banner()
    st.title("💰 G6 기술 가치평가")
    render_stage_bar(current=6)

    col1, col2 = st.columns(2)
    with col1:
        method   = st.selectbox("평가 방법", ["dcf", "cca", "roa"])
        discount = st.slider("할인율 (%)", 5, 40, 15) / 100
        royalty  = st.slider("로열티율 (%)", 1, 20, 5) / 100
    with col2:
        st.subheader("연도별 매출 예측 (USD)")
        revenues = {}
        for y in range(2025, 2030):
            revenues[str(y)] = st.number_input(
                f"{y}년", min_value=0, value=int(1e6*(y-2024)), step=100_000, key=f"rev_{y}")

    if st.button("▶ 가치평가 실행", type="primary"):
        with st.spinner("가치평가 중..."):
            result = api_post("/valuation/dcf", {
                "tech_id": st.session_state.tech_id,
                "revenue_forecast": revenues,
                "discount_rate": discount,
                "royalty_rate": royalty,
                "method": method,
            })
        if result:
            _save_gate(6, result)
            out = result.get("output_doc", result)
            val = out.get("valuation_usd") or out.get("npv_usd") or out.get("value_usd", 0)
            st.metric("추정 기술 가치", f"${val:,.0f}" if val else "산출 불가")
            render_gate_card(result.get("gate",""), float(result.get("score",0)),
                             "G6 가치평가", result.get("next_actions",[]))
            with st.expander("상세 결과"):
                st.json(result)


# ════════════════════════════════════════════════════════════════
# G10 KPI 대시보드
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "kpi":
    render_topnav()
    render_context_banner()
    st.title("📈 G10 성과 모니터링")
    render_stage_bar(current=10)

    tab_dash, tab_record, tab_alert = st.tabs(["📊 대시보드", "✏️ KPI 기록", "🔔 알림"])

    KPI_META = {
        "revenue_usd":                ("매출액",     "USD", 1_000_000),
        "royalty_usd":                ("로열티",     "USD",   100_000),
        "investment_raised_usd":      ("투자유치",   "USD",   500_000),
        "poc_to_commercial_rate_pct": ("PoC→사업화", "%",          30),
        "tech_utilization_rate_pct":  ("기술활용율", "%",          70),
        "new_customers":              ("신규고객",   "건",         10),
    }

    with tab_dash:
        if st.button("🔄 새로고침", key="kpi_rf"):
            st.rerun()
        data = api_get(f"/g10/kpi/{st.session_state.tech_id}", silent=True)
        if data and data.get("event_count", 0) > 0:
            latest = data.get("latest_kpis", {})
            cols = st.columns(3)
            for i, (key, (label, unit, target)) in enumerate(KPI_META.items()):
                val = latest.get(key, 0)
                pct = val / target * 100 if target else 0
                cols[i%3].metric(f"{label} ({unit})", f"{val:,.1f}",
                                  f"{pct:.0f}% 달성")

            events = data.get("events", [])
            if events:
                try:
                    import plotly.express as px, pandas as pd
                    df = pd.DataFrame(events).sort_values("recorded_at")
                    fig = px.line(df, x="recorded_at", y="value", color="kpi_key",
                                  title="KPI 추이", height=300,
                                  labels={"recorded_at":"시각","value":"값","kpi_key":"KPI"})
                    fig.update_layout(margin=dict(t=40,b=20))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass

            alerts_d = api_get(f"/g10/kpi/{st.session_state.tech_id}/alerts", silent=True)
            if alerts_d and alerts_d.get("alert_count", 0) > 0:
                has_d = alerts_d.get("has_danger")
                (st.error if has_d else st.warning)(
                    f"{'🚨' if has_d else '⚠️'} KPI 알림 {alerts_d['alert_count']}건 — '알림' 탭 확인")
        else:
            st.info("KPI 기록 없음. 'KPI 기록' 탭에서 입력하세요.")

    with tab_record:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("kpi_single"):
                kpi_key = st.selectbox("KPI 항목", list(KPI_META.keys()))
                kpi_val = st.number_input("값", min_value=0.0, step=1000.0)
                kpi_note = st.text_input("메모")
                if st.form_submit_button("✅ 기록", type="primary"):
                    r = api_post("/g10/kpi", {"tech_id": st.session_state.tech_id,
                                              "kpi_key": kpi_key, "value": kpi_val,
                                              "note": kpi_note, "source": "dashboard"})
                    if r:
                        st.success("기록 완료")
                        st.rerun()
        with c2:
            with st.form("kpi_batch"):
                st.caption("일괄 기록")
                vals = {}
                for key, (label, unit, _) in KPI_META.items():
                    vals[key] = st.number_input(f"{label} ({unit})",
                                                min_value=0.0, step=100.0, key=f"b_{key}")
                if st.form_submit_button("📤 일괄 기록", type="primary"):
                    r = api_post("/g10/kpi/batch",
                                 {"tech_id": st.session_state.tech_id, "actuals": vals})
                    if r:
                        st.success(f"{r.get('recorded',0)}개 기록 완료")
                        st.rerun()

    with tab_alert:
        alerts_d = api_get(f"/g10/kpi/{st.session_state.tech_id}/alerts")
        if alerts_d:
            alerts = alerts_d.get("alerts", [])
            if not alerts:
                st.success("✅ 모든 KPI 정상")
            for a in alerts:
                fn = st.error if a["level"] == "danger" else st.warning
                fn(f"{'🔴' if a['level']=='danger' else '🟡'} {a['message']}")
        else:
            st.info("KPI 기록이 없어 알림을 확인할 수 없습니다.")


# ════════════════════════════════════════════════════════════════
# 보고서 센터 (R1~R9)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "reports":
    render_topnav()
    render_context_banner()
    st.title("📄 보고서 센터 — R1~R9")
    render_stage_bar()

    REPORT_META = {
        "R1_investment":   ("R1 투자타당성",     "IP 구조 분석 기반 투자 검토 보고서"),
        "R2_enforcement":  ("R2 권리행사",        "FTO · 침해 분석 보고서"),
        "R3_commercialize":("R3 기술사업화",      "G0~G5 종합 사업화 전략 보고서"),
        "R4_portfolio":    ("R4 포트폴리오",      "기술 포트폴리오 전략 보고서"),
        "R5_valuation":    ("R5 가치평가",        "DCF · CCA · ROA 종합 보고서"),
        "R6_ir":           ("R6 IR 덱",           "투자자용 12슬라이드 IR 자료"),
        "R7_license":      ("R7 라이선싱",        "라이선스 구조 · 로열티 보고서"),
        "R8_gov_ir":       ("R8 정부 IR",         "KIAT/KEIT 정부 제출용 IR"),
        "R9_sps":          ("R9 신규성 스크리닝", "PCML+SCR 기반 신규성 검토 보고서"),
    }

    # 가용성 조회
    avail_data = api_get("/reports/availability", silent=True) or {}
    avail = avail_data.get("availability", {})

    cols = st.columns(3)
    for i, (rid, (rname, rdesc)) in enumerate(REPORT_META.items()):
        is_avail = avail.get(rid, {}).get("available", False) if avail else True
        with cols[i % 3]:
            status = "🟢 생성 가능" if is_avail else "🔒 의존성 부족"
            st.markdown(
                f"**{rname}**  \n"
                f"<small>{rdesc}</small>  \n"
                f"{status}",
                unsafe_allow_html=True,
            )
            if st.button(f"생성", key=f"rpt_{rid}",
                         type="primary" if is_avail else "secondary",
                         disabled=not is_avail):
                with st.spinner(f"{rname} 생성 중..."):
                    r = api_post("/reports/generate", {
                        "tech_id": st.session_state.tech_id,
                        "report_type": rid,
                        "input_data": {"tech_name": st.session_state.tech_name},
                    })
                if r:
                    with st.expander(f"📄 {rname} 결과", expanded=True):
                        st.json(r)
            st.divider()


# ════════════════════════════════════════════════════════════════
# 전체 로드맵
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "roadmap":
    render_topnav()
    render_context_banner()
    st.title("🗺️ G0→G10 전체 로드맵")
    render_stage_bar()

    col1, col2 = st.columns(2)
    with col1:
        tech_type = st.selectbox("기술 유형", ["general","biotech","ICT","device","material"])
        region    = st.selectbox("목표 국가", ["KOR","USA","EU","JPN","CHN","SGP"])
    with col2:
        trl_cur = st.slider("현재 TRL", 1, 9, st.session_state.trl, key="rm_cur2")
        trl_tgt = st.slider("목표 TRL", trl_cur, 9, 9, key="rm_tgt2")

    if st.button("⚡ 전체 로드맵 생성", type="primary"):
        with st.spinner("G0~G10 로드맵 생성 중... (30~60초)"):
            result = api_post("/roadmap/full", {
                "tech_id": st.session_state.tech_id,
                "tech_name": st.session_state.tech_name,
                "tech_type": tech_type, "region": region,
                "trl_current": trl_cur, "trl_target": trl_tgt,
            })
        if result:
            stages = result.get("stages", {})
            if stages:
                try:
                    import plotly.graph_objects as go
                    x = list(stages.keys())
                    y = [v.get("score",0) for v in stages.values()]
                    colors = ["#22c55e" if v.get("gate")=="Go" else
                              "#eab308" if v.get("gate")=="Hold" else "#ef4444"
                              for v in stages.values()]
                    fig = go.Figure(go.Bar(x=x, y=y, marker_color=colors,
                                          text=[f"{s:.0f}" for s in y],
                                          textposition="auto"))
                    fig.update_layout(title="G-Stage Gate 점수", height=300,
                                      margin=dict(t=40,b=20))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass

                for sid, sdata in stages.items():
                    gate  = sdata.get("gate","")
                    score = sdata.get("score",0)
                    icon  = "🟢" if gate=="Go" else "🟡" if gate=="Hold" else "🔴"
                    with st.expander(f"{icon} {sid} — {gate} ({score:.0f}점)"):
                        st.json(sdata)
            else:
                st.json(result)


# ════════════════════════════════════════════════════════════════
# 관리자 콘솔 (통합)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "admin":
    render_topnav()
    st.title("⚙️ 관리자 콘솔")

    tab_health, tab_metrics, tab_jobs, tab_login = st.tabs(
        ["🩺 헬스 체크", "📊 API 메트릭", "📋 Job 모니터", "🔐 인증"]
    )

    with tab_health:
        h = api_get("/health")
        if h:
            c1, c2 = st.columns(2)
            c1.metric("API 버전", h.get("version","?"))
            c2.metric("LLM 백엔드", "Groq" if h.get("groq") else "Anthropic/Rule")
            st.subheader("커넥터 상태")
            conns = h.get("connectors", {})
            for k, v in conns.items():
                st.markdown(f"{'🟢' if v else '🟡'} **{k}** — {'연결됨' if v else '미연결'}")

    with tab_metrics:
        if st.button("🔄 새로고침", key="adm_rf"):
            st.rerun()
        m = api_get("/metrics")
        if m:
            c1, c2, c3 = st.columns(3)
            c1.metric("총 요청", m.get("requests",0))
            c2.metric("오류율", f"{m.get('error_rate',0):.1f}%")
            c3.metric("평균 응답", f"{m.get('avg_ms',0):.0f}ms")
            recent = m.get("recent_10",[])
            if recent:
                import pandas as pd
                st.dataframe(pd.DataFrame(recent), use_container_width=True)

    with tab_jobs:
        job_id = st.text_input("Job ID", placeholder="UUID")
        if st.button("📋 조회") and job_id:
            job = api_get(f"/jobs/{job_id}")
            if job:
                status = job.get("status","")
                icon = {"queued":"⏳","running":"🔄","completed":"✅","failed":"❌"}.get(status,"❓")
                st.metric("상태", f"{icon} {status}")
                if job.get("result"):
                    with st.expander("결과"):
                        st.json(job["result"])
                if job.get("error"):
                    st.error(job["error"])

    with tab_login:
        if st.session_state.token:
            st.success("✅ 인증됨")
            if st.button("로그아웃"):
                st.session_state.token = ""
                st.rerun()
        else:
            with st.form("login_form"):
                u = st.text_input("아이디", value="admin")
                p = st.text_input("비밀번호", type="password")
                if st.form_submit_button("로그인", type="primary"):
                    r = api_post("/auth/token", {"username": u, "password": p})
                    if r and "access_token" in r:
                        st.session_state.token = r["access_token"]
                        st.success("로그인 완료")
                        st.rerun()
                    else:
                        st.error("로그인 실패")
            st.info("개발 모드에서는 인증 없이 API 호출 가능합니다.")
