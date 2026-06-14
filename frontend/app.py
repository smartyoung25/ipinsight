"""IPInsight — 글로벌 기술사업화 Agent OS (UX v2.1)
실행: streamlit run frontend/app.py
"""
from __future__ import annotations
import os, time, json, re
import requests
import streamlit as st

# ── 설정 ─────────────────────────────────────────────────────────
API_URL = os.environ.get("IPINSIGHT_API", "http://localhost:8100")

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


# ════════════════════════════════════════════════════════════════
# HOME — Claude 스타일 랜딩 화면
# ════════════════════════════════════════════════════════════════
if st.session_state.page == "home":

    health = api_get("/health", silent=True)
    api_ok = health is not None

    # ── 좌측 패널 / 우측 패널 컬럼 ──
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
        api_dot = "🟢" if api_ok else "🔴"
        st.caption(f"{api_dot} API {'연결됨' if api_ok else '오프라인'}")
        if st.session_state.token:
            if st.button("로그아웃", use_container_width=True, key="logout_home"):
                st.session_state.token = ""; st.rerun()
        else:
            if st.button("🔐 로그인", use_container_width=True, key="login_home"):
                st.session_state.page = "admin"; st.rerun()

    # ──────────── 우측 패널 ────────────
    with right_col:
        # 상단 여백
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)

        # 인사말
        st.markdown(
            "<div style='text-align:center;margin-bottom:32px'>"
            "<div style='font-size:36px;font-weight:700;color:#f0f0f0;line-height:1.3'>"
            "기술의 가치를 발견하세요</div>"
            "<div style='font-size:14px;color:#666;margin-top:8px'>"
            "특허·논문·사업계획서·기술명 — 무엇이든 입력하면 G0→G10 사업화 분석이 시작됩니다</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # ── 입력 모드 탭 ──
        mode_labels = {
            "text":      ("✏️",  "직접 입력"),
            "patent_no": ("📄",  "특허번호"),
            "paper":     ("🎓",  "논문 정보"),
            "bizplan":   ("📊",  "사업계획서"),
            "file":      ("📎",  "파일 업로드"),
        }
        tab_cols = st.columns(len(mode_labels))
        for i, (mode_key, (icon, label)) in enumerate(mode_labels.items()):
            is_active = st.session_state.input_mode == mode_key
            btn_type  = "primary" if is_active else "secondary"
            with tab_cols[i]:
                if st.button(f"{icon} {label}", use_container_width=True,
                             type=btn_type, key=f"mode_{mode_key}"):
                    st.session_state.input_mode = mode_key
                    st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        mode = st.session_state.input_mode

        # ── 모드별 입력 폼 ──
        with st.form("landing_form", clear_on_submit=False):

            if mode == "text":
                user_input = st.text_area(
                    "기술 설명",
                    placeholder=(
                        "기술명, 특허 청구항, 기술 요약 등을 자유롭게 입력하세요.\n\n"
                        "예시:\n"
                        "• 청구항 1: 딥러닝 기반 작물 수확량 예측 방법으로서...\n"
                        "• 본 발명은 IoT 센서와 머신러닝을 결합하여..."
                    ),
                    height=160, label_visibility="collapsed",
                )
                tech_id_input   = st.text_input("기술 ID (선택)", placeholder="예: KR-2024-AI-001", value="")
                tech_name_input = st.text_input("기술명 (선택)", placeholder="예: 스마트팜 수확량 예측 AI", value="")
                patent_no_input = ""
                paper_title     = ""; paper_doi = ""; paper_abstract = ""
                biz_summary     = ""; biz_target = ""
                uploaded_file   = None

            elif mode == "patent_no":
                st.markdown("##### 특허번호로 분석")
                patent_no_input = st.text_input(
                    "특허번호",
                    placeholder="KR10-2023-0001234  /  US11234567  /  EP3456789",
                    label_visibility="collapsed",
                )
                c1, c2 = st.columns(2)
                tech_id_input   = c1.text_input("기술 ID", placeholder="자동 생성됨", value="")
                tech_name_input = c2.text_input("기술명 (선택)", placeholder="특허 제목에서 자동 추출", value="")
                user_input = patent_no_input
                paper_title = ""; paper_doi = ""; paper_abstract = ""
                biz_summary = ""; biz_target = ""
                uploaded_file = None

            elif mode == "paper":
                st.markdown("##### 논문 정보 입력")
                c1, c2 = st.columns(2)
                paper_title    = c1.text_input("논문 제목", placeholder="예: Deep Learning for Crop Yield Prediction")
                paper_doi      = c2.text_input("DOI / arXiv", placeholder="10.1000/xyz123  또는  arXiv:2301.00000")
                paper_abstract = st.text_area("초록 (Abstract)", height=120,
                                              placeholder="논문 초록을 붙여넣으세요...")
                tech_name_input = st.text_input("파생 기술명 (선택)", placeholder="논문에서 파생될 기술명")
                user_input      = f"{paper_title}\n{paper_doi}\n{paper_abstract}"
                tech_id_input   = ""; patent_no_input = ""
                biz_summary = ""; biz_target = ""
                uploaded_file = None

            elif mode == "bizplan":
                st.markdown("##### 사업계획서 정보 입력")
                biz_summary = st.text_area(
                    "기술/사업 요약",
                    height=130,
                    placeholder=(
                        "사업계획서의 핵심 내용을 입력하세요.\n"
                        "• 개발 기술 개요\n• 목표 시장 및 고객\n• 수익 모델\n• 기대 효과"
                    ),
                )
                c1, c2 = st.columns(2)
                biz_target      = c1.text_input("목표 시장", placeholder="예: 국내 온실 농가 2만 호")
                tech_name_input = c2.text_input("기술명", placeholder="예: AI 작물 관리 SaaS")
                user_input      = f"{biz_summary}\n목표시장: {biz_target}"
                tech_id_input   = ""; patent_no_input = ""
                paper_title = ""; paper_doi = ""; paper_abstract = ""
                uploaded_file = None

            else:  # file
                st.markdown("##### 파일 업로드")
                uploaded_file = st.file_uploader(
                    "파일 선택",
                    type=["pdf", "txt", "docx", "hwp", "xlsx", "png", "jpg"],
                    label_visibility="collapsed",
                    help="특허명세서 PDF, 사업계획서 DOCX, 논문 PDF, 기술개요 TXT 등",
                )
                tech_name_input = st.text_input("기술명 (선택)", placeholder="파일에서 자동 추출 시도")
                user_input      = uploaded_file.name if uploaded_file else ""
                tech_id_input   = ""; patent_no_input = ""
                paper_title = ""; paper_doi = ""; paper_abstract = ""
                biz_summary = ""; biz_target = ""

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            # TRL 슬라이더
            trl_val = st.select_slider(
                "현재 TRL 단계",
                options=list(range(1, 10)),
                value=4,
                format_func=lambda x: {
                    1:"TRL1 기초연구",2:"TRL2 개념정립",3:"TRL3 개념검증",
                    4:"TRL4 실험실검증",5:"TRL5 파일럿",6:"TRL6 시제품",
                    7:"TRL7 시스템검증",8:"TRL8 인증",9:"TRL9 상용화",
                }[x],
            )

            # 제출
            submitted = st.form_submit_button(
                "🚀  분석 시작",
                use_container_width=True,
                type="primary",
            )

        if submitted and (user_input or uploaded_file):
            # 기술 ID 자동 생성
            import time as _time
            auto_id = tech_id_input.strip() or f"TECH-{int(_time.time()) % 100000}"
            auto_name = tech_name_input.strip() or (
                patent_no_input.strip() or
                paper_title[:30] or
                biz_target[:30] or
                user_input[:30].replace("\n", " ") or
                "분석 기술"
            )

            st.session_state.tech_id   = auto_id
            st.session_state.tech_name = auto_name
            st.session_state.trl       = trl_val
            st.session_state.ipc       = ""
            st.session_state.stage_gates = {}

            # 최근 분석 목록에 추가
            new_recent = {"id": auto_id, "name": auto_name, "trl": trl_val, "icon": "🔬"}
            recs = [r for r in st.session_state.recent_techs if r["id"] != auto_id]
            st.session_state.recent_techs = [new_recent] + recs[:4]

            # 입력 유형에 따라 첫 분석 화면으로 이동
            if mode in ("patent_no", "text") and (patent_no_input or user_input):
                st.session_state.page = "ip_hub"
            elif mode == "paper":
                st.session_state.page = "ip_hub"
            elif mode == "bizplan":
                st.session_state.page = "bm"
            else:
                st.session_state.page = "workspace"
            st.rerun()

        elif submitted:
            st.warning("입력값을 먼저 작성해 주세요.")

        # ── 예시 칩 ──
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:center;font-size:11px;color:#555;margin-bottom:10px'>"
            "빠른 시작 예시</div>",
            unsafe_allow_html=True,
        )
        chip_data = [
            ("📄", "KR10-2021-0112233", "patent_no"),
            ("🌱", "스마트팜 수확량 AI", "text"),
            ("⚡", "차세대 배터리 양극재", "text"),
            ("🧬", "mRNA 백신 전달체", "text"),
            ("🤖", "US10123456 (robotics)", "patent_no"),
            ("🎓", "IEEE 논문 기술이전", "paper"),
        ]
        chip_cols = st.columns(3)
        for i, (icon, label, chip_mode) in enumerate(chip_data):
            with chip_cols[i % 3]:
                if st.button(f"{icon} {label}", use_container_width=True,
                             key=f"chip_{i}"):
                    st.session_state.input_mode = chip_mode
                    st.session_state.tech_name  = label
                    st.session_state.tech_id    = f"DEMO-{i+10}"
                    st.session_state.trl        = 4
                    st.session_state.stage_gates = {}
                    new_r = {"id": f"DEMO-{i+10}", "name": label, "trl": 4, "icon": icon}
                    recs2 = [r for r in st.session_state.recent_techs if r["id"] != f"DEMO-{i+10}"]
                    st.session_state.recent_techs = [new_r] + recs2[:4]
                    st.session_state.page = "workspace"
                    st.rerun()


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

    tab_chain, tab_lifecycle, tab_fto = st.tabs(
        ["⚡ PCML+SCR 분석 체인", "🔄 IP 전주기 분석", "🔍 FTO · 경쟁사"]
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
