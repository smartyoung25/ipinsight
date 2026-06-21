"""IPInsight — 글로벌 기술사업화 Agent OS (UX v2.1)
실행: streamlit run frontend/app.py
"""
from __future__ import annotations
import os, time, json, re, datetime, random
import requests
import streamlit as st

# ── 설정 ─────────────────────────────────────────────────────────
API_URL = os.environ.get("IPINSIGHT_API", "http://localhost:8001")

STAGE_META = {
    0:  ("G0",  "기술발굴",    "🔭"),
    1:  ("G1",  "IP 구조화",   "📋"),
    2:  ("G2",  "기술성 평가", "🧪"),
    3:  ("G3",  "시장성 평가", "🌐"),
    4:  ("G4",  "고객검증",    "🤝"),
    5:  ("G5",  "사업화전략",  "💼"),
    6:  ("G6",  "가치평가",    "💰"),
    7:  ("G7",  "PoC 실증",    "🔬"),
    8:  ("G8",  "PoB / MRL",  "📊"),
    9:  ("G9",  "거래·투자",   "🤝"),
    10: ("G10", "성과관리",    "📈"),
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
    initial_sidebar_state="expanded",
)

# ── CSS 커스텀 ────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── 전역 ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
/* ── Streamlit 사이드바 스타일 재정의 ── */
[data-testid="stSidebar"] {
  background: #0a0b10 !important;
  border-right: 1px solid rgba(255,255,255,.06) !important;
  min-width: 220px !important;
  max-width: 260px !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebarContent"] { padding: 0 !important; }
/* 메인 콘텐츠 여백 */
.block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }
* { box-sizing: border-box; }
body, .stApp { font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif !important; }
/* 크림 테마 사이드바 */
body[data-theme="cream"] [data-testid="stSidebar"] {
  background: #f0e9df !important;
  border-right-color: #ddd0bc !important;
}
/* 블랙 테마 사이드바 */
body[data-theme="black"] [data-testid="stSidebar"] {
  background: #030303 !important;
  border-right-color: rgba(255,255,255,.04) !important;
}

/* ══ 앱 쉘 ══ */
.app-shell {
  display: flex; height: 100vh; overflow: hidden;
  background: #0b0d14;
}

/* ══ 사이드바 ══ */
.sidebar {
  width: 220px; min-width: 220px;
  background: #0a0b10;
  border-right: 1px solid rgba(255,255,255,.06);
  display: flex; flex-direction: column;
  overflow-y: auto; overflow-x: hidden;
  padding-bottom: 12px;
}
.sb-brand {
  padding: 14px 14px 10px;
  display: flex; align-items: center; gap: 8px;
  border-bottom: 1px solid rgba(255,255,255,.05);
}
.sb-brand-icon { font-size: 16px; }
.sb-brand-text { font-size: 12px; font-weight: 700; color: #f1f5f9; letter-spacing: -.2px; }
.sb-brand-sub  { font-size: 9px; color: rgba(255,255,255,.3); margin-top: 1px; }

/* 컨텍스트 칩 */
.sb-ctx {
  margin: 8px 10px; padding: 8px 10px;
  background: rgba(37,99,235,.1);
  border: 1px solid rgba(37,99,235,.2);
  border-radius: 8px; font-size: 10px;
}
.sb-ctx-name { font-weight: 600; color: #93c5fd; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sb-ctx-meta { color: rgba(255,255,255,.35); margin-top: 2px; }

/* 섹션 라벨 */
.sb-label {
  font-size: 9px; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; color: rgba(255,255,255,.2);
  padding: 12px 14px 4px;
}

/* 네비 아이템 */
.sb-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; margin: 1px 8px;
  border-radius: 7px; cursor: pointer;
  font-size: 11px; font-weight: 500; color: rgba(255,255,255,.5);
  transition: background .1s, color .1s;
  white-space: nowrap;
}
.sb-item:hover { background: rgba(255,255,255,.06); color: rgba(255,255,255,.85); }
.sb-item.active { background: rgba(37,99,235,.15); color: #93c5fd; }
.sb-item-icon { font-size: 12px; opacity: .7; flex-shrink: 0; width: 16px; text-align: center; }
.sb-item-label { flex: 1; overflow: hidden; text-overflow: ellipsis; }

/* 스테이지 레일 */
.sb-stage {
  display: flex; align-items: center; gap: 7px;
  padding: 5px 12px; margin: 1px 8px;
  border-radius: 7px; cursor: pointer;
  font-size: 10.5px; color: rgba(255,255,255,.4);
  transition: background .1s, color .1s;
}
.sb-stage:hover { background: rgba(255,255,255,.05); color: rgba(255,255,255,.75); }
.sb-stage.active { background: rgba(37,99,235,.12); color: #93c5fd; }
.sb-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-go   { background: #4ade80; box-shadow: 0 0 4px #4ade8066; }
.dot-hold { background: #fbbf24; box-shadow: 0 0 4px #fbbf2466; }
.dot-kill { background: #f87171; box-shadow: 0 0 4px #f8717166; }
.dot-idle { background: rgba(255,255,255,.15); }
.sb-stage-gid { font-weight: 600; font-size: 9px; color: rgba(255,255,255,.3); min-width: 22px; }
.sb-divider { border: none; border-top: 1px solid rgba(255,255,255,.05); margin: 6px 0; }

/* API 상태 */
.sb-status {
  margin-top: auto; padding: 8px 10px;
  border-top: 1px solid rgba(255,255,255,.05);
  font-size: 9px; color: rgba(255,255,255,.3);
  display: flex; align-items: center; gap: 5px;
}
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; }
.status-dot.off { background: #f87171; }

/* ══ 메인 콘텐츠 ══ */
.main-area {
  flex: 1; overflow-y: auto;
  background: #0f1117;
  display: flex; flex-direction: column;
}

/* 상단 컨텍스트 바 */
.ctx-bar {
  padding: 10px 24px; border-bottom: 1px solid rgba(255,255,255,.06);
  display: flex; align-items: center; gap: 12px;
  background: rgba(0,0,0,.2); backdrop-filter: blur(8px);
  position: sticky; top: 0; z-index: 10; flex-shrink: 0;
}
.ctx-breadcrumb { font-size: 12px; color: rgba(255,255,255,.4); }
.ctx-breadcrumb b { color: #e2e8f0; }
.ctx-badge {
  font-size: 10px; padding: 2px 8px; border-radius: 5px; font-weight: 600;
}
.badge-go   { background: #14532d; color: #4ade80; }
.badge-hold { background: #451a03; color: #fbbf24; }
.badge-kill { background: #450a0a; color: #f87171; }
.badge-trl  { background: rgba(37,99,235,.2); color: #93c5fd; }
.badge-new  { background: rgba(255,255,255,.07); color: rgba(255,255,255,.5); }
.ctx-spacer { flex: 1; }

/* 페이지 바디 */
.page-body { padding: 28px 28px; }
.page-title {
  font-size: 22px; font-weight: 800; color: #f1f5f9;
  letter-spacing: -.4px; margin-bottom: 4px;
}
.page-sub { font-size: 13px; color: rgba(255,255,255,.4); margin-bottom: 20px; }

/* KPI 카드 그리드 */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 24px; }
.kpi-card {
  background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.07);
  border-radius: 12px; padding: 16px;
}
.kpi-card-label { font-size: 10px; font-weight: 600; color: rgba(255,255,255,.35); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
.kpi-card-val { font-size: 26px; font-weight: 800; color: #f1f5f9; letter-spacing: -.5px; }
.kpi-card-delta { font-size: 10px; color: rgba(255,255,255,.35); margin-top: 2px; }

/* 섹션 헤더 */
.sec-header { font-size: 13px; font-weight: 700; color: #e2e8f0; margin: 20px 0 10px; display: flex; align-items: center; gap: 6px; }
.sec-header::after { content:''; flex:1; height:1px; background:rgba(255,255,255,.06); margin-left:8px; }

/* 스테이지 그리드 카드 */
.stage-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; }
.sg-card {
  background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.07);
  border-radius: 10px; padding: 12px; cursor: pointer;
  transition: all .15s;
}
.sg-card:hover { border-color: rgba(255,255,255,.15); background: rgba(255,255,255,.05); transform: translateY(-1px); }
.sg-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.sg-gid { font-size: 10px; font-weight: 700; color: rgba(255,255,255,.3); }
.sg-gate { font-size: 10px; font-weight: 600; }
.sg-name { font-size: 12px; font-weight: 600; color: #e2e8f0; margin-bottom: 2px; }
.sg-score { font-size: 11px; color: rgba(255,255,255,.35); }
.sg-idle { color: rgba(255,255,255,.2); font-style: italic; font-size: 10px; }

/* 홈 그리딩 */
.home-hero { text-align: center; padding: 40px 0 28px; }
.home-title {
  font-size: 36px; font-weight: 800; letter-spacing: -1.5px;
  background: linear-gradient(135deg, #f1f5f9 30%, #93c5fd 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 8px; line-height: 1.15;
}
.home-sub { font-size: 14px; color: rgba(255,255,255,.4); line-height: 1.6; }

/* 입력 박스 */
.input-wrap {
  background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.1);
  border-radius: 14px; padding: 18px 20px 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,.4);
  transition: border-color .2s, box-shadow .2s;
}
.input-wrap:focus-within {
  border-color: rgba(59,130,246,.5);
  box-shadow: 0 0 0 3px rgba(59,130,246,.1), 0 4px 24px rgba(0,0,0,.4);
}

/* 칩 */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 16px 0 24px; }
.chip {
  background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1);
  border-radius: 20px; padding: 6px 14px; font-size: 11.5px; color: rgba(255,255,255,.55);
  cursor: pointer; transition: all .15s; display: inline-flex; align-items: center; gap: 5px;
}
.chip:hover { background: rgba(59,130,246,.15); border-color: rgba(59,130,246,.4); color: #93c5fd; }

/* 타입 탭 */
.type-tabs { display: flex; gap: 6px; margin-bottom: 12px; }
.type-tab {
  background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.1);
  border-radius: 7px; padding: 5px 14px; font-size: 11px; color: rgba(255,255,255,.5); cursor: pointer; transition: all .15s;
}
.type-tab.active, .type-tab:hover { background: rgba(37,99,235,.2); border-color: rgba(59,130,246,.4); color: #93c5fd; }

/* 최근 분석 카드 */
.rec-cards { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; margin-top: 12px; }
.rec-card {
  background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.08);
  border-radius: 12px; padding: 14px 16px; width: 175px; cursor: pointer;
  transition: all .18s;
}
.rec-card:hover { border-color: rgba(59,130,246,.4); background: rgba(37,99,235,.1); transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,.3); }
.rec-icon { font-size: 20px; margin-bottom: 8px; }
.rec-title { font-size: 11.5px; font-weight: 600; color: #e2e8f0; margin-bottom: 3px; line-height: 1.4; }
.rec-sub { font-size: 9.5px; color: rgba(255,255,255,.3); }

/* 보고서 섹션 */
.report-card {
  background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.07);
  border-radius: 10px; padding: 14px 16px; margin-bottom: 8px;
  display: flex; align-items: center; gap: 12px;
}
.report-card:hover { border-color: rgba(255,255,255,.14); background: rgba(255,255,255,.05); }
.report-icon { font-size: 20px; flex-shrink: 0; }
.report-meta { flex: 1; }
.report-label { font-size: 12px; font-weight: 600; color: #e2e8f0; }
.report-desc { font-size: 10.5px; color: rgba(255,255,255,.35); margin-top: 2px; }
.report-badge { font-size: 9px; padding: 2px 7px; border-radius: 4px; font-weight: 700; flex-shrink: 0; }
.rb-t1 { background: rgba(37,99,235,.2); color: #93c5fd; }
.rb-t2 { background: rgba(124,58,237,.2); color: #c4b5fd; }
.rb-t3 { background: rgba(6,182,212,.2); color: #67e8f9; }

/* 3단 위저드 진행 바 */
.wizard-steps { display: flex; gap: 0; margin-bottom: 24px; }
.wz-step {
  flex: 1; padding: 10px 16px; text-align: center;
  border-bottom: 2px solid rgba(255,255,255,.08);
  font-size: 11px; color: rgba(255,255,255,.3); font-weight: 500;
}
.wz-step.active { border-bottom-color: #2563eb; color: #93c5fd; font-weight: 700; }
.wz-step.done { border-bottom-color: #16a34a; color: #4ade80; }
.wz-num { display: inline-block; width: 18px; height: 18px; border-radius: 50%; background: rgba(255,255,255,.1); font-size: 9px; font-weight: 700; line-height: 18px; text-align: center; margin-right: 5px; }
.wz-step.active .wz-num { background: #2563eb; color: #fff; }
.wz-step.done .wz-num { background: #16a34a; color: #fff; }

/* Gate 카드 */
.gate-card { border-radius: 10px; padding: 14px 16px; margin: 12px 0; }
.gate-go   { background: rgba(22,163,74,.1);  border: 1px solid rgba(22,163,74,.3); }
.gate-hold { background: rgba(202,138,4,.1);  border: 1px solid rgba(202,138,4,.3); }
.gate-kill { background: rgba(220,38,38,.1);  border: 1px solid rgba(220,38,38,.3); }

/* 스테이지 진행 바 (상단) */
.stage-bar { display: flex; gap: 4px; overflow-x: auto; padding: 4px 0 12px; }
.stage-node { display: flex; flex-direction: column; align-items: center; min-width: 58px; cursor: pointer; }
.stage-circle { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; border: 2px solid; transition: .15s; }
.stage-done   .stage-circle { background: rgba(22,163,74,.15); border-color: #4ade80; color: #4ade80; }
.stage-active .stage-circle { background: rgba(37,99,235,.2); border-color: #60a5fa; color: #60a5fa; }
.stage-locked .stage-circle { background: rgba(30,41,59,.5); border-color: #334155; color: #64748b; }
.stage-kill   .stage-circle { background: rgba(127,29,29,.15); border-color: #f87171; color: #f87171; }
.stage-label  { font-size: 8.5px; margin-top: 3px; text-align: center; color: #94a3b8; max-width: 56px; line-height: 1.2; }
.stage-connector { flex: 1; height: 2px; background: rgba(51,65,85,.8); margin-top: 15px; min-width: 6px; }

/* BM 캔버스 */
.bm-block { background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.08); border-radius: 8px; padding: 10px 12px; min-height: 80px; }
.bm-title { font-size: 9px; font-weight: 700; color: rgba(255,255,255,.3); text-transform: uppercase; margin-bottom: 6px; letter-spacing: .04em; }

/* 컨텍스트 배너 */
.ctx-banner { background: rgba(30,41,59,.6); border: 1px solid rgba(51,65,85,.8); border-radius: 8px; padding: 8px 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 10px; font-size: 12px; }

/* 테마 — 미색 */
body[data-theme="cream"] .app-shell { background: #faf6f0; }
body[data-theme="cream"] .sidebar { background: #f0e9df; border-right-color: #ddd0bc; }
body[data-theme="cream"] .main-area { background: #faf6f0; }
body[data-theme="cream"] .ctx-bar { background: rgba(240,233,223,.9); border-bottom-color: rgba(0,0,0,.08); }
body[data-theme="cream"] .sb-brand-text { color: #1a0a00; }
body[data-theme="cream"] .sb-item { color: rgba(60,30,10,.6); }
body[data-theme="cream"] .sb-item:hover { background: rgba(0,0,0,.06); color: #1a0a00; }
body[data-theme="cream"] .sb-item.active { background: rgba(194,122,48,.15); color: #92400e; }
body[data-theme="cream"] .sb-stage { color: rgba(60,30,10,.5); }
body[data-theme="cream"] .sb-stage:hover { background: rgba(0,0,0,.05); }
body[data-theme="cream"] .sb-label { color: rgba(60,30,10,.25); }
body[data-theme="cream"] .sb-divider { border-color: rgba(0,0,0,.06); }
body[data-theme="cream"] .home-title { background: linear-gradient(135deg, #1c0a00 40%, #92400e 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
body[data-theme="cream"] .home-sub { color: rgba(60,30,10,.55); }
body[data-theme="cream"] .page-title { color: #1a0a00; }
body[data-theme="cream"] .page-sub { color: rgba(60,30,10,.5); }
body[data-theme="cream"] .input-wrap { background: rgba(255,255,255,.7); border-color: rgba(0,0,0,.12); }
body[data-theme="cream"] .kpi-card { background: rgba(255,255,255,.5); border-color: rgba(0,0,0,.07); }
body[data-theme="cream"] .kpi-card-val { color: #1a0a00; }
body[data-theme="cream"] .sg-card { background: rgba(255,255,255,.5); border-color: rgba(0,0,0,.07); }
body[data-theme="cream"] .sb-ctx { background: rgba(194,122,48,.1); border-color: rgba(194,122,48,.2); }
body[data-theme="cream"] .sb-ctx-name { color: #92400e; }

/* 테마 — 블랙 */
body[data-theme="black"] .app-shell { background: #000; }
body[data-theme="black"] .sidebar { background: #030303; border-right-color: rgba(255,255,255,.04); }
body[data-theme="black"] .main-area { background: #000; }
body[data-theme="black"] .ctx-bar { background: rgba(0,0,0,.8); border-bottom-color: rgba(255,255,255,.05); }
body[data-theme="black"] .kpi-card { background: rgba(255,255,255,.02); border-color: rgba(255,255,255,.05); }
body[data-theme="black"] .input-wrap { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.07); }

/* 배경 이미지 (bg-on) */
body.bg-on .main-area {
  background-image: radial-gradient(ellipse 80% 60% at 65% 25%, rgba(37,99,235,.1) 0%, transparent 60%), radial-gradient(ellipse 50% 40% at 15% 80%, rgba(124,58,237,.07) 0%, transparent 55%);
  background-attachment: fixed;
}
body.bg-on[data-theme="black"] .main-area {
  background-image: radial-gradient(ellipse 80% 60% at 65% 25%, rgba(37,99,235,.15) 0%, transparent 60%), radial-gradient(ellipse 50% 40% at 15% 80%, rgba(124,58,237,.1) 0%, transparent 55%);
}
body.bg-on[data-theme="cream"] .main-area {
  background-image: radial-gradient(ellipse 80% 60% at 65% 25%, rgba(194,122,48,.08) 0%, transparent 60%), radial-gradient(ellipse 50% 40% at 15% 80%, rgba(234,179,8,.06) 0%, transparent 55%);
}

/* 스크롤바 */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.1); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.2); }

/* ── Streamlit 버튼 정제 ── */
.stButton > button {
  background: rgba(255,255,255,.04) !important;
  border: 1px solid rgba(255,255,255,.1) !important;
  color: rgba(255,255,255,.65) !important;
  border-radius: 7px !important;
  font-size: 11.5px !important;
  font-weight: 500 !important;
  padding: 5px 12px !important;
  transition: all .12s !important;
  font-family: inherit !important;
}
.stButton > button:hover {
  background: rgba(255,255,255,.08) !important;
  border-color: rgba(255,255,255,.2) !important;
  color: #e2e8f0 !important;
}
.stButton > button[kind="primary"] {
  background: #2563eb !important;
  border-color: #2563eb !important;
  color: #fff !important;
}
.stButton > button[kind="primary"]:hover {
  background: #1d4ed8 !important;
  border-color: #1d4ed8 !important;
}
body[data-theme="cream"] .stButton > button {
  background: rgba(255,255,255,.6) !important;
  border-color: rgba(0,0,0,.1) !important;
  color: rgba(60,30,10,.7) !important;
}
body[data-theme="cream"] .stButton > button:hover {
  background: rgba(255,255,255,.9) !important;
  color: #1a0a00 !important;
}

/* ── Streamlit metric ── */
[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 800 !important; color: #f1f5f9 !important; }
[data-testid="stMetricLabel"] { font-size: 10px !important; font-weight: 600 !important; color: rgba(255,255,255,.35) !important; text-transform: uppercase !important; letter-spacing: .06em !important; }
[data-testid="stMetricDelta"] { font-size: 10px !important; }
[data-testid="metric-container"] { background: rgba(255,255,255,.03) !important; border: 1px solid rgba(255,255,255,.07) !important; border-radius: 12px !important; padding: 14px !important; }
body[data-theme="cream"] [data-testid="metric-container"] { background: rgba(255,255,255,.5) !important; border-color: rgba(0,0,0,.07) !important; }
body[data-theme="cream"] [data-testid="stMetricValue"] { color: #1a0a00 !important; }
body[data-theme="cream"] [data-testid="stMetricLabel"] { color: rgba(60,30,10,.4) !important; }

/* ═══════════════════════════════════════════
   IPInsight UI v2.1 — v0.dev 품질 강화 CSS
   ══════════════════════════════════════════ */

/* ── 사이드바 스테이지 게이트 강화 ── */
.sb-stage { border: 1px solid transparent; transition: background .12s, border-color .12s; }
.sb-stage:hover { background: rgba(255,255,255,.04) !important; border-color: rgba(255,255,255,.06); }
.sb-stage.active { background: rgba(37,99,235,.12) !important; border-color: rgba(37,99,235,.22) !important; }
.dot-go   { background: #4ade80 !important; box-shadow: 0 0 6px rgba(74,222,128,.6) !important; }
.dot-hold { background: #fbbf24 !important; box-shadow: 0 0 6px rgba(251,191,36,.5) !important; }
.dot-kill { background: #f87171 !important; box-shadow: 0 0 6px rgba(248,113,113,.5) !important; }
.dot-idle { background: rgba(255,255,255,.12) !important; }

/* ── BM Canvas 카드 ── */
.bm-card {
  background: #1a1d27;
  border: 1px solid rgba(255,255,255,.07);
  border-radius: 9px;
  padding: 11px 13px;
  min-height: 88px;
  transition: border-color .14s, transform .1s, box-shadow .14s;
}
.bm-card:hover {
  border-color: rgba(59,130,246,.3);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0,0,0,.3);
}
.bm-card.highlight {
  border-color: rgba(59,130,246,.35);
  background: rgba(37,99,235,.06);
}
.bm-card-hdr { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.bm-card-icon { font-size: 14px; }
.bm-card-title { font-size: 9px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: .06em; }
.bm-card-body { font-size: 10px; color: #64748b; line-height: 1.6; }
.bm-tag {
  display: inline-block; padding: 2px 7px;
  background: rgba(59,130,246,.1); color: #60a5fa;
  border: 1px solid rgba(59,130,246,.18);
  border-radius: 4px; font-size: 9px; font-weight: 500;
  margin: 2px 2px 0 0;
}
.bm-tag-green  { background: rgba(74,222,128,.08) !important; color: #4ade80 !important; border-color: rgba(74,222,128,.2) !important; }
.bm-tag-yellow { background: rgba(251,191,36,.08) !important; color: #fbbf24 !important; border-color: rgba(251,191,36,.2) !important; }
.bm-add { font-size: 9px; color: #334155; margin-top: 8px; cursor: pointer; border-top: 1px solid rgba(255,255,255,.04); padding-top: 6px; }

/* ── 상단 Stage Rail v2 ── */
.stage-rail-v2 {
  display: flex; align-items: center;
  padding: 9px 20px; overflow-x: auto;
  background: #0d0f18; border-bottom: 1px solid rgba(255,255,255,.05);
  gap: 0; scrollbar-width: none;
}
.stage-rail-v2::-webkit-scrollbar { display: none; }
.sr-node { display: flex; flex-direction: column; align-items: center; gap: 3px; flex-shrink: 0; cursor: pointer; padding: 0 6px; }
.sr-circle {
  width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 800; border: 1.5px solid;
  transition: all .15s;
}
.sr-circle.go     { background: rgba(74,222,128,.12);  border-color: #4ade80; color: #4ade80; }
.sr-circle.hold   { background: rgba(251,191,36,.1);   border-color: #fbbf24; color: #fbbf24; }
.sr-circle.kill   { background: rgba(248,113,113,.1);  border-color: #f87171; color: #f87171; }
.sr-circle.active { background: rgba(59,130,246,.18);  border-color: #3b82f6; color: #93c5fd; box-shadow: 0 0 12px rgba(59,130,246,.35); }
.sr-circle.idle   { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.1); color: #475569; }
.sr-text { font-size: 7px; color: #334155; white-space: nowrap; }
.sr-node.active .sr-text { color: #60a5fa; font-weight: 700; }
.sr-node.go .sr-text { color: #4ade80; }
.sr-connector { flex: 1; height: 1px; background: rgba(255,255,255,.06); min-width: 8px; max-width: 22px; margin-bottom: 11px; }

/* ── Context Banner v2 ── */
.ctx-banner-v2 {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 20px; background: #111420;
  border-bottom: 1px solid rgba(255,255,255,.04);
  flex-wrap: wrap;
}
.ctx-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 9px; border-radius: 99px;
  font-size: 9px; font-weight: 700; line-height: 1;
}
.ctx-chip-blue   { background: rgba(59,130,246,.12); color: #60a5fa; border: 1px solid rgba(59,130,246,.22); }
.ctx-chip-green  { background: rgba(74,222,128,.1);  color: #4ade80; border: 1px solid rgba(74,222,128,.2); }
.ctx-chip-yellow { background: rgba(251,191,36,.1);  color: #fbbf24; border: 1px solid rgba(251,191,36,.2); }
.ctx-chip-gray   { background: rgba(255,255,255,.06); color: #94a3b8; border: 1px solid rgba(255,255,255,.08); }
.ctx-tech-name   { font-size: 12px; font-weight: 600; color: #e2e8f0; }

/* ── Gate 결과 카드 v2 ── */
.gate-card-v2 {
  background: #1a1d27; border-radius: 10px;
  padding: 14px 18px; display: flex; align-items: center;
  justify-content: space-between; margin-top: 14px;
}
.gate-card-v2.go   { border: 1px solid rgba(74,222,128,.25); }
.gate-card-v2.hold { border: 1px solid rgba(251,191,36,.25); }
.gate-card-v2.kill { border: 1px solid rgba(248,113,113,.25); }
.gate-v2-score { font-size: 30px; font-weight: 800; letter-spacing: -1.5px; }
.gate-v2-score.go   { color: #4ade80; }
.gate-v2-score.hold { color: #fbbf24; }
.gate-v2-score.kill { color: #f87171; }
.gate-v2-label { font-size: 13px; font-weight: 700; }
.gate-v2-label.go   { color: #4ade80; }
.gate-v2-label.hold { color: #fbbf24; }
.gate-v2-label.kill { color: #f87171; }
.gate-v2-sub { font-size: 10px; color: #475569; margin-top: 2px; }

/* ── KPI 카드 v2 ── */
.kpi-v2 {
  background: #1a1d27; border: 1px solid rgba(255,255,255,.07);
  border-radius: 10px; padding: 14px 16px;
  transition: border-color .15s, transform .1s;
}
.kpi-v2:hover { border-color: rgba(255,255,255,.14); transform: translateY(-1px); }
.kpi-v2-label { font-size: 9px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 6px; }
.kpi-v2-value { font-size: 26px; font-weight: 800; color: #f1f5f9; letter-spacing: -.8px; line-height: 1; }
.kpi-v2-delta { font-size: 10px; color: #64748b; margin-top: 4px; }
.kpi-v2-delta.up   { color: #4ade80; }
.kpi-v2-delta.down { color: #f87171; }

/* ── 탭 강화 ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid rgba(255,255,255,.06) !important;
  gap: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 7px 7px 0 0 !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  color: #64748b !important;
  padding: 8px 16px !important;
  transition: all .12s !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: #e2e8f0 !important;
  background: rgba(59,130,246,.07) !important;
  border-bottom: 2px solid #3b82f6 !important;
}

/* ── 텍스트 입력 강화 ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
  background: #1a1d27 !important;
  border: 1px solid rgba(255,255,255,.09) !important;
  border-radius: 7px !important;
  color: #e2e8f0 !important;
  font-size: 12px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: rgba(59,130,246,.45) !important;
  box-shadow: 0 0 0 3px rgba(59,130,246,.1) !important;
}

/* ── Expander 강화 ── */
[data-testid="stExpander"] {
  background: #1a1d27 !important;
  border: 1px solid rgba(255,255,255,.07) !important;
  border-radius: 9px !important;
}

/* ── 섹션 헤더 강화 ── */
.sec-header-v2 {
  font-size: 11px; font-weight: 700; color: #475569;
  text-transform: uppercase; letter-spacing: .08em;
  display: flex; align-items: center; gap: 8px;
  margin: 16px 0 10px;
}
.sec-header-v2::after { content:''; flex:1; height:1px; background: rgba(255,255,255,.05); }

/* ── 인라인 상태 카드 ── */
.info-card  { background: rgba(59,130,246,.07); border: 1px solid rgba(59,130,246,.18); border-radius: 8px; padding: 10px 14px; font-size: 11px; color: #93c5fd; margin: 8px 0; }
.warn-card  { background: rgba(251,191,36,.07);  border: 1px solid rgba(251,191,36,.2);  border-radius: 8px; padding: 10px 14px; font-size: 11px; color: #fcd34d; margin: 8px 0; }
.ok-card    { background: rgba(74,222,128,.07);  border: 1px solid rgba(74,222,128,.2);  border-radius: 8px; padding: 10px 14px; font-size: 11px; color: #86efac; margin: 8px 0; }

/* ── 헤딩 강화 ── */
[data-testid="stHeadingContainer"] h1 {
  font-size: 22px !important; font-weight: 800 !important;
  color: #f1f5f9 !important; letter-spacing: -.5px !important;
  border-bottom: 1px solid rgba(255,255,255,.06) !important;
  padding-bottom: 10px !important; margin-bottom: 8px !important;
}
[data-testid="stHeadingContainer"] h2 { font-size: 16px !important; font-weight: 700 !important; color: #e2e8f0 !important; letter-spacing: -.2px !important; }
[data-testid="stHeadingContainer"] h3 { font-size: 13px !important; font-weight: 700 !important; color: #cbd5e1 !important; }
[data-testid="stCaptionContainer"] p  { font-size: 11px !important; color: #475569 !important; }

/* ── 메인 배경 v2 ── */
.stApp { background: #0b0d14 !important; }
body[data-theme="black"] .stApp { background: #030303 !important; }
body[data-theme="cream"] .stApp { background: #faf6f0 !important; }
body[data-theme="cream"] [data-testid="stHeadingContainer"] h1 { color: #1a0a00 !important; border-color: rgba(0,0,0,.08) !important; }

/* ── Home hero 타이틀 강화 ── */
.home-title {
  font-size: 38px !important; font-weight: 800 !important; letter-spacing: -2px !important;
  background: linear-gradient(135deg, #f1f5f9 20%, #60a5fa 60%, #a78bfa 100%) !important;
  -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important;
}

/* ── 구분선 ── */
[data-testid="stDivider"] hr { border-color: rgba(255,255,255,.06) !important; }

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
        {"id": "DEMO-001", "name": "스마트팜 수확량 예측 AI",  "trl": 4, "icon": "🌱", "project": "R&D 상용화"},
        {"id": "DEMO-002", "name": "차세대 리튬-황 배터리",     "trl": 6, "icon": "⚡", "project": "특허 포트폴리오"},
        {"id": "DEMO-003", "name": "AI 기반 암 진단 플랫폼",   "trl": 5, "icon": "🔬", "project": "스타트업 사업화"},
    ],
    "projects": [               # 프로젝트 목록
        {"name": "특허 포트폴리오",    "icon": "📋"},
        {"name": "기술 이전 프로젝트", "icon": "🏭"},
        {"name": "스타트업 사업화",    "icon": "🚀"},
        {"name": "R&D 상용화",        "icon": "🔬"},
    ],
    "input_mode": "text",
    "dark_mode": True,          # 하위 호환 (미사용)
    "theme": "dark",            # dark | black | cream
    "bg_on": True,              # 배경 이미지 온/오프
    "move_mode": None,          # 이동 대상 tech id
    "_active_proj": None,       # 선택된 프로젝트 필터
    "_show_new_proj": False,
    "gate_audit": [],           # Audit Trail: [{stage, gate, score, ts, tech_id}]
    "_ws_filter_gate": "전체",  # 워크스페이스 필터
    "_ws_saved_views": [],      # 저장된 뷰 목록 [{name, filter_gate}]
    "_ws_selected_stage": None, # 듀얼패널 선택 스테이지
    # Smart KPI Column Layout
    "_kpi_visible": ["completed", "avg_score", "kill_hold", "alerts"],
    # Bulk Operation
    "_bulk_selected": [],       # 선택된 tech id 목록
    "_bulk_action": None,
    # AI Agent Governance
    "_agent_log": [],           # [{ts, endpoint, params_preview, result_summary, approved}]
    # G3 시장성 분석 결과 캐시 (G5 자동인계용)
    "_g3_tam_result": None,
    "_g3_sam_result": None,
    "_g3_som_result": None,
    # G6 방법론별 결과 캐시
    "_g6_dcf_result": None,
    "_g6_cca_result": None,
    "_g6_roa_result": None,
    # G9 결과 캐시 (보고서 센터 연동용)
    "_g9_lic_result": None,
    "_g9_ir_result": None,
    "_g9_exit_result": None,
    "_rpt_prefill": None,   # G9→REPORTS 저장 시 prefill 데이터
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── 기본값 초기화 (active_stage) ──
if "_active_stage" not in st.session_state:
    st.session_state["_active_stage"] = None


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
    import datetime as _dt
    try:
        r = requests.post(f"{API_URL}{path}", json=body, headers=_headers(), timeout=90)
        result = None
        if r.status_code == 200:
            result = r.json()
        elif not silent:
            st.error(f"API {r.status_code}: {r.text[:300]}")
        # AI Agent Governance 로그 기록
        _log = st.session_state.get("_agent_log", [])
        params_preview = ", ".join(f"{k}={str(v)[:20]}" for k, v in list(body.items())[:3])
        result_summary = ""
        if result:
            gate = result.get("gate","")
            score = result.get("score","")
            result_summary = f"gate={gate} score={score}" if gate else str(list(result.keys())[:3])
        _log.append({
            "ts":      _dt.datetime.now().strftime("%H:%M:%S"),
            "date":    _dt.datetime.now().strftime("%m/%d"),
            "endpoint": path,
            "params":  params_preview,
            "status":  r.status_code,
            "result":  result_summary,
            "approved": None,   # None=미검토, True=승인, False=거부
        })
        st.session_state["_agent_log"] = _log[-50:]  # 최근 50건 유지
        return result
    except Exception as e:
        if not silent:
            st.error(f"서버 연결 실패: {e}")
    return None


# ── 공통 컴포넌트 ─────────────────────────────────────────────────

def render_stage_bar(current: int | None = None, show_toolbar: bool = True):
    """G0~G10 Stage Rail v2 — 전 화면 공통 렌더링"""
    gates = st.session_state.stage_gates
    html = '<div class="stage-rail-v2">'
    for n, (gid, name, icon) in STAGE_META.items():
        info = gates.get(n, {})
        gate = info.get("gate", "")
        if gate == "Kill":
            circle_cls = "kill"
            node_cls   = "kill"
        elif gate == "Go":
            circle_cls = "go"
            node_cls   = "go"
        elif gate == "Hold":
            circle_cls = "hold"
            node_cls   = ""
        elif n == current:
            circle_cls = "active"
            node_cls   = "active"
        else:
            circle_cls = "idle"
            node_cls   = ""
        score_txt = f"{info['score']:.0f}" if info.get("score") else gid
        html += f'<div class="sr-node {node_cls}" title="{name}">'
        html += f'<div class="sr-circle {circle_cls}">{score_txt}</div>'
        html += f'<div class="sr-text">{icon} {name}</div>'
        html += '</div>'
        if n < 10:
            html += '<div class="sr-connector"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
    if show_toolbar and current is not None:
        render_quick_toolbar(current)


def render_context_banner():
    """현재 기술 컨텍스트 배너 v2 — chip 스타일"""
    tid       = st.session_state.tech_id
    tname     = st.session_state.tech_name
    trl       = st.session_state.trl
    gates     = st.session_state.stage_gates
    completed = sum(1 for g in gates.values() if g.get("gate") == "Go")
    kills     = sum(1 for g in gates.values() if g.get("gate") == "Kill")
    holds     = sum(1 for g in gates.values() if g.get("gate") == "Hold")

    # TRL 색상
    trl_cls = "ctx-chip-green" if trl >= 7 else ("ctx-chip-yellow" if trl >= 4 else "ctx-chip-gray")
    # 전체 리스크 표시
    risk_cls  = "ctx-chip-yellow" if kills > 0 else "ctx-chip-green" if completed >= 3 else "ctx-chip-gray"
    risk_lbl  = f"⛔ Kill {kills}" if kills > 0 else (f"✅ Go {completed}" if completed > 0 else "🔵 진행 중")

    hold_html = f'<span class="ctx-chip ctx-chip-yellow">⏸ Hold {holds}</span>' if holds > 0 else ""
    st.markdown(
        f'<div class="ctx-banner-v2">'
        f'<span class="ctx-chip ctx-chip-blue">🔬 {tid}</span>'
        f'<span class="ctx-tech-name">{tname}</span>'
        f'<span class="ctx-chip {trl_cls}">TRL {trl}</span>'
        f'<span class="ctx-chip ctx-chip-gray">완료 {completed}/11</span>'
        f'<span class="ctx-chip {risk_cls}">{risk_lbl}</span>'
        f'{hold_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
    if trl and trl > 0:
        render_trl_gauge(min(max(int(trl), 1), 9))


def render_gate_card(gate: str, score: float, stage_label: str, next_actions: list[str]):
    """Gate 판정 → 다음 행동 카드 (v2.1 스타일)"""
    meta     = GATE_NEXT.get(gate, GATE_NEXT["Hold"])
    gate_cls = gate.lower() if gate in ("Go","Hold","Kill") else "hold"
    actions_html = "".join(f"<li style='margin-bottom:3px'>{a}</li>" for a in next_actions[:3])
    st.markdown(f"""
    <div class="gate-card-v2 {gate_cls}">
      <div>
        <div class="gate-v2-label {gate_cls}">{meta['icon']} {stage_label} — {meta['label']}</div>
        <div class="gate-v2-sub">다음 단계 권장 행동</div>
        <ul style="margin:8px 0 0;padding-left:18px;font-size:11px;color:#64748b">{actions_html}</ul>
      </div>
      <div class="gate-v2-score {gate_cls}">{score:.0f}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Quick Action Toolbar (Wellspring/Anaqua 스타일) ──────────────────
_STAGE_ACTIONS: dict[int, list[tuple[str, str, str]]] = {
    0:  [("🔍", "특허 검색",       "g1"),  ("📋", "IP 구조화",   "g1"),  ("🧪", "기술성 평가",  "g2")],
    1:  [("🧪", "기술성 평가",     "g2"),  ("🌐", "시장성 평가", "g3"),  ("📊", "클레임 분석",  "g1")],
    2:  [("🌐", "시장성 평가",     "g3"),  ("🤝", "고객 검증",   "g4"),  ("💼", "사업화전략",   "g5")],
    3:  [("🤝", "고객 검증",       "g4"),  ("💼", "사업화전략",  "g5"),  ("💰", "가치평가",     "g6")],
    4:  [("💼", "사업화전략",      "g5"),  ("💰", "가치평가",    "g6"),  ("🔬", "PoC 실증",     "g7")],
    5:  [("💰", "가치평가",        "g6"),  ("🔬", "PoC 실증",    "g7"),  ("📊", "PoB/MRL",      "g8")],
    6:  [("🔬", "PoC 실증",        "g7"),  ("📊", "PoB/MRL",     "g8"),  ("🤝", "거래·투자",    "g9")],
    7:  [("📊", "PoB/MRL",         "g8"),  ("🤝", "거래·투자",   "g9"),  ("📈", "성과관리",     "g10")],
    8:  [("🤝", "거래·투자",       "g9"),  ("📈", "성과관리",    "g10"), ("📄", "보고서",        "reports")],
    9:  [("📈", "성과관리",        "g10"), ("📄", "보고서",      "reports"),("🏠","워크스페이스","workspace")],
    10: [("📄", "보고서 생성",     "reports"), ("🏠", "워크스페이스", "workspace"), ("🔭", "신기술 발굴", "g0")],
}


def render_quick_toolbar(current_stage: int):
    """현재 스테이지 기반 다음 권장 액션 툴바 (Wellspring 스타일)"""
    actions = _STAGE_ACTIONS.get(current_stage, [])
    if not actions:
        return
    gate_info = st.session_state.stage_gates.get(current_stage, {})
    gate      = gate_info.get("gate", "")

    # Gate=Go 이면 다음 단계로 이동 CTA 강조
    label = "다음 권장 단계" if gate == "Go" else "관련 기능"
    chips = "".join(
        f'<span class="ctx-chip ctx-chip-{"blue" if i == 0 and gate == "Go" else "gray"}" '
        f'style="cursor:pointer;margin:2px">{ico} {name}</span>'
        for i, (ico, name, _) in enumerate(actions[:4])
    )
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;padding:7px 0 10px;'
        f'border-bottom:1px solid rgba(255,255,255,.05);margin-bottom:12px">'
        f'<span style="font-size:10px;color:#334155;font-weight:700">{label}</span>'
        f'{chips}</div>',
        unsafe_allow_html=True,
    )
    # 버튼 클릭 연동 (Streamlit 방식)
    cols = st.columns(len(actions[:4]))
    for i, (ico, name, page) in enumerate(actions[:4]):
        with cols[i]:
            if st.button(f"{ico} {name}", key=f"qa_{current_stage}_{i}", use_container_width=True):
                st.session_state.page = page
                st.rerun()


def _save_gate(stage_num: int, result: dict):
    """Gate 결과를 세션에 저장 + Audit Trail 기록"""
    import datetime as _dt
    gate  = result.get("gate", "")
    score = float(result.get("score", 0))
    st.session_state.stage_gates[stage_num] = {"gate": gate, "score": score}
    st.session_state.last_result = result
    st.session_state.last_stage  = stage_num
    # Audit Trail
    gid, name, icon = STAGE_META.get(stage_num, (f"G{stage_num}", "?", "?"))
    st.session_state.gate_audit.append({
        "ts":       _dt.datetime.now().strftime("%H:%M"),
        "date":     _dt.datetime.now().strftime("%m/%d"),
        "stage":    stage_num,
        "gid":      gid,
        "name":     name,
        "icon":     icon,
        "gate":     gate,
        "score":    score,
        "tech_id":  st.session_state.get("tech_id", ""),
        "tech_name":st.session_state.get("tech_name", ""),
    })


def render_trl_gauge(trl: int, show_label: bool = True):
    """TRL 1~9 시각화 게이지 (NASA/EU Horizon 기준)"""
    TRL_LABELS = {
        1: "기초 원리 관찰",   2: "기술 개념 정립",   3: "개념 실험 검증",
        4: "연구실 규모 실증", 5: "관련 환경 실증",   6: "실 환경 데모",
        7: "프로토타입 시연",  8: "시스템 완성·검증", 9: "임무 성공 실증",
    }
    TRL_PHASE = {(1,3): ("연구","#6366f1"), (4,6): ("개발","#3b82f6"), (7,9): ("상용화","#4ade80")}
    phase_lbl, phase_col = "연구", "#6366f1"
    for (lo, hi), (lbl, col) in TRL_PHASE.items():
        if lo <= trl <= hi:
            phase_lbl, phase_col = lbl, col

    bars = ""
    for i in range(1, 10):
        filled = i <= trl
        col = phase_col if filled else "rgba(255,255,255,.07)"
        bars += (
            f'<div style="flex:1;height:6px;background:{col};border-radius:2px;'
            f'transition:background .2s" title="TRL {i}"></div>'
        )
    label_html = (
        f'<div style="display:flex;justify-content:space-between;margin-top:4px">'
        f'<span style="font-size:9px;color:#475569">TRL {trl}/9</span>'
        f'<span style="font-size:9px;color:{phase_col};font-weight:700">{phase_lbl} 단계 — {TRL_LABELS.get(trl,"")}</span>'
        f'</div>'
    ) if show_label else ""
    st.markdown(
        f'<div style="margin:6px 0">'
        f'<div style="display:flex;gap:3px">{bars}</div>'
        f'{label_html}</div>',
        unsafe_allow_html=True,
    )


def render_output_doc(doc: dict | list | str | None, title: str = "", collapsed: bool = False):
    """API 출력 문서를 구조화된 카드로 렌더링 (st.json 대체)"""
    if doc is None:
        st.markdown('<div class="info-card">결과 없음</div>', unsafe_allow_html=True)
        return
    if isinstance(doc, str):
        st.markdown(f'<div class="ok-card">{doc}</div>', unsafe_allow_html=True)
        return
    if isinstance(doc, list):
        for i, item in enumerate(doc):
            render_output_doc(item, title=f"항목 {i+1}")
        return

    # dict 처리
    _SKIP = {"_version", "_source", "tech_id"}
    _GATE_COLORS = {"Go": "#4ade80", "Hold": "#fbbf24", "Kill": "#f87171"}

    def _tag(v: str, color: str = "#60a5fa") -> str:
        return f'<span class="bm-tag" style="background:rgba(255,255,255,.05);color:{color};border-color:rgba(255,255,255,.1)">{v}</span>'

    def _render_value(k: str, v):
        """단일 키-값 렌더링"""
        if k in _SKIP:
            return
        label = k.replace("_", " ").title()

        # 게이트 판정
        if k in ("gate", "Gate") and isinstance(v, str):
            color = _GATE_COLORS.get(v, "#94a3b8")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
                f'<span style="font-size:10px;color:#475569;min-width:90px">{label}</span>'
                f'<span class="bm-tag" style="background:rgba(255,255,255,.05);color:{color};'
                f'border-color:{color};font-size:10px;font-weight:700">{v}</span></div>',
                unsafe_allow_html=True,
            )
        # 숫자 점수
        elif k in ("score", "pcml_score", "scr_score", "trl", "mrl") and isinstance(v, (int, float)):
            col_a, col_b = st.columns([1, 3])
            col_a.metric(label, f"{v:.1f}" if isinstance(v, float) else v)
        # 리스트 → 태그 행
        elif isinstance(v, list):
            if not v:
                return
            tags = "".join(_tag(str(i)) for i in v[:8])
            more = f'<span style="font-size:9px;color:#334155"> +{len(v)-8}개</span>' if len(v) > 8 else ""
            st.markdown(
                f'<div style="margin:4px 0">'
                f'<div style="font-size:9px;color:#475569;font-weight:700;margin-bottom:3px">{label}</div>'
                f'<div>{tags}{more}</div></div>',
                unsafe_allow_html=True,
            )
        # 중첩 dict → expander
        elif isinstance(v, dict):
            with st.expander(f"📂 {label}", expanded=False):
                render_output_doc(v)
        # 긴 문자열 → caption
        elif isinstance(v, str) and len(v) > 80:
            st.markdown(
                f'<div style="margin:4px 0">'
                f'<div style="font-size:9px;color:#475569;font-weight:700;margin-bottom:2px">{label}</div>'
                f'<div style="font-size:11px;color:#94a3b8;line-height:1.6">{v}</div></div>',
                unsafe_allow_html=True,
            )
        # 짧은 값 → 인라인
        else:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
                f'<span style="font-size:9px;color:#475569;min-width:90px">{label}</span>'
                f'{_tag(str(v))}</div>',
                unsafe_allow_html=True,
            )

    # 요약/설명 필드 우선 표시
    priority_keys = ["summary", "description", "executive_summary", "conclusion",
                     "gate", "Gate", "score", "pcml_score", "scr_score"]
    shown = set()
    for k in priority_keys:
        if k in doc:
            _render_value(k, doc[k])
            shown.add(k)

    # 나머지 필드
    other_keys = [k for k in doc if k not in shown and k not in _SKIP]
    if other_keys:
        label_str = f"📋 {title} 상세" if title else "📋 전체 결과"
        with st.expander(label_str, expanded=not collapsed):
            for k in other_keys:
                _render_value(k, doc[k])


def render_pcml_chart(pcml_data: dict):
    """PCML v3.0 4도메인(기술·시장·사업·규제) 통합 시각화"""
    import streamlit.components.v1 as components
    import json as _json
    from collections import Counter

    # ── 4도메인에서 전체 노드/링크 수집 ──
    DOMAIN_LAYERS = [
        ("tech_graph_layer",       "기술",  "#3b82f6"),
        ("market_graph_layer",     "시장",  "#10b981"),
        ("business_graph_layer",   "사업",  "#f59e0b"),
        ("regulatory_graph_layer", "규제",  "#ef4444"),
    ]
    all_nodes, all_links, all_attrs = [], [], []
    for layer_key, _, _ in DOMAIN_LAYERS:
        layer = pcml_data.get(layer_key, {})
        all_nodes.extend(layer.get("nodes", []))
        all_links.extend(layer.get("links", []))
        all_attrs.extend(layer.get("attributes", []))

    # 도메인 간 링크도 포함
    all_links.extend(pcml_data.get("cross_domain_links", []))

    # v2.0 호환: claim_graph_layer가 있으면 병합
    clg = pcml_data.get("claim_graph_layer", {})
    for n in clg.get("nodes", []):
        if not n.get("domain"):
            n["domain"] = "technology"
        all_nodes.append(n)
    all_links.extend(clg.get("links", []))
    all_attrs.extend(clg.get("attributes", []))

    if not all_nodes:
        st.info("PCML 분석 결과가 없습니다. 위에서 분석을 먼저 실행하세요.")
        return

    # ── 통계 집계 ──
    domain_cnt    = Counter(n.get("domain", "technology") for n in all_nodes)
    node_type_cnt = Counter(n.get("node_type", "?") for n in all_nodes)
    elem_cls_cnt  = Counter(n.get("element_class", "?") for n in all_nodes)
    link_rel_cnt  = Counter(l.get("relation_type", "?") for l in all_links)
    attr_type_cnt = Counter(a.get("attr_type", "?") for a in all_attrs)

    # ── 스탯 카드: 4도메인 노드 수 ──
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("전체 노드", len(all_nodes), f"Core {elem_cls_cnt.get('Core',0)}개")
    c2.metric("🔵 기술", domain_cnt.get("technology", 0))
    c3.metric("🟢 시장", domain_cnt.get("market", 0))
    c4.metric("🟡 사업", domain_cnt.get("business", 0))
    c5.metric("🔴 규제", domain_cnt.get("regulatory", 0))

    qc = pcml_data.get("qc", {})
    cross_cnt = len(pcml_data.get("cross_domain_links", []))
    cx1, cx2, cx3 = st.columns(3)
    cx1.metric("도메인 간 링크", cross_cnt)
    cx2.metric("QC 등급", qc.get("qc_grade", "–"), f"신뢰 {qc.get('qc_confidence', 0)}%")
    cx3.metric("전체 링크", len(all_links))

    # ── D3 인터랙티브 그래프 ──
    nodes_js = _json.dumps(all_nodes)
    links_js = _json.dumps(all_links)
    attrs_js = _json.dumps(all_attrs)

    nt_labels = list(node_type_cnt.keys())[:10]
    nt_vals   = list(node_type_cnt.values())[:10]
    ec_labels = list(elem_cls_cnt.keys())
    ec_vals   = list(elem_cls_cnt.values())
    lr_labels = list(link_rel_cnt.keys())[:8]
    lr_vals   = list(link_rel_cnt.values())[:8]
    at_labels = list(attr_type_cnt.keys())[:8]
    at_vals   = list(attr_type_cnt.values())[:8]
    dom_labels = list(domain_cnt.keys())
    dom_vals   = list(domain_cnt.values())

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ margin:0; background:#0f1117; font-family:'Inter',sans-serif; color:#e2e8f0; }}
  .container {{ display:flex; gap:14px; padding:14px; height:620px; }}
  .graph-panel {{ flex:1.7; background:#1a1d27; border-radius:10px; border:1px solid rgba(255,255,255,.07); position:relative; overflow:hidden; }}
  .stats-panel {{ flex:1; display:flex; flex-direction:column; gap:8px; overflow-y:auto; }}
  .chart-box {{ background:#1a1d27; border:1px solid rgba(255,255,255,.07); border-radius:10px; padding:10px; }}
  .chart-title {{ font-size:10px; font-weight:700; color:rgba(255,255,255,.35); text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; }}
  .tooltip {{ position:absolute; background:#1e293b; border:1px solid rgba(255,255,255,.15); border-radius:8px; padding:8px 12px; font-size:11px; pointer-events:none; opacity:0; transition:.15s; max-width:210px; z-index:100; }}
  .legend {{ position:absolute; bottom:10px; left:10px; font-size:9px; background:rgba(15,17,23,.8); padding:6px 8px; border-radius:6px; }}
  .legend-item {{ display:flex; align-items:center; gap:5px; margin-bottom:3px; }}
  .legend-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
  .domain-filter {{ position:absolute; top:8px; right:10px; display:flex; gap:4px; }}
  .domain-btn {{ font-size:9px; padding:2px 7px; border-radius:10px; cursor:pointer; border:1px solid rgba(255,255,255,.2); background:transparent; color:#cbd5e1; }}
  .domain-btn.active {{ border-color:#fff; background:rgba(255,255,255,.15); }}
  svg text {{ font-family:'Inter',sans-serif; }}
  .node circle {{ stroke-width:2; cursor:pointer; transition:.15s; }}
  .node circle:hover {{ stroke-width:3; filter:brightness(1.3); }}
  .link line {{ stroke-opacity:.6; }}
  .link-label {{ font-size:7px; fill:rgba(255,255,255,.35); }}
</style>
</head>
<body>
<div class="container">
  <div class="graph-panel" id="graph">
    <div id="tooltip" class="tooltip"></div>
    <div style="position:absolute;top:10px;left:12px;font-size:11px;font-weight:700;color:rgba(255,255,255,.5)">
      PCML v3.0 — 4도메인 통합 그래프
    </div>
    <div class="domain-filter" id="domFilter">
      <button class="domain-btn active" data-domain="all" title="전체 4도메인">전체</button>
      <button class="domain-btn" data-domain="technology" style="border-color:#3b82f6;color:#3b82f6" title="기술 + 특허(PatentRight)">기술·특허</button>
      <button class="domain-btn" data-domain="market" style="border-color:#10b981;color:#10b981" title="시장 + 고객검증(Validation)">시장·검증</button>
      <button class="domain-btn" data-domain="business" style="border-color:#f59e0b;color:#f59e0b" title="사업 + 투자(Investor·FundingRound)">사업·투자</button>
      <button class="domain-btn" data-domain="regulatory" style="border-color:#ef4444;color:#ef4444" title="규제 + 정책(Policy)">규제·정책</button>
    </div>
    <svg id="main-svg" width="100%" height="100%"></svg>
    <div class="legend" id="legend"></div>
  </div>
  <div class="stats-panel">
    <div class="chart-box">
      <div class="chart-title">도메인별 노드</div>
      <svg id="dom-chart" width="100%" height="70"></svg>
    </div>
    <div class="chart-box">
      <div class="chart-title">Node 유형</div>
      <svg id="nt-chart" width="100%" height="80"></svg>
    </div>
    <div class="chart-box">
      <div class="chart-title">Element Class</div>
      <svg id="ec-chart" width="100%" height="70"></svg>
    </div>
    <div class="chart-box">
      <div class="chart-title">Link 관계</div>
      <svg id="lr-chart" width="100%" height="90"></svg>
    </div>
    <div class="chart-box">
      <div class="chart-title">Attribute 유형</div>
      <svg id="at-chart" width="100%" height="90"></svg>
    </div>
  </div>
</div>

<script>
const rawNodes = {nodes_js};
const rawLinks = {links_js};
const rawAttrs = {attrs_js};

// 도메인 색상
const DOMAIN_COLORS = {{
  technology:"#3b82f6", market:"#10b981",
  business:"#f59e0b",   regulatory:"#ef4444"
}};
// Node 유형 색상 (도메인 우선, 유형 보조)
const NODE_TYPE_COLORS = {{
  // 기술 도메인 (파란 계열)
  Physical:"#3b82f6",Logical:"#8b5cf6",Data:"#06b6d4",Actor:"#f59e0b",Step:"#a78bfa",TechSpec:"#38bdf8",Material:"#64748b",
  PatentRight:"#1d4ed8",  // 특허권 — 진한 파랑 (기술 중에서도 IP자산 강조)
  // 시장 도메인 (초록 계열)
  MarketSegment:"#10b981",Customer:"#34d399",Competitor:"#f87171",Product:"#4ade80",Channel:"#86efac",Pricing:"#fbbf24",Trend:"#6ee7b7",
  Validation:"#059669",   // 고객검증 — 진한 초록 (검증 완료 강조)
  // 사업 도메인 (황금 계열)
  ValueProp:"#f59e0b",Revenue:"#fcd34d",Cost:"#fb923c",Partner:"#fdba74",Activity:"#fde68a",Resource:"#fef3c7",CustomerSegment:"#d97706",UnitEcon:"#b45309",
  Investor:"#7c3aed",     // 투자자 — 보라 (사업 도메인 내 자본 흐름 차별화)
  FundingRound:"#6d28d9", // 투자 라운드 — 진한 보라
  // 규제 도메인 (빨간 계열)
  Regulation:"#ef4444",Certification:"#f87171",Authority:"#fca5a5",Jurisdiction:"#fecaca",Penalty:"#dc2626",Compliance:"#fee2e2",RegulatoryPath:"#b91c1c",
  Policy:"#0891b2",       // 정책 — 청록 (규제 도메인이지만 지원·혜택 성격 강조)
}};
const ELEM_COLORS = {{Core:"#fff",Supporting:"#94a3b8",Peripheral:"#475569"}};
const LINK_COLORS = {{
  controls:"#f87171",inputs:"#60a5fa",outputs:"#4ade80",includes:"#a78bfa",has:"#34d399",
  performs:"#fb923c",based_on:"#c084fc",depends_on:"#f472b6",transmits:"#38bdf8",
  targets:"#10b981",competes_with:"#ef4444",serves:"#34d399",distributed_via:"#4ade80",
  enables:"#f59e0b",generates:"#fcd34d",partnered_with:"#fdba74",drives:"#fb923c",
  regulated_by:"#ef4444",requires_cert:"#f87171",blocks:"#dc2626",operates_in:"#fca5a5",
  commercializes:"#8b5cf6",protected_by:"#a78bfa",valued_at:"#c084fc",
  default:"#475569"
}};

// ── 메인 그래프 ────────────────────────────────────────────────
const svgEl  = d3.select("#main-svg");
const gPanel = document.getElementById("graph");
const W = gPanel.clientWidth || 640;
const H = gPanel.clientHeight || 580;

const g = svgEl.append("g");
const zoom = d3.zoom().scaleExtent([0.2,4]).on("zoom", e => g.attr("transform", e.transform));
svgEl.call(zoom);

let activeFilter = "all";
const attrByTarget = {{}};
rawAttrs.forEach(a => {{
  if (!attrByTarget[a.target_id]) attrByTarget[a.target_id] = [];
  attrByTarget[a.target_id].push(a);
}});

// 화살표 마커
const defs = svgEl.append("defs");
[...new Set(rawLinks.map(l=>l.relation_type||"default"))].forEach(rel => {{
  const col = LINK_COLORS[rel]||LINK_COLORS.default;
  defs.append("marker").attr("id",`arrow-${{rel}}`)
    .attr("viewBox","0 -4 8 8").attr("refX",20).attr("refY",0)
    .attr("markerWidth",5).attr("markerHeight",5).attr("orient","auto")
    .append("path").attr("d","M0,-4L8,0L0,4").attr("fill",col).attr("opacity",.7);
}});

function buildGraph(filterDomain) {{
  g.selectAll("*").remove();
  const visNodes = filterDomain==="all" ? rawNodes : rawNodes.filter(n=>n.domain===filterDomain);
  const visIds   = new Set(visNodes.map(n=>n.node_id||n.id));
  const visLinks = rawLinks.filter(l => visIds.has(l.src_node||l.source) && visIds.has(l.dst_node||l.target));

  const simNodes = visNodes.map(n=>({{...n, id:n.node_id||n.id}}));
  const simLinks = visLinks.map(l=>({{...l, source:l.src_node||l.source, target:l.dst_node||l.target}}));

  const sim = d3.forceSimulation(simNodes)
    .force("link", d3.forceLink(simLinks).id(d=>d.id).distance(85))
    .force("charge", d3.forceManyBody().strength(-200))
    .force("center", d3.forceCenter(W/2, H/2))
    .force("collide", d3.forceCollide(24));

  const linkG = g.append("g").selectAll(".link").data(simLinks).join("g").attr("class","link");
  const linkLine = linkG.append("line")
    .attr("stroke", d=>LINK_COLORS[d.relation_type]||LINK_COLORS.default)
    .attr("stroke-width", d=>d.element_class==="Core"?2:1)
    .attr("stroke-dasharray", d=>d.element_class==="Peripheral"?"4,3":null)
    .attr("marker-end", d=>`url(#arrow-${{d.relation_type||"default"}})`);

  linkG.append("text").attr("class","link-label").attr("text-anchor","middle")
    .text(d=>d.relation_type||"");

  const nodeG = g.append("g").selectAll(".node").data(simNodes).join("g").attr("class","node")
    .call(d3.drag()
      .on("start",(e,d)=>{{if(!e.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y;}})
      .on("drag", (e,d)=>{{d.fx=e.x;d.fy=e.y;}})
      .on("end",  (e,d)=>{{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}}));

  const radius = d=>d.element_class==="Core"?15:d.element_class==="Supporting"?11:8;

  // 도메인 링 + 노드 원
  nodeG.append("circle")
    .attr("r", d=>radius(d)+3)
    .attr("fill","none")
    .attr("stroke", d=>DOMAIN_COLORS[d.domain]||"#475569")
    .attr("stroke-width",1.5).attr("opacity",.5);
  nodeG.append("circle")
    .attr("r", radius)
    .attr("fill", d=>NODE_TYPE_COLORS[d.node_type]||DOMAIN_COLORS[d.domain]||"#64748b")
    .attr("fill-opacity", d=>d.element_class==="Core"?0.92:0.55)
    .attr("stroke", d=>d.element_class==="Core"?"#fff":"#64748b")
    .attr("stroke-width",d=>d.element_class==="Core"?1.5:0.8)
    .on("mouseover", function(e,d) {{
      const aList = attrByTarget[d.node_id||d.id]||[];
      const aHtml = aList.slice(0,4).map(a=>`<div style="font-size:9px;color:#94a3b8">📌 ${{a.attr_type}}: ${{String(a.value||"").slice(0,40)}}</div>`).join("");
      const tip = document.getElementById("tooltip");
      tip.innerHTML = `
        <div style="font-weight:700;color:#f1f5f9;margin-bottom:3px">${{d.label||d.node_id}}</div>
        <div style="font-size:9px;margin-bottom:3px">
          <span style="background:${{DOMAIN_COLORS[d.domain]||"#475569"}};padding:1px 5px;border-radius:8px;font-size:8px">${{d.domain||"?"}}</span>
          <span style="color:#93c5fd;margin-left:4px">${{d.node_type||"?"}}</span>
          · <span style="color:#94a3b8">${{d.element_class||"?"}}</span>
        </div>
        ${{aHtml}}
      `;
      tip.style.opacity=1; tip.style.left=(e.offsetX+14)+"px"; tip.style.top=(e.offsetY-10)+"px";
    }})
    .on("mouseout",()=>{{document.getElementById("tooltip").style.opacity=0;}});

  nodeG.append("text").attr("text-anchor","middle").attr("dy","3px")
    .style("font-size","7px").style("font-weight","700").style("fill","#fff")
    .style("pointer-events","none").text(d=>(d.node_id||"").replace(/^[A-Z]+-/,""));
  nodeG.append("text").attr("text-anchor","middle").attr("dy","22px")
    .style("font-size","8px").style("fill","#94a3b8").style("pointer-events","none")
    .text(d=>{{const l=d.label||"";return l.length>12?l.slice(0,11)+"…":l;}});

  sim.on("tick",()=>{{
    linkLine
      .attr("x1",d=>d.source.x).attr("y1",d=>d.source.y)
      .attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
    g.selectAll(".link text")
      .attr("x",d=>(d.source.x+d.target.x)/2)
      .attr("y",d=>(d.source.y+d.target.y)/2-4);
    nodeG.attr("transform",d=>`translate(${{d.x}},${{d.y}})`);
  }});
}}

buildGraph("all");

// 도메인 필터 버튼
document.querySelectorAll(".domain-btn").forEach(btn=>{{
  btn.addEventListener("click",()=>{{
    document.querySelectorAll(".domain-btn").forEach(b=>b.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.domain;
    buildGraph(activeFilter);
  }});
}});

// 레전드
const legend = document.getElementById("legend");
legend.innerHTML = Object.entries(DOMAIN_COLORS).map(([d,c])=>
  `<div class="legend-item"><div class="legend-dot" style="background:${{c}}"></div><span style="color:#94a3b8;font-size:8px">${{{{technology:"기술",market:"시장",business:"사업",regulatory:"규제"}}[d]||d}}</span></div>`
).join("");

// ── 미니 바 차트 ──────────────────────────────────────────────
function miniBar(svgId, labels, vals, colors) {{
  const s = d3.select(`#${{svgId}}`);
  const W2 = (s.node().parentElement?.clientWidth||220) - 20;
  const H2 = parseInt(s.attr("height"))||80;
  const max = d3.max(vals)||1;
  if(!labels.length) return;
  const bw = Math.max(4, W2/labels.length-3);
  s.attr("width",W2);
  labels.forEach((lbl,i)=>{{
    const x  = i*(bw+3)+1;
    const bh = Math.max(2,(vals[i]/max)*(H2-22));
    const col= Array.isArray(colors)?(colors[i%colors.length]):(colors[lbl]||"#475569");
    s.append("rect").attr("x",x).attr("y",H2-bh-18).attr("width",bw).attr("height",bh)
      .attr("fill",col).attr("rx",2).attr("opacity",.85);
    s.append("text").attr("x",x+bw/2).attr("y",H2-2).attr("text-anchor","middle")
      .style("font-size","7px").style("fill","#64748b")
      .text(lbl.length>8?lbl.slice(0,7)+"…":lbl);
    s.append("text").attr("x",x+bw/2).attr("y",H2-bh-20).attr("text-anchor","middle")
      .style("font-size","8px").style("fill","#e2e8f0").style("font-weight","700")
      .text(vals[i]);
  }});
}}

const DOM_LABELS = {_json.dumps(dom_labels)};
const DOM_VALS   = {_json.dumps(dom_vals)};
const NT_LABELS  = {_json.dumps(nt_labels)};
const NT_VALS    = {_json.dumps(nt_vals)};
const EC_LABELS  = {_json.dumps(ec_labels)};
const EC_VALS    = {_json.dumps(ec_vals)};
const LR_LABELS  = {_json.dumps(lr_labels)};
const LR_VALS    = {_json.dumps(lr_vals)};
const AT_LABELS  = {_json.dumps(at_labels)};
const AT_VALS    = {_json.dumps(at_vals)};

setTimeout(()=>{{
  miniBar("dom-chart", DOM_LABELS, DOM_VALS, ["#3b82f6","#10b981","#f59e0b","#ef4444"]);
  miniBar("nt-chart",  NT_LABELS,  NT_VALS,  Object.values(NODE_TYPE_COLORS));
  miniBar("ec-chart",  EC_LABELS,  EC_VALS,  {{Core:"#fff",Supporting:"#94a3b8",Peripheral:"#475569"}});
  miniBar("lr-chart",  LR_LABELS,  LR_VALS,  Object.values(LINK_COLORS));
  miniBar("at-chart",  AT_LABELS,  AT_VALS,  ["#fbbf24","#06b6d4","#3b82f6","#8b5cf6","#10b981","#f59e0b","#ef4444","#94a3b8"]);
}}, 120);
</script>
</body>
</html>
"""
    components.html(html, height=660, scrolling=False)


# ── 공통 앱 사이드바 ──────────────────────────────────────────────
def render_app_sidebar(api_ok: bool = True):
    """모든 페이지에서 공통으로 사용하는 좌측 사이드바"""
    theme   = st.session_state.get("theme", "dark")
    bg_on   = st.session_state.get("bg_on", True)
    page    = st.session_state.page
    gates   = st.session_state.stage_gates
    tid     = st.session_state.get("tech_id", "")
    tname   = st.session_state.get("tech_name", "")
    trl     = st.session_state.get("trl", 4)

    # ── 브랜드 ──
    st.markdown(
        "<div class='sb-brand'>"
        "<span class='sb-brand-icon'>🔬</span>"
        "<div><div class='sb-brand-text'>IPInsight</div>"
        "<div class='sb-brand-sub'>기술사업화 Agent OS</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── 테마 & 배경 토글 ──
    tc1, tc2, tc3, tc4 = st.columns(4)
    with tc1:
        if st.button("⬛", key="sb_th_black", help="검정"):
            st.session_state.theme = "black"; st.rerun()
    with tc2:
        if st.button("🌙", key="sb_th_dark", help="다크"):
            st.session_state.theme = "dark"; st.rerun()
    with tc3:
        if st.button("☀️", key="sb_th_cream", help="미색"):
            st.session_state.theme = "cream"; st.rerun()
    with tc4:
        bg_icon = "🌅" if bg_on else "🌫️"
        if st.button(bg_icon, key="sb_bg", help="배경 ON/OFF"):
            st.session_state.bg_on = not bg_on; st.rerun()

    # ── 현재 기술 컨텍스트 ──
    if tname:
        st.markdown(
            f"<div class='sb-ctx'>"
            f"<div class='sb-ctx-name'>🔬 {tname[:24]}</div>"
            f"<div class='sb-ctx-meta'>TRL {trl} · {tid or '–'}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── 새 분석 버튼 ──
    if st.button("✏️ 새 기술 분석", use_container_width=True, type="primary", key="sb_new"):
        st.session_state.tech_id = ""
        st.session_state.tech_name = ""
        st.session_state.trl = 4
        st.session_state.stage_gates = {}
        st.session_state.page = "home"
        st.rerun()

    # ── Stage Gate 레일 (G0~G10) ──
    st.markdown("<div class='sb-label'>Stage Gates</div>", unsafe_allow_html=True)

    # MECE: G0~G10 각 Stage는 전용 페이지로 1:1 매핑
    STAGE_PAGE = {
        0: "g0",  1: "g1",  2: "g2",  3: "g3",
        4: "g4",  5: "g5",  6: "g6",  7: "g7",
        8: "g8",  9: "g9",  10: "g10",
    }
    for n, (gid, sname, icon) in STAGE_META.items():
        info = gates.get(n, {})
        gate = info.get("gate", "")
        dot_cls = {"Go":"dot-go","Hold":"dot-hold","Kill":"dot-kill"}.get(gate,"dot-idle")
        gate_short = {"Go":"✓","Hold":"⏸","Kill":"✕"}.get(gate,"")
        target_page = STAGE_PAGE.get(n, "workspace")
        is_active = (page == target_page and st.session_state.get("_active_stage") == n)
        gate_color = '#4ade80' if gate=='Go' else '#fbbf24' if gate=='Hold' else '#f87171' if gate=='Kill' else 'transparent'
        st.markdown(
            f"<div class='sb-stage{' active' if is_active else ''}'>"
            f"<span class='sb-dot {dot_cls}'></span>"
            f"<span class='sb-stage-gid'>{gid}</span>"
            f"<span style='flex:1'>{icon} {sname}</span>"
            f"<span style='font-size:9px;color:{gate_color}'>{gate_short}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(f"{gid} {sname}", key=f"sb_stage_{n}", help=f"G{n} {sname}", use_container_width=True):
            st.session_state._active_stage = n
            st.session_state.page = target_page
            st.rerun()

    # ── 횡단 도구 (Cross-Cutting) — Stage가 아닌 것만 ──
    st.markdown("<hr class='sb-divider'>", unsafe_allow_html=True)
    st.markdown("<div class='sb-label'>횡단 도구</div>", unsafe_allow_html=True)

    cross_items = [
        ("🏠", "워크스페이스", "workspace"),
        ("📄", "보고서 센터",  "reports"),
        ("⚙️", "관리자 콘솔",  "admin"),
    ]
    for icon, label, pg in cross_items:
        active_cls = " active" if page == pg else ""
        st.markdown(
            f"<div class='sb-item{active_cls}'>"
            f"<span class='sb-item-icon'>{icon}</span>"
            f"<span class='sb-item-label'>{label}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(f"{icon} {label}", key=f"sb_cross_{pg}", help=label, use_container_width=True):
            st.session_state.page = pg; st.rerun()

    # ── API 상태 & 로그아웃 ──
    status_cls = "" if api_ok else " off"
    st.markdown(
        f"<div class='sb-status'>"
        f"<span class='status-dot{status_cls}'></span>"
        f"{'API 연결' if api_ok else 'API 오프라인'}"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.session_state.get("token"):
        if st.button("로그아웃", use_container_width=True, key="sb_logout"):
            st.session_state.token = ""; st.rerun()
    else:
        if st.button("🔐 로그인", use_container_width=True, key="sb_login"):
            st.session_state.page = "admin"; st.rerun()


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

    # ── 테마/배경 JS ──
    theme  = st.session_state.get("theme", "dark")
    bg_on  = st.session_state.get("bg_on", True)
    st.markdown(
        f"<script>"
        f"document.body.setAttribute('data-theme','{theme}');"
        f"document.body.classList.{'add' if theme=='cream' else 'remove'}('light-mode');"
        f"document.body.classList.{'add' if bg_on else 'remove'}('bg-on');"
        f"</script>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        render_app_sidebar(api_ok)

    # ── 프로젝트 섹션 (사이드바 하단 추가) ──
    with st.sidebar:
        proj_col, new_proj_col = st.columns([3, 1])
        with proj_col:
            st.markdown(
                "<p style='font-size:10px;font-weight:700;color:#555;"
                "text-transform:uppercase;letter-spacing:.08em;"
                "padding:14px 4px 4px;margin:0'>프로젝트</p>",
                unsafe_allow_html=True,
            )
        with new_proj_col:
            st.markdown("<div style='padding-top:12px'>", unsafe_allow_html=True)
            if st.button("＋", key="new_project_btn", help="새 프로젝트 생성"):
                st.session_state["_show_new_proj"] = True
            st.markdown("</div>", unsafe_allow_html=True)

        # 새 프로젝트 생성 폼
        if st.session_state.get("_show_new_proj"):
            with st.form("new_proj_form", clear_on_submit=True):
                new_proj_name = st.text_input("프로젝트명", placeholder="예: AI 헬스케어 특허", label_visibility="collapsed")
                new_proj_icon = st.selectbox("아이콘", ["📋","🏭","🚀","🔬","💡","🌐","🤝","📊"], label_visibility="collapsed")
                col_ok, col_cancel = st.columns(2)
                with col_ok:
                    submitted = st.form_submit_button("만들기", use_container_width=True, type="primary")
                with col_cancel:
                    cancelled = st.form_submit_button("취소", use_container_width=True)
            if submitted and new_proj_name.strip():
                st.session_state.projects.append({"name": new_proj_name.strip(), "icon": new_proj_icon})
                st.session_state["_show_new_proj"] = False
                st.rerun()
            if cancelled:
                st.session_state["_show_new_proj"] = False
                st.rerun()

        # 프로젝트 목록 (클릭으로 필터)
        active_proj = st.session_state.get("_active_proj")
        for proj in st.session_state.projects:
            is_active = active_proj == proj["name"]
            count = sum(1 for t in st.session_state.recent_techs if t.get("project") == proj["name"])
            label = f"{proj['icon']} {proj['name']}" + (f"  [{count}]" if count else "")
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"proj_{proj['name']}", use_container_width=True, type=btn_type):
                st.session_state["_active_proj"] = None if is_active else proj["name"]
                st.rerun()

        # ── 최근 분석 섹션 (Claude 스타일 소형 목록) ──
        st.markdown(
            "<p style='font-size:10px;font-weight:700;color:#555;"
            "text-transform:uppercase;letter-spacing:.08em;"
            "padding:14px 4px 4px;margin:0'>최근 분석</p>",
            unsafe_allow_html=True,
        )

        # 이동 모드 안내
        move_id = st.session_state.get("move_mode")
        if move_id:
            target_tech = next((t for t in st.session_state.recent_techs if t["id"] == move_id), None)
            if target_tech:
                st.markdown(
                    f"<div style='font-size:10px;color:#60a5fa;padding:4px 8px;background:#1e3a5f;"
                    f"border-radius:5px;margin:2px 4px'>📦 <b>{target_tech['name'][:12]}</b> 이동 중...</div>",
                    unsafe_allow_html=True,
                )
                proj_names = [p["name"] for p in st.session_state.projects]
                sel_proj = st.selectbox("이동할 프로젝트", proj_names, key="move_proj_sel")
                col_mv, col_cx = st.columns(2)
                with col_mv:
                    if st.button("이동", key="do_move", use_container_width=True, type="primary"):
                        for t in st.session_state.recent_techs:
                            if t["id"] == move_id:
                                t["project"] = sel_proj
                        st.session_state.move_mode = None
                        st.rerun()
                with col_cx:
                    if st.button("취소", key="cancel_move", use_container_width=True):
                        st.session_state.move_mode = None
                        st.rerun()

        # ── Bulk Operation 모드 토글 ─────────────────────────
        bulk_mode = st.session_state.get("_bulk_mode", False)
        brow1, brow2 = st.columns([3, 1])
        with brow1:
            if st.button("☑ 일괄 선택" if not bulk_mode else "✕ 선택 취소",
                         key="sb_bulk_toggle", use_container_width=True):
                st.session_state["_bulk_mode"]     = not bulk_mode
                st.session_state["_bulk_selected"] = []
                st.rerun()
        with brow2:
            if bulk_mode and st.session_state.get("_bulk_selected"):
                cnt = len(st.session_state["_bulk_selected"])
                st.markdown(f'<span class="bm-tag bm-tag-green">{cnt}개 선택</span>',
                            unsafe_allow_html=True)

        # 일괄 액션 바 (선택 항목 있을 때만)
        if bulk_mode and st.session_state.get("_bulk_selected"):
            sel_ids = st.session_state["_bulk_selected"]
            st.markdown('<div class="info-card" style="padding:8px">', unsafe_allow_html=True)
            ba1, ba2, ba3 = st.columns(3)
            if ba1.button("📄 일괄 보고서", key="bulk_report", use_container_width=True):
                with st.spinner(f"{len(sel_ids)}개 기술 보고서 생성 중…"):
                    for tid in sel_ids:
                        tech = next((t for t in st.session_state.recent_techs if t["id"] == tid), None)
                        if tech:
                            api_post("/reports/pipeline", {
                                "tech_id": tid, "tech_name": tech.get("name",""),
                                "trl": tech.get("trl", 4), "tier": "LITE",
                            })
                st.success(f"✅ {len(sel_ids)}개 보고서 생성 완료")
                st.session_state["_bulk_selected"] = []
            if ba2.button("🗺️ 포트폴리오 맵", key="bulk_map", use_container_width=True):
                st.session_state.page = "workspace"; st.rerun()
            if ba3.button("🗑 선택 해제", key="bulk_clear", use_container_width=True):
                st.session_state["_bulk_selected"] = []
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # 최근 분석 목록 (프로젝트 필터 적용)
        filtered = [
            t for t in st.session_state.recent_techs
            if active_proj is None or t.get("project") == active_proj
        ]
        for tech in filtered:
            proj_label = tech.get("project", "")
            name_short = tech["name"][:18] + ("…" if len(tech["name"]) > 18 else "")
            tid = tech["id"]

            if bulk_mode:
                # 체크박스 행
                sel_list = st.session_state.get("_bulk_selected", [])
                checked = tid in sel_list
                cb_col, name_col = st.columns([1, 5])
                with cb_col:
                    if st.checkbox("", value=checked, key=f"bulk_cb_{tid}"):
                        if tid not in sel_list:
                            sel_list.append(tid)
                            st.session_state["_bulk_selected"] = sel_list
                    else:
                        if tid in sel_list:
                            sel_list.remove(tid)
                            st.session_state["_bulk_selected"] = sel_list
                with name_col:
                    trl_col = "#4ade80" if tech["trl"] >= 7 else "#fbbf24" if tech["trl"] >= 4 else "#94a3b8"
                    st.markdown(
                        f'<div style="padding:4px 0;font-size:11px;color:#cbd5e1">'
                        f'{tech["icon"]} {name_short}'
                        f'<span style="font-size:9px;color:{trl_col};margin-left:6px">TRL {tech["trl"]}</span></div>',
                        unsafe_allow_html=True)
            else:
                # 기존 버튼 행
                c1, c2 = st.columns([5, 1])
                with c1:
                    if st.button(f"{tech['icon']} {name_short}", key=f"recent_{tid}",
                                 use_container_width=True, help=proj_label):
                        st.session_state.tech_id   = tid
                        st.session_state.tech_name = tech["name"]
                        st.session_state.trl       = tech["trl"]
                        st.session_state.page      = "workspace"
                        st.rerun()
                with c2:
                    if st.button("↗", key=f"move_{tid}", help="프로젝트로 이동"):
                        st.session_state.move_mode = tid
                        st.rerun()

    # ──────────── 메인 콘텐츠 (3단계 위저드) ────────────
    # 역할 명확화 배너: HOME = 신규 기술 등록 전용
    st.markdown(
        "<div style='display:flex;align-items:center;gap:10px;padding:8px 14px;"
        "background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2);"
        "border-radius:8px;margin-bottom:12px;font-size:12px;color:#a5b4fc'>"
        "📌 <b>HOME</b>은 <b>신규 기술 등록 전용</b>입니다. "
        "기존 기술의 심층 분석·비교·보고서는 "
        "<b>워크스페이스</b> 또는 각 <b>G-Stage 페이지</b>를 사용하세요.</div>",
        unsafe_allow_html=True,
    )
    step = st.session_state.home_step

    # ── 스텝 진행 표시 ──────────────────────────────────────────
    STEPS = [
        ("① 자료 입력",    "특허·논문·사업계획서"),
        ("② AI 분석",      "PCML 구조화"),
        ("③ 선행기술조사", "신규성·진보성"),
        ("④ 스크리닝",     "등록가능성 판단"),
        ("⑤ 게이트 평가",  "Go / Hold / Kill"),
    ]
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
    _TECH_QUOTES = [
        ("기술은 발명할 때가 아니라 상용화될 때 비로소 가치를 갖는다.", "피터 드러커"),
        ("혁신은 리더와 추종자를 구별한다.", "스티브 잡스"),
        ("시장에서 검증받지 못한 기술은 발명에 불과하다.", "조셉 슘페터"),
        ("특허는 발명가를 위한 것이 아니라 산업 전체를 위한 것이다.", "에이브러햄 링컨"),
        ("위험을 감수하지 않으면 더 큰 위험을 감수하는 것이다.", "마크 저커버그"),
        ("IP 없는 스타트업은 경쟁 해자 없는 성이다.", "피터 틸"),
        ("연구실 성과가 사회 가치로 전환될 때 비로소 과학은 완성된다.", "한국 TLO 격언"),
        ("기술의 가치는 그것이 해결하는 문제의 크기에 달려 있다.", "엘론 머스크"),
        ("기술이전은 지식의 복제가 아니라 가치의 재창조이다.", "OECD 기술이전 보고서"),
        ("사업화 없는 혁신은 반쪽 혁신이다.", "KAIST 기술사업화 원칙"),
        ("스타트업은 반복 가능하고 확장 가능한 비즈니스 모델을 찾는 조직이다.", "스티브 블랭크"),
        ("기술의 수명은 특허 기간보다 짧다. 빠르게 움직여라.", "실리콘밸리 격언"),
        ("가장 어려운 것은 기술을 발명하는 것이 아니라 시장을 찾는 것이다.", "스티브 블랭크"),
        ("지식재산권은 혁신의 씨앗을 보호하는 울타리다.", "앨런 그린스펀"),
        ("혁신은 변화를 기회로 포착하는 것이다.", "피터 드러커"),
        ("기술이전은 기술의 출발지가 아닌 도착지에서 가치가 결정된다.", "나타나엘 마스칼리트"),
        ("아이디어는 1%이고, 실행이 99%이다.", "토마스 에디슨"),
        ("세상을 바꾸는 것은 기술이 아니라 기술을 사용하는 사람이다.", "빌 게이츠"),
        ("훌륭한 아이디어를 가진 사람은 많지만, 그것을 실현하는 사람은 드물다.", "월트 디즈니"),
        ("기술사업화는 과학적 발견을 경제적 가치로 번역하는 예술이다.", "MIT 기술이전 센터"),
    ]
    if "_home_quote" not in st.session_state:
        st.session_state["_home_quote"] = random.choice(_TECH_QUOTES)
    _q, _a = st.session_state["_home_quote"]

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
        st.caption(f'💬 "{_q}" — {_a}')

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

        # 안내 칩
        st.markdown(
            "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px'>"
            "<span style='background:rgba(37,99,235,.15);border:1px solid rgba(59,130,246,.3);border-radius:20px;padding:3px 10px;font-size:10px;color:#93c5fd'>🤖 기술명 자동 추출</span>"
            "<span style='background:rgba(37,99,235,.15);border:1px solid rgba(59,130,246,.3);border-radius:20px;padding:3px 10px;font-size:10px;color:#93c5fd'>📊 TRL 자동 평가</span>"
            "<span style='background:rgba(37,99,235,.15);border:1px solid rgba(59,130,246,.3);border-radius:20px;padding:3px 10px;font-size:10px;color:#93c5fd'>🔍 선행기술 자동 조사</span>"
            "<span style='background:rgba(37,99,235,.15);border:1px solid rgba(59,130,246,.3);border-radius:20px;padding:3px 10px;font-size:10px;color:#93c5fd'>✅ 신규성 스크리닝</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        if st.button("🔍 분석 시작 →", type="primary",
                     use_container_width=True, key="step1_next"):
            text_in   = st.session_state.get("step1_text", "")
            up_obj    = st.session_state.get("step1_file")
            file_name = up_obj.name if up_obj else ""
            if not text_in.strip() and not file_name:
                st.warning("텍스트를 입력하거나 파일을 업로드해 주세요.")
            else:
                st.session_state.home_text     = text_in.strip()
                st.session_state.home_filename = file_name
                # 기술명·TRL은 Step 2에서 AI가 추출 — 임시 설정
                st.session_state.tech_name     = text_in[:30].replace("\n"," ") or file_name or "분석 중..."
                st.session_state.home_rec_stages = _recommend_stages(text_in, 4, file_name)
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
    # ════════════════════════════════
    # STEP 2 — AI 분석 (PCML 구조화 + 기술명/TRL 자동 추출)
    # ════════════════════════════════
    elif step == 2:
        st.markdown(
            "<div style='margin-bottom:20px'>"
            "<div style='font-size:22px;font-weight:700'>🤖 AI 분석 중</div>"
            "<div style='font-size:13px;color:#888;margin-top:4px'>"
            "PCML v2.0으로 기술 구조를 파악하고 기술명·TRL을 자동 추출합니다</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        home_text = st.session_state.get("home_text", "")
        step2_done = st.session_state.get("_step2_done", False)

        if not step2_done:
            with st.spinner("PCML v2.0 분석 + 기술명/TRL 자동 추출 중..."):
                pcml_r = api_post("/ip/pcml", {
                    "patent_text": home_text,
                    "tech_id":     st.session_state.tech_id or "HOME",
                    "input_mode":  "claim_only",
                }) if home_text.strip() else None

            if pcml_r:
                st.session_state["_pcml_result"] = pcml_r
                # 기술명·TRL 자동 추출
                patent_meta = pcml_r.get("patent_layer", {})
                auto_name = patent_meta.get("title") or patent_meta.get("tech_field") or ""
                auto_trl  = pcml_r.get("kpi_inputs", {}).get("trl", 4)
                if auto_name:
                    st.session_state.tech_name = auto_name
                if isinstance(auto_trl, int):
                    st.session_state.home_trl = auto_trl
            else:
                # API 불가 → 텍스트에서 간단 추출
                auto_name = home_text[:40].replace("\n"," ").strip()
                st.session_state.tech_name = auto_name or "분석 기술"

            st.session_state["_step2_done"] = True
            st.rerun()
        else:
            pcml_r  = st.session_state.get("_pcml_result")
            c1, c2 = st.columns(2)

            # 기술명 확인
            confirmed_name = c1.text_input(
                "기술명 (AI 추출 · 수정 가능)",
                value=st.session_state.tech_name,
                key="step2_name",
            )
            confirmed_trl = c2.select_slider(
                "TRL (AI 평가 · 수정 가능)",
                options=list(range(1, 10)),
                value=int(st.session_state.home_trl or 4),
                format_func=lambda x: f"TRL {x}",
                key="step2_trl",
            )

            # PCML 미니 결과
            if pcml_r:
                clg   = pcml_r.get("claim_graph_layer", {})
                nodes = clg.get("nodes", [])
                links = clg.get("links", [])
                attrs = clg.get("attributes", [])
                qc    = pcml_r.get("qc", {})
                gate  = pcml_r.get("gate", "–")
                score = pcml_r.get("score", 0)

                gate_color = {"Go":"#4ade80","Hold":"#fbbf24","Kill":"#f87171"}.get(gate,"#94a3b8")
                core_nodes = sum(1 for n in nodes if n.get("element_class")=="Core")

                st.markdown(
                    f"<div style='background:rgba(37,99,235,.08);border:1px solid rgba(59,130,246,.2);"
                    f"border-radius:10px;padding:16px;margin:12px 0'>"
                    f"<div style='display:flex;gap:20px;flex-wrap:wrap'>"
                    f"<div><div style='font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700'>PCML Gate</div>"
                    f"<div style='font-size:22px;font-weight:800;color:{gate_color}'>{gate}</div>"
                    f"<div style='font-size:10px;color:#94a3b8'>점수 {score:.1f}</div></div>"
                    f"<div><div style='font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700'>노드</div>"
                    f"<div style='font-size:22px;font-weight:800;color:#f1f5f9'>{len(nodes)}</div>"
                    f"<div style='font-size:10px;color:#94a3b8'>Core {core_nodes}개</div></div>"
                    f"<div><div style='font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700'>링크</div>"
                    f"<div style='font-size:22px;font-weight:800;color:#f1f5f9'>{len(links)}</div>"
                    f"<div style='font-size:10px;color:#94a3b8'>속성 {len(attrs)}개</div></div>"
                    f"<div><div style='font-size:9px;color:#64748b;text-transform:uppercase;font-weight:700'>QC 등급</div>"
                    f"<div style='font-size:22px;font-weight:800;color:#f1f5f9'>{qc.get('qc_grade','–')}</div>"
                    f"<div style='font-size:10px;color:#94a3b8'>신뢰 {qc.get('qc_confidence',0)}%</div></div>"
                    f"</div>"
                    f"<div style='margin-top:10px;font-size:10px;color:#64748b'>"
                    f"💡 상세 그래프는 IP 분석 허브 → 구조 분석 탭에서 확인하세요</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.info("API 연결 없음 — 텍스트 기반 기본 분석으로 진행합니다.")

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            cb, cn = st.columns(2)
            if cb.button("← 뒤로", use_container_width=True, key="step2_back"):
                st.session_state.home_step = 1
                st.session_state["_step2_done"] = False
                st.rerun()
            if cn.button("선행기술조사 →", type="primary", use_container_width=True, key="step2_next"):
                st.session_state.tech_name = confirmed_name
                st.session_state.home_trl  = confirmed_trl
                st.session_state.home_rec_stages = _recommend_stages(home_text, confirmed_trl, "")
                st.session_state.home_step = 3
                st.rerun()

    # ════════════════════════════════
    # STEP 3 — 선행기술조사
    # ════════════════════════════════
    elif step == 3:
        name = st.session_state.tech_name or "기술"
        home_text = st.session_state.get("home_text", "")

        st.markdown(
            f"<div style='margin-bottom:16px'>"
            f"<div style='font-size:22px;font-weight:700'>🔍 선행기술조사</div>"
            f"<div style='font-size:13px;color:#888;margin-top:4px'>"
            f"<b style='color:#e2e8f0'>{name}</b> — 신규성·진보성 판단을 위한 선행기술 검색</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        scr_done = st.session_state.get("_step3_scr_done", False)

        if not scr_done:
            # 검색 파라미터
            sc1, sc2 = st.columns(2)
            search_scope = sc1.selectbox(
                "조사 범위", ["국내 (KIPRIS)", "국제 (USPTO+EPO)", "전체 (국내+국제)"],
                key="step3_scope",
            )
            search_depth = sc2.radio(
                "조사 깊이", ["빠른 스크리닝 (3~5분)", "정밀 조사 (10~15분)"],
                horizontal=True, key="step3_depth",
            )

            keywords = st.text_input(
                "핵심 키워드 (선택 · 자동 추출 가능)",
                placeholder="예: 딥러닝, 작물 수확량, IoT 센서",
                key="step3_kw",
            )

            st.markdown(
                "<div style='background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.2);"
                "border-radius:8px;padding:10px 14px;font-size:11px;color:#fbbf24;margin:8px 0'>"
                "⚡ 선행기술조사는 SCR(신규성 스크리닝)과 연계하여 한 번에 실행됩니다</div>",
                unsafe_allow_html=True,
            )

            cb3, cn3 = st.columns(2)
            if cb3.button("← 뒤로", use_container_width=True, key="step3_back"):
                st.session_state.home_step = 2
                st.session_state["_step2_done"] = True
                st.rerun()

            if cn3.button("🔍 선행기술 + 스크리닝 실행 →", type="primary",
                          use_container_width=True, key="step3_run"):
                with st.spinner("선행기술 조사 + SCR 스크리닝 중... (30~60초)"):
                    scr_r = api_post("/ip/analyze-chain", {
                        "patent_text": home_text,
                        "tech_id":     st.session_state.tech_id or "HOME3",
                        "scope":       "full" if "정밀" in search_depth else "basic",
                    })
                st.session_state["_step3_scr"] = scr_r
                st.session_state["_step3_scr_done"] = True
                st.rerun()

        else:
            scr_r = st.session_state.get("_step3_scr")

            if scr_r:
                chain = scr_r.get("chain", {})
                pcml  = chain.get("step2_pcml", {})
                scr   = chain.get("step3_scr",  {})
                overall_gate = scr_r.get("overall_gate", "–")
                gate_color = {"Go":"#4ade80","Hold":"#fbbf24","Kill":"#f87171"}.get(overall_gate,"#94a3b8")

                # 결과 요약
                st.markdown(
                    f"<div style='background:rgba(22,163,74,.08);border:1px solid rgba(22,163,74,.2);"
                    f"border-radius:10px;padding:16px;margin-bottom:16px'>"
                    f"<div style='font-size:14px;font-weight:700;margin-bottom:10px'>📋 선행기술조사 결과</div>"
                    f"<div style='display:flex;gap:20px;flex-wrap:wrap'>"
                    f"<div><div style='font-size:9px;color:#64748b;font-weight:700;text-transform:uppercase'>신규성</div>"
                    f"<div style='font-size:20px;font-weight:800;color:#f1f5f9'>{scr.get('novelty','–')}</div></div>"
                    f"<div><div style='font-size:9px;color:#64748b;font-weight:700;text-transform:uppercase'>SCR 판정</div>"
                    f"<div style='font-size:20px;font-weight:800;color:{gate_color}'>{scr.get('gate','–')}</div></div>"
                    f"<div><div style='font-size:9px;color:#64748b;font-weight:700;text-transform:uppercase'>종합 점수</div>"
                    f"<div style='font-size:20px;font-weight:800;color:#f1f5f9'>{float(scr.get('score',0)):.1f}</div></div>"
                    f"<div><div style='font-size:9px;color:#64748b;font-weight:700;text-transform:uppercase'>종합 게이트</div>"
                    f"<div style='font-size:20px;font-weight:800;color:{gate_color}'>{overall_gate}</div></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

                # 선행기술 목록 (SCR 결과에서)
                prior_arts = scr.get("prior_arts", scr.get("references", []))
                if prior_arts:
                    st.markdown("**🔎 발견된 선행기술**")
                    for pa in prior_arts[:5]:
                        if isinstance(pa, dict):
                            st.markdown(
                                f"<div style='background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);"
                                f"border-radius:8px;padding:10px 14px;margin-bottom:6px;font-size:11px'>"
                                f"<b style='color:#93c5fd'>{pa.get('id','')}</b> "
                                f"<span style='color:#64748b'>· 유사도 {pa.get('similarity',pa.get('score',0)):.0%}</span><br>"
                                f"<span style='color:#e2e8f0'>{pa.get('title',pa.get('text',''))[:100]}</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(f"- {str(pa)[:100]}")

                # 다음 단계
                next_steps = scr_r.get("next_steps", [])
                if next_steps:
                    st.markdown("**📌 권장 후속 액션**")
                    for ns in next_steps[:3]:
                        st.markdown(f"→ {ns}")

                _save_gate(2, {"gate": overall_gate, "score": float(scr.get("score",0))})
            else:
                st.warning("조사 결과가 없습니다. API 연결 상태를 확인하세요.")

            cb4, cn4 = st.columns(2)
            if cb4.button("← 재조사", use_container_width=True, key="step3_redo"):
                st.session_state["_step3_scr_done"] = False
                st.rerun()
            if cn4.button("게이트 평가 →", type="primary",
                          use_container_width=True, key="step3_next"):
                st.session_state.home_step = 4
                st.rerun()

    # ════════════════════════════════
    # STEP 4 — 스크리닝 · 게이트 평가 · 워크스페이스 이동
    # ════════════════════════════════
    elif step == 4:
        name = st.session_state.tech_name or "기술"
        scr_r = st.session_state.get("_step3_scr")
        overall_gate = "Hold"
        if scr_r:
            overall_gate = scr_r.get("overall_gate", "Hold")

        gate_color = {"Go":"#4ade80","Hold":"#fbbf24","Kill":"#f87171"}.get(overall_gate,"#94a3b8")
        gate_bg    = {"Go":"rgba(22,163,74,.1)","Hold":"rgba(202,138,4,.1)","Kill":"rgba(220,38,38,.1)"}.get(overall_gate,"rgba(30,41,59,.6)")
        gate_border= {"Go":"rgba(22,163,74,.3)","Hold":"rgba(202,138,4,.3)","Kill":"rgba(220,38,38,.3)"}.get(overall_gate,"rgba(51,65,85,.8)")

        st.markdown(
            f"<div style='margin-bottom:16px'>"
            f"<div style='font-size:22px;font-weight:700'>⚖️ 게이트 평가 결과</div>"
            f"<div style='font-size:13px;color:#888;margin-top:4px'>"
            f"<b style='color:#e2e8f0'>{name}</b> — 선행기술조사 + PCML 분석 종합 판정</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # 게이트 카드
        gate_icon = {"Go":"🟢","Hold":"🟡","Kill":"🔴"}.get(overall_gate,"⚪")
        gate_desc = {"Go":"신규성·진보성 충족 — 다음 단계로 진행 권장",
                     "Hold":"조건부 통과 — 보완 후 재평가 필요",
                     "Kill":"선행기술 저촉 가능성 높음 — 피벗 또는 중단 검토"}.get(overall_gate,"평가 결과 확인 필요")

        st.markdown(
            f"<div style='background:{gate_bg};border:2px solid {gate_border};"
            f"border-radius:14px;padding:24px;text-align:center;margin-bottom:20px'>"
            f"<div style='font-size:48px;margin-bottom:8px'>{gate_icon}</div>"
            f"<div style='font-size:28px;font-weight:800;color:{gate_color}'>{overall_gate}</div>"
            f"<div style='font-size:13px;color:#94a3b8;margin-top:6px'>{gate_desc}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # 4단계 프로세스 요약
        st.markdown("**📊 분석 프로세스 요약**")
        process_steps = [
            ("① 자료 입력",    "✅ 완료", "#4ade80"),
            ("② AI 분석 (PCML)", "✅ 완료", "#4ade80"),
            ("③ 선행기술조사", "✅ 완료", "#4ade80"),
            ("④ 스크리닝",     f"{gate_icon} {overall_gate}", gate_color),
        ]
        cols = st.columns(4)
        for i, (label, status, color) in enumerate(process_steps):
            cols[i].markdown(
                f"<div style='background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);"
                f"border-radius:8px;padding:10px;text-align:center'>"
                f"<div style='font-size:10px;color:#64748b;margin-bottom:4px'>{label}</div>"
                f"<div style='font-size:12px;font-weight:700;color:{color}'>{status}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # 다음 액션 버튼들
        import time as _t
        ca, cb5, cc = st.columns(3)

        if ca.button("🏠 워크스페이스로 →", type="primary", use_container_width=True, key="step4_ws"):
            auto_id = f"TECH-{int(_t.time())%100000}"
            st.session_state.tech_id   = auto_id
            st.session_state.trl       = st.session_state.home_trl
            new_r = {"id": auto_id, "name": name,
                     "trl": st.session_state.home_trl, "icon": "🔬"}
            st.session_state.recent_techs = [new_r] + st.session_state.recent_techs[:4]
            st.session_state.page = "workspace"
            st.rerun()

        if cb5.button("📋 G1 IP 구조화 →", use_container_width=True, key="step4_ip"):
            st.session_state.page = "g1"
            st.rerun()

        if cc.button("🔄 새 기술 분석", use_container_width=True, key="step4_reset"):
            _home_reset()

        # 리포트 다운로드
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        report_txt = (
            f"IPInsight 분석 리포트\n{'='*40}\n"
            f"기술명: {name}\nTRL: {st.session_state.home_trl}\n"
            f"게이트: {overall_gate}\n설명: {gate_desc}\n\n"
            f"입력 자료:\n{st.session_state.home_text[:500] or '–'}\n"
        )
        st.download_button(
            "📥 분석 리포트 다운로드 (.txt)",
            data=report_txt.encode("utf-8"),
            file_name=f"ipinsight_{name[:10]}.txt",
            mime="text/plain",
            use_container_width=True,
        )
        if st.button("← 선행기술조사로 돌아가기", use_container_width=True, key="step4_back"):
            st.session_state.home_step = 3
            st.rerun()

    # ── 기존 Step 3 하위 코드 (sel_n 참조) — 더 이상 사용하지 않음 ──
    elif step == 99:
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
            # MECE: 각 Stage → 전용 페이지
            _PAGE_MAP = {n: f"g{n}" for n in range(11)}
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
    _health_ws = api_get("/health", silent=True)
    _api_ok_ws = _health_ws is not None
    theme = st.session_state.get("theme", "dark"); bg_on = st.session_state.get("bg_on", True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{theme}');document.body.classList.{'add' if bg_on else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_api_ok_ws)
    render_context_banner()
    st.title("🏠 기술 워크스페이스")
    render_stage_bar()

    # ── Smart KPI Column Layout (Anaqua 스타일 — 사용자 커스터마이징) ──
    completed = sum(1 for g in st.session_state.stage_gates.values() if g.get("gate") == "Go")
    kills     = sum(1 for g in st.session_state.stage_gates.values() if g.get("gate") == "Kill")
    holds     = sum(1 for g in st.session_state.stage_gates.values() if g.get("gate") == "Hold")
    avg_score = (sum(g.get("score", 0) for g in st.session_state.stage_gates.values())
                 / max(len(st.session_state.stage_gates), 1))
    alerts_d  = api_get(f"/g10/kpi/{st.session_state.tech_id}/alerts", silent=True)
    alert_cnt = alerts_d.get("alert_count", 0) if alerts_d else 0

    _ALL_KPI = {
        "completed":  ("완료 단계",   f"{completed}/11",        "Go 판정",                        "🏁"),
        "avg_score":  ("평균 점수",   f"{avg_score:.1f}",       "0~100점",                        "📊"),
        "kill_hold":  ("Kill / Hold", f"{kills} / {holds}",     "재검토 필요" if kills else "없음","⚠️"),
        "alerts":     ("KPI 알림",    str(alert_cnt),            "🚨" if alert_cnt else "정상",    "🔔"),
        "trl":        ("TRL",         str(st.session_state.trl), "현재 기술성숙도",                "🔬"),
        "techs":      ("기술 수",     str(len(st.session_state.get("recent_techs",[]))), "등록 기술","📋"),
        "go_rate":    ("Go 비율",     f"{completed/11*100:.0f}%", "G0~G10 기준",                  "🎯"),
        "audit_cnt":  ("이력 건수",   str(len(st.session_state.get("gate_audit",[]))),"분석 실행","📝"),
    }
    visible_keys = st.session_state.get("_kpi_visible", list(_ALL_KPI)[:4])

    kpi_row, kpi_cfg_btn = st.columns([5, 1])
    with kpi_cfg_btn:
        if st.button("⚙️ KPI 설정", key="ws_kpi_cfg"):
            st.session_state["_show_kpi_cfg"] = not st.session_state.get("_show_kpi_cfg", False)
    if st.session_state.get("_show_kpi_cfg", False):
        with st.expander("KPI 카드 선택 (최대 6개)", expanded=True):
            new_vis = []
            cfg_cols = st.columns(4)
            for ci, (k, (label, val, delta, ico)) in enumerate(_ALL_KPI.items()):
                with cfg_cols[ci % 4]:
                    if st.checkbox(f"{ico} {label}", value=(k in visible_keys), key=f"kpi_cfg_{k}"):
                        new_vis.append(k)
            if new_vis:
                st.session_state["_kpi_visible"] = new_vis[:6]

    visible_keys = st.session_state.get("_kpi_visible", list(_ALL_KPI)[:4])
    kpi_cols = st.columns(max(len(visible_keys), 1))
    for ci, key in enumerate(visible_keys):
        if key in _ALL_KPI:
            label, val, delta, ico = _ALL_KPI[key]
            kpi_cols[ci].metric(f"{ico} {label}", val, delta)

    st.divider()

    # ── 필터 바 + Saved Views (Clarivate/Anaqua 스타일) ─────────────
    frow1, frow2 = st.columns([3, 1])
    with frow1:
        f_opts = ["전체", "Go", "Hold", "Kill", "미실행"]
        cur_f  = st.session_state.get("_ws_filter_gate", "전체")
        sel_f  = st.radio("게이트 필터", f_opts, index=f_opts.index(cur_f),
                          horizontal=True, key="ws_gate_filter_radio", label_visibility="collapsed")
        st.session_state["_ws_filter_gate"] = sel_f
    with frow2:
        saved = st.session_state.get("_ws_saved_views", [])
        sv_names = ["뷰 선택…"] + [v["name"] for v in saved]
        sv_sel = st.selectbox("저장된 뷰", sv_names, key="ws_saved_view_sel", label_visibility="collapsed")
        if sv_sel != "뷰 선택…":
            matched = next((v for v in saved if v["name"] == sv_sel), None)
            if matched:
                st.session_state["_ws_filter_gate"] = matched["filter_gate"]
                st.rerun()
        if st.button("💾 현재 뷰 저장", key="ws_save_view"):
            vname = f"필터:{sel_f}"
            if not any(v["name"] == vname for v in saved):
                saved.append({"name": vname, "filter_gate": sel_f})
                st.session_state["_ws_saved_views"] = saved
                st.success(f'뷰 "{vname}" 저장됨')

    # ── 듀얼 패널 레이아웃 (Anaqua/Wellspring 스타일) ───────────────
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown('<div class="sec-header-v2">단계별 진행 현황</div>', unsafe_allow_html=True)
        active_filter = st.session_state.get("_ws_filter_gate", "전체")
        grid_cols = st.columns(3)
        for n, (gid, name, icon) in STAGE_META.items():
            info  = st.session_state.stage_gates.get(n, {})
            gate  = info.get("gate", "미실행")
            score = info.get("score", 0)
            # 필터 적용
            if active_filter != "전체" and gate != active_filter:
                continue
            gate_color = {"Go":"#4ade80","Hold":"#fbbf24","Kill":"#f87171","미실행":"#334155"}.get(gate,"#334155")
            is_selected = st.session_state.get("_ws_selected_stage") == n
            border_style = f"border:1px solid {gate_color};" + ("box-shadow:0 0 10px rgba(59,130,246,.3);" if is_selected else "")
            html_card = (
                f'<div class="bm-card" style="{border_style}cursor:pointer;min-height:70px">'
                f'<div class="bm-card-hdr">'
                f'<span style="font-size:16px">{icon}</span>'
                f'<span class="bm-card-title">{gid} {name}</span>'
                f'</div>'
                f'<div style="display:flex;align-items:center;gap:6px">'
                f'<span style="width:7px;height:7px;border-radius:50%;background:{gate_color};display:inline-block"></span>'
                f'<span style="font-size:10px;color:{gate_color}">{gate}</span>'
                + (f'<span class="bm-tag" style="margin-left:auto">{score:.0f}점</span>' if gate != "미실행" else "")
                + f'</div></div>'
            )
            with grid_cols[n % 3]:
                st.markdown(html_card, unsafe_allow_html=True)
                if st.button(f"{'▶' if not is_selected else '▼'} {gid}", key=f"ws_sel_{n}",
                             use_container_width=True):
                    st.session_state["_ws_selected_stage"] = None if is_selected else n
                    st.rerun()

        # 3단 파이프라인 빠른 실행
        st.divider()
        with st.expander("⚡ Cross-Stage 빠른 진입 (G1+G2+G3 동시 분석)", expanded=False):
            st.caption("📌 단축 진입점 — 특허 텍스트 하나로 G1 PCML · G2 SCR · G3 시장성을 한 번에 분석합니다. 개별 G-Stage 페이지에서 심층 분석을 추가할 수 있습니다.")
            pipeline_text = st.text_area("특허 텍스트 또는 기술 설명",
                value=st.session_state.get("home_text", ""), height=110,
                key="ws_pipeline_text", placeholder="청구항 또는 기술 요약을 붙여넣으세요…")
            c_tam, c_grow = st.columns(2)
            ws_tam  = c_tam.number_input("TAM (USD)", value=500_000_000, step=100_000_000, format="%d", key="ws_tam")
            ws_grow = c_grow.number_input("성장률 (%)", value=8.0, step=1.0, key="ws_grow")
            ws_mkt  = st.text_input("목표 시장", value="글로벌 B2B 기술 라이선싱", key="ws_mkt")
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
                        sc2.metric("SCR (G2)",  f"{scores.get('scr',0):.0f}점",  chain.get('step3_scr',{}).get('gate',''))
                        sc3.metric("시장성 (G3)",f"{scores.get('g3',0):.0f}점",  chain.get('step4_g3',{}).get('gate',''))
                        sc4.metric("종합 점수", f"{scores.get('composite',0):.0f}점", resp.get('overall_gate',''))
                        for stage_n, step_key in [(1,'step2_pcml'),(2,'step3_scr'),(3,'step4_g3')]:
                            s = chain.get(step_key, {})
                            if s.get('gate'):
                                _save_gate(stage_n, s)
                        st.session_state.last_result = {"gate": resp.get('overall_gate',''), "score": scores.get('composite',0), "next_actions": resp.get('next_steps',[])}
                        st.session_state.last_stage  = 3
                        for ns in resp.get("next_steps", [])[:3]:
                            st.markdown(f"- {ns}")
                    else:
                        st.error("파이프라인 실행 실패 — API 서버 상태를 확인하세요.")

    with right_col:
        sel_stage = st.session_state.get("_ws_selected_stage")
        if sel_stage is not None:
            # ── 상세 패널 (선택된 스테이지) ──────────────────
            gid, sname, sicon = STAGE_META[sel_stage]
            info  = st.session_state.stage_gates.get(sel_stage, {})
            gate  = info.get("gate", "미실행")
            score = info.get("score", 0)
            gate_color = {"Go":"#4ade80","Hold":"#fbbf24","Kill":"#f87171"}.get(gate,"#475569")

            st.markdown(f'<div class="sec-header-v2">{sicon} {gid} — {sname} 상세</div>', unsafe_allow_html=True)
            if gate != "미실행":
                render_gate_card(gate=gate, score=score, stage_label=f"{gid} {sname}", next_actions=[])
            else:
                st.markdown('<div class="info-card">아직 분석이 실행되지 않았습니다.</div>', unsafe_allow_html=True)

            # 해당 스테이지 이동 버튼
            if st.button(f"▶ {gid} {sname} 열기", type="primary", key=f"ws_open_{sel_stage}", use_container_width=True):
                st.session_state.page = f"g{sel_stage}"
                st.rerun()

            # Gate → 다음 단계
            if gate == "Go" and sel_stage < 10:
                next_n = sel_stage + 1
                ng, nn, ni = STAGE_META[next_n]
                if st.button(f"▶ {ni} {ng} {nn} 시작", key=f"ws_next_{sel_stage}", use_container_width=True):
                    st.session_state.page = f"g{next_n}"
                    st.rerun()
            elif gate == "Kill":
                if st.button("🔄 G0 재진입 (Pivot)", key=f"ws_pivot_{sel_stage}", use_container_width=True):
                    st.session_state.page = "g0"; st.rerun()

        else:
            # ── 우측 패널: 탭 2개 ────────────────────────────
            tab_audit, tab_portfolio = st.tabs(["📋 활동 타임라인", "🗺️ 포트폴리오 맵"])

            with tab_audit:
                audit = list(reversed(st.session_state.gate_audit))
                if not audit:
                    st.markdown('<div class="info-card">Gate 분석을 실행하면 여기에 이력이 기록됩니다.</div>', unsafe_allow_html=True)
                else:
                    for entry in audit[:15]:
                        g = entry.get("gate","")
                        col = {"Go":"#4ade80","Hold":"#fbbf24","Kill":"#f87171"}.get(g,"#475569")
                        st.markdown(
                            f'<div style="display:flex;gap:10px;align-items:flex-start;'
                            f'padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04)">'
                            f'<div style="min-width:38px;text-align:right;font-size:9px;color:#334155;padding-top:2px">'
                            f'{entry["date"]}<br>{entry["ts"]}</div>'
                            f'<div style="width:2px;background:{col};border-radius:2px;align-self:stretch;flex-shrink:0"></div>'
                            f'<div>'
                            f'<div style="font-size:11px;font-weight:600;color:#cbd5e1">'
                            f'{entry["icon"]} {entry["gid"]} {entry["name"]}</div>'
                            f'<div style="font-size:10px;color:{col};margin-top:2px">'
                            f'{g} · {entry["score"]:.0f}점</div>'
                            f'<div style="font-size:9px;color:#334155;margin-top:1px">{entry.get("tech_name","")}</div>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )

            with tab_portfolio:
                # ── Portfolio Heat Map (Clarivate 스타일) ────
                techs = st.session_state.get("recent_techs", [])
                if not techs:
                    st.markdown('<div class="info-card">홈 화면에서 기술을 등록하면 포트폴리오 맵이 표시됩니다.</div>', unsafe_allow_html=True)
                else:
                    st.caption(f"총 {len(techs)}개 기술 · G0~G10 단계 분포")
                    # 스테이지별 기술 카운트
                    _stage_counts = {n: 0 for n in range(11)}
                    for tech in techs:
                        trl_val = int(tech.get("trl", 4))
                        # TRL → 대략적 스테이지 매핑
                        approx_stage = min(10, max(0, (trl_val - 1) * 10 // 8))
                        _stage_counts[approx_stage] += 1

                    max_count = max(_stage_counts.values()) or 1
                    heat_rows = ""
                    for n, (gid, name, icon) in STAGE_META.items():
                        count = _stage_counts[n]
                        pct   = count / max_count
                        intensity = int(pct * 200)
                        bg = f"rgba(59,130,246,{pct:.2f})" if count > 0 else "rgba(255,255,255,.03)"
                        heat_rows += (
                            f'<div style="display:flex;align-items:center;gap:8px;'
                            f'padding:5px 8px;border-radius:6px;background:{bg};margin:2px 0">'
                            f'<span style="font-size:11px;min-width:24px">{icon}</span>'
                            f'<span style="font-size:10px;color:#94a3b8;min-width:60px">{gid}</span>'
                            f'<div style="flex:1;height:4px;background:rgba(255,255,255,.07);border-radius:2px">'
                            f'<div style="width:{pct*100:.0f}%;height:100%;background:#3b82f6;border-radius:2px"></div></div>'
                            f'<span style="font-size:10px;color:#60a5fa;min-width:20px;text-align:right">{count}</span>'
                            f'</div>'
                        )
                    st.markdown(f'<div style="margin-top:8px">{heat_rows}</div>', unsafe_allow_html=True)

                    st.divider()
                    # 기술 목록 간략 표
                    for tech in techs[:6]:
                        trl_v = int(tech.get("trl", 4))
                        trl_col = "#4ade80" if trl_v >= 7 else "#fbbf24" if trl_v >= 4 else "#94a3b8"
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:8px;'
                            f'padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);cursor:pointer">'
                            f'<span style="font-size:14px">{tech.get("icon","🔬")}</span>'
                            f'<div style="flex:1">'
                            f'<div style="font-size:11px;color:#e2e8f0">{tech.get("name","")}</div>'
                            f'<div style="font-size:9px;color:#475569">{tech.get("project","")}</div>'
                            f'</div>'
                            f'<span style="font-size:9px;color:{trl_col};font-weight:700">TRL {trl_v}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

    # 마지막 결과 Gate 카드 (워크스페이스 하단, 패널 미선택 시)
    if st.session_state.last_result and st.session_state.last_stage is not None \
            and st.session_state.get("_ws_selected_stage") is None:
        st.divider()
        r  = st.session_state.last_result
        sn = st.session_state.last_stage
        gid, name, _ = STAGE_META.get(sn, ("G?", "?", "?"))
        render_gate_card(gate=r.get("gate",""), score=float(r.get("score",0)),
                         stage_label=f"{gid} {name}", next_actions=r.get("next_actions",[]))
        gate = r.get("gate","")
        if gate == "Go" and sn < 10:
            next_n = sn + 1
            if st.button(f"▶ {STAGE_META[next_n][2]} G{next_n} {STAGE_META[next_n][1]} 시작", type="primary", key="ws_last_next"):
                st.session_state.page = f"g{next_n}"; st.rerun()
        elif gate == "Kill":
            ca, cb = st.columns(2)
            if ca.button("🔄 G0 재진입 (Pivot)", key="ws_pivot_last"):
                st.session_state.page = "g0"; st.rerun()
            if cb.button("📄 IP 라이선싱 검토", key="ws_lic_last"):
                st.session_state.page = "g1"; st.rerun()


# ════════════════════════════════════════════════════════════════
# G1 — IP 구조화 (PCML v3.0 + SCR 체인 통합)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g1":
    _health_ip = api_get("/health", silent=True)
    _api_ok_ip = _health_ip is not None
    theme = st.session_state.get("theme", "dark"); bg_on = st.session_state.get("bg_on", True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{theme}');document.body.classList.{'add' if bg_on else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_api_ok_ip)
    render_context_banner()
    st.title("📋 G1 — IP 구조화")
    render_stage_bar(current=1)

    tab_graph, tab_chain, tab_extended, tab_lifecycle, tab_fto = st.tabs(
        ["🔗 구조 분석", "⚡ G1+G2 체인", "🚀 G1→G2→G3 통합", "🔄 IP 전주기", "🔍 FTO · 경쟁사"]
    )

    # ── 구조 분석 탭 ──────────────────────────────────────────────
    with tab_graph:
        st.subheader("PCML v3.0 — 기술·시장·사업·규제 통합 구조 분석")
        st.caption("특허·사업계획서·시장보고서 등 모든 문서를 4도메인으로 구조화합니다.")

        stored_pcml = st.session_state.get("_pcml_result")

        col_inp, col_btn = st.columns([3, 1])
        with col_inp:
            graph_text = st.text_area(
                "입력 문서 (특허·사업계획서·시장보고서·기술요약 등)",
                height=110,
                placeholder=(
                    "예) 청구항 1: 딥러닝 기반 작물 수확량 예측 방법...\n"
                    "또는: 시장 규모 2026년 1.2조원, TAM 5.4조원, 주요 경쟁사 A사·B사...\n"
                    "또는: 주요 수익원은 SaaS 구독료(월 30만원/농가), 파트너는 농협..."
                ),
                key="graph_patent_text",
                value=st.session_state.get("_ip_text", ""),
            )
        with col_btn:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            mode_sel = st.selectbox("입력 모드", ["full_spec","claim_only","business_plan","market_report","mixed"],
                                    key="pcml_input_mode_sel")
            if st.button("🔍 PCML v3.0 분석", type="primary", use_container_width=True,
                         key="graph_run", disabled=not graph_text.strip()):
                with st.spinner("PCML v3.0 기술·시장·사업·규제 4도메인 구조화 중..."):
                    r = api_post("/ip/pcml", {
                        "patent_text": graph_text,
                        "tech_id":     st.session_state.tech_id or "GRAPH",
                        "input_mode":  mode_sel,
                    })
                if r:
                    st.session_state["_pcml_result"] = r
                    stored_pcml = r
                    st.success("✅ PCML v3.0 분석 완료")
                else:
                    st.error("분석 실패 — API를 확인하세요.")

        if stored_pcml:
            render_pcml_chart(stored_pcml)

            import pandas as pd

            # 도메인별 노드 상세 탭
            DOMAIN_TABS = [
                ("tech_graph_layer",       "🔵 기술 노드"),
                ("market_graph_layer",     "🟢 시장 노드"),
                ("business_graph_layer",   "🟡 사업 노드"),
                ("regulatory_graph_layer", "🔴 규제 노드"),
            ]
            all_domain_nodes = []
            for lkey, _ in DOMAIN_TABS:
                for n in stored_pcml.get(lkey, {}).get("nodes", []):
                    all_domain_nodes.append(n)
            # v2 호환
            for n in stored_pcml.get("claim_graph_layer", {}).get("nodes", []):
                all_domain_nodes.append(n)

            if all_domain_nodes:
                with st.expander(f"🗂️ 전체 노드 상세 ({len(all_domain_nodes)}개)"):
                    df = pd.DataFrame([{
                        "ID": n.get("node_id"), "도메인": n.get("domain", "technology"),
                        "라벨": n.get("label"), "유형": n.get("node_type"),
                        "클래스": n.get("element_class"),
                        "신뢰도": f"{int(n.get('confidence_score',0)*100)}%",
                    } for n in all_domain_nodes])
                    st.dataframe(df, use_container_width=True, hide_index=True)

            # 도메인 간 링크
            cross_links = stored_pcml.get("cross_domain_links", [])
            if cross_links:
                with st.expander(f"🔀 도메인 간 연결 ({len(cross_links)}개)"):
                    df_xl = pd.DataFrame([{
                        "ID": l.get("link_id"),
                        "출발노드": l.get("src_node"), "출발도메인": l.get("src_domain"),
                        "도착노드": l.get("dst_node"), "도착도메인": l.get("dst_domain"),
                        "관계": l.get("relation_type"),
                        "근거": (l.get("rationale") or "")[:60],
                    } for l in cross_links])
                    st.dataframe(df_xl, use_container_width=True, hide_index=True)

            # 시장 KPI
            mkt_kpi = stored_pcml.get("market_graph_layer", {}).get("market_kpi", {})
            if any(v and v != "정보 없음" for v in mkt_kpi.values()):
                with st.expander("📊 시장 KPI"):
                    mk1, mk2, mk3, mk4 = st.columns(4)
                    mk1.metric("TAM", mkt_kpi.get("tam", "–"))
                    mk2.metric("SAM", mkt_kpi.get("sam", "–"))
                    mk3.metric("SOM", mkt_kpi.get("som", "–"))
                    mk4.metric("CAGR", mkt_kpi.get("cagr", "–"))

            # 규제 리스크
            reg_risk = stored_pcml.get("regulatory_graph_layer", {}).get("risk_summary", {})
            if reg_risk.get("overall_risk"):
                with st.expander("⚖️ 규제 리스크 요약"):
                    risk_col = {"Low":"🟢","Medium":"🟡","High":"🟠","Critical":"🔴"}.get(
                        reg_risk.get("overall_risk",""), "⚪")
                    st.markdown(f"**종합 리스크**: {risk_col} {reg_risk.get('overall_risk','–')}")
                    if reg_risk.get("blocking_issues"):
                        st.warning("🚧 블로킹 이슈: " + " / ".join(reg_risk["blocking_issues"]))
                    if reg_risk.get("key_certifications"):
                        st.info("📋 필요 인증: " + " / ".join(reg_risk["key_certifications"]))

            # ── 특허 현황 ──────────────────────────────────────────
            tech_nodes = stored_pcml.get("tech_graph_layer", {}).get("nodes", [])
            patent_nodes = [n for n in tech_nodes if n.get("node_type") == "PatentRight"]
            if patent_nodes:
                with st.expander(f"📜 특허권 현황 ({len(patent_nodes)}건)"):
                    import pandas as pd
                    rows = []
                    for n in patent_nodes:
                        attrs_all = stored_pcml.get("tech_graph_layer", {}).get("attributes", [])
                        nat = {a.get("attr_type"): a.get("value") for a in attrs_all if a.get("target_id") == n.get("node_id")}
                        rows.append({
                            "특허 레이블": n.get("label", ""),
                            "특허번호": nat.get("patent_no", "–"),
                            "IP 상태": nat.get("ip_status", "–"),
                            "청구범위": nat.get("claim_scope", "–"),
                            "출원국가": nat.get("filing_country", "–"),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # ── 고객검증 현황 ───────────────────────────────────────
            mkt_nodes = stored_pcml.get("market_graph_layer", {}).get("nodes", [])
            val_nodes = [n for n in mkt_nodes if n.get("node_type") == "Validation"]
            if val_nodes:
                with st.expander(f"✅ 고객검증 결과 ({len(val_nodes)}건)"):
                    import pandas as pd
                    rows = []
                    mkt_attrs = stored_pcml.get("market_graph_layer", {}).get("attributes", [])
                    for n in val_nodes:
                        nat = {a.get("attr_type"): a.get("value") for a in mkt_attrs if a.get("target_id") == n.get("node_id")}
                        result_emoji = {"긍정": "🟢", "부정": "🔴", "혼합": "🟡", "미결": "⚪"}.get(nat.get("validation_result", ""), "⚪")
                        rows.append({
                            "검증명": n.get("label", ""),
                            "결론": f"{result_emoji} {nat.get('validation_result', '–')}",
                            "방법": nat.get("validation_method", "–"),
                            "N수": nat.get("sample_size", "–"),
                            "NPS": nat.get("nps_score", "–"),
                            "WTP": nat.get("willingness_to_pay", "–"),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # ── 투자 현황 ──────────────────────────────────────────
            biz_nodes = stored_pcml.get("business_graph_layer", {}).get("nodes", [])
            inv_nodes  = [n for n in biz_nodes if n.get("node_type") in ("Investor", "FundingRound")]
            if inv_nodes:
                with st.expander(f"💰 투자 현황 ({len(inv_nodes)}건)"):
                    import pandas as pd
                    rows = []
                    biz_attrs = stored_pcml.get("business_graph_layer", {}).get("attributes", [])
                    for n in inv_nodes:
                        nat = {a.get("attr_type"): a.get("value") for a in biz_attrs if a.get("target_id") == n.get("node_id")}
                        rows.append({
                            "유형": n.get("node_type", ""),
                            "명칭": n.get("label", ""),
                            "투자금액": nat.get("investment_amount", "–"),
                            "기업가치": nat.get("valuation", "–"),
                            "지분율": nat.get("equity_ratio", "–"),
                            "단계": nat.get("investment_stage", "–"),
                            "자금유형": nat.get("funding_type", "–"),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # ── 정책 현황 ──────────────────────────────────────────
            reg_nodes = stored_pcml.get("regulatory_graph_layer", {}).get("nodes", [])
            policy_nodes = [n for n in reg_nodes if n.get("node_type") == "Policy"]
            if policy_nodes:
                with st.expander(f"🏛️ 활용 가능 정책 ({len(policy_nodes)}건)"):
                    import pandas as pd
                    rows = []
                    reg_attrs = stored_pcml.get("regulatory_graph_layer", {}).get("attributes", [])
                    for n in policy_nodes:
                        nat = {a.get("attr_type"): a.get("value") for a in reg_attrs if a.get("target_id") == n.get("node_id")}
                        align_emoji = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(nat.get("policy_alignment", ""), "⚪")
                        rows.append({
                            "정책명": n.get("label", ""),
                            "정책번호/고시": nat.get("policy_ref", "–"),
                            "지원규모": nat.get("support_amount", "–"),
                            "기간": nat.get("policy_period", "–"),
                            "자격조건": (nat.get("eligibility") or "–")[:40],
                            "부합도": f"{align_emoji} {nat.get('policy_alignment', '–')}",
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # 청구항 목록 (v2 호환)
            claims = stored_pcml.get("tech_graph_layer", {}).get("claims", []) or \
                     stored_pcml.get("claim_graph_layer", {}).get("claims", [])
            if claims:
                with st.expander(f"📋 청구항 목록 ({len(claims)}건)"):
                    for c in claims:
                        badge = "🔵 독립항" if c.get("claim_type") == "independent" else "⚪ 종속항"
                        st.markdown(f"**C-{c.get('claim_no','')}** {badge}  \n{c.get('claim_text','')[:200]}...")
        else:
            st.markdown(
                "<div style='text-align:center;padding:60px;color:rgba(255,255,255,.3)'>"
                "⬆️ 문서를 입력하고 PCML v3.0 분석을 실행하세요<br>"
                "<small>특허·사업계획서·시장보고서 모두 지원합니다</small></div>",
                unsafe_allow_html=True,
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
                    render_output_doc(result, collapsed=True)

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

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("📋 G1 PCML", f"{scores.get('pcml',0):.0f}점", pcml_s.get('gate',''))
                mc2.metric("🧪 G2 SCR",  f"{scores.get('scr',0):.0f}점",  scr_s.get('gate',''))
                mc3.metric("🌐 G3 시장", f"{scores.get('g3',0):.0f}점",   g3_s.get('gate',''))
                mc4.metric("⭐ 종합",    f"{scores.get('composite',0):.0f}점", ext_result.get('overall_gate',''))

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

                st.markdown("**📊 G3 시장성 요약**")
                g3c1, g3c2, g3c3 = st.columns(3)
                g3c1.metric("TAM", f"${ext_tam/1e6:.0f}M")
                g3c2.metric("성장률", f"{ext_growth:.1f}%/yr")
                g3c3.metric("경쟁사 분석", f"{g3_s.get('competitors_analyzed',0)}개사")

                next_steps = ext_result.get("next_steps", [])
                if next_steps:
                    st.markdown("**🗺 권장 다음 단계**")
                    for ns in next_steps[:5]:
                        st.markdown(f"- {ns}")

                for sn, sk, score_key in [(1,'step2_pcml','pcml'),(2,'step3_scr','scr'),(3,'step4_g3','g3')]:
                    s = chain.get(sk, {})
                    if s.get('gate'):
                        st.session_state.stage_gates[sn] = {"gate": s['gate'], "score": scores.get(score_key, 0)}
                _save_gate(1, {"gate": ext_result.get('overall_gate',''), "score": scores.get('composite',0), "next_actions": next_steps})

                with st.expander("전체 JSON"):
                    render_output_doc(ext_result, collapsed=True)
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
                    render_output_doc(result, collapsed=True)

    with tab_fto:
        st.subheader("경쟁사·침해 모니터링")
        if st.button("▶ 경쟁사 동향 조회"):
            result = api_get(f"/result/{st.session_state.tech_id}")
            if result:
                render_output_doc(result)
            else:
                st.info("아직 분석 결과가 없습니다. IP 전주기 분석을 먼저 실행하세요.")


# ════════════════════════════════════════════════════════════════
# S04 — G4 인터뷰 보드 (칸반 + JTBD + LoI)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g4":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("🤝 G4 고객검증 — NSF I-Corps 인터뷰 보드")
    render_stage_bar(current=4)

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
                    st.session_state.g4_data["interview_count"] = new_total
                    if loi_yn:
                        st.session_state.g4_data["loi_count"] = \
                            st.session_state.g4_data.get("loi_count", 0) + 1
                    if poc_yn:
                        st.session_state.g4_data["poc_requests"] = \
                            st.session_state.g4_data.get("poc_requests", 0) + 1
                    if wtp > 0:
                        prev_sum   = st.session_state.g4_data.get("_wtp_sum", 0)
                        prev_count = st.session_state.g4_data.get("_wtp_count", 0)
                        st.session_state.g4_data["_wtp_sum"]   = prev_sum + wtp
                        st.session_state.g4_data["_wtp_count"] = prev_count + 1
                        st.session_state.g4_data["wtp_avg_krw"] = \
                            (prev_sum + wtp) // (prev_count + 1)
                    if new_total >= 100:
                        st.balloons()
                    st.rerun()

    with tab_board:
        if data and data.get("interviews"):
            import pandas as pd
            interviews = data["interviews"]
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
                    render_output_doc(result.get("loi_template", result), title="LoI 템플릿", collapsed=True)


# ════════════════════════════════════════════════════════════════
# G5 — 사업화전략 (BM Canvas + GTM + Unit Economics + SMK + 로드맵)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g5":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("💼 G5 — 사업화전략")
    render_stage_bar(current=5)

    g4 = st.session_state.g4_data
    if g4:
        st.info(f"✅ G4 데이터 자동 인계됨 — LoI {g4.get('loi_count',0)}건 · 인터뷰 {g4.get('interview_count',0)}건")

    tab_bm, tab_ue, tab_smk, tab_rm = st.tabs([
        "🎨 BM Canvas", "💰 Unit Economics", "🚀 SMK 사업화키트", "🗺️ 실행 로드맵"
    ])

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
                    row1 = st.columns(5)
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
                        tags_html = "".join(
                            f"<span class='bm-tag'>{i}</span>" for i in items[:4]
                        )
                        col.markdown(
                            f"<div class='bm-card'>"
                            f"<div class='bm-card-hdr'><span class='bm-card-title'>{title}</span></div>"
                            f"<div>{tags_html}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    c_cost, c_rev = st.columns(2)
                    for col, title, key, tag_cls in [
                        (c_cost,"💸 비용 구조","cost_structure","bm-tag-yellow"),
                        (c_rev, "💰 수익 흐름","revenue_streams","bm-tag-green"),
                    ]:
                        items = canvas.get(key, [])
                        items = items if isinstance(items, list) else [items]
                        tags_html = "".join(
                            f"<span class='bm-tag {tag_cls}'>{i}</span>" for i in items[:4]
                        )
                        col.markdown(
                            f"<div class='bm-card highlight'>"
                            f"<div class='bm-card-hdr'><span class='bm-card-title'>{title}</span></div>"
                            f"<div>{tags_html}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                if out.get("smk_triggered"):
                    st.success("✅ SMK(사업화시장키트) 자동 생성 완료")
                with st.expander("전체 결과 JSON"):
                    render_output_doc(result, collapsed=True)

    with tab_ue:
        st.subheader("Unit Economics 분석")
        _g4 = st.session_state.get("g4_data", {})
        _wtp_avg = _g4.get("wtp_avg_krw", 0)
        if _wtp_avg:
            st.markdown(f'<div class="ok-card">✅ G4 인터뷰 데이터 인계 — WTP 평균 {_wtp_avg:,.0f}원/월 ({_g4.get("interview_count",0)}건)</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            cac   = st.number_input("CAC (원)",  min_value=0, value=500_000, step=50_000)
            ltv   = st.number_input("LTV (원)",  min_value=0, value=3_000_000, step=100_000)
            churn = st.slider("Churn율 (%/월)", 0.0, 30.0, 5.0)
        with col2:
            arpu = st.number_input("ARPU (원/월)", min_value=0,
                                   value=int(_wtp_avg) if _wtp_avg else 200_000, step=10_000)
            gm   = st.slider("Gross Margin (%)", 0, 100, 70)
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
                    render_output_doc(r, collapsed=True)

    with tab_smk:
        st.subheader("🚀 SMK — 사업화시장키트 (S·M·K)")
        st.caption("G3 시장분석 + G4 고객검증 + G5 BM을 통합해 GTM 실행 키트를 자동 생성합니다.")
        _g3_tam_default  = int(st.session_state.get("g3_tam", 500))
        # G3 성장률은 g3_growth 키로 저장됨 (g3_grow는 구 키명)
        _g3_grow_default = float(st.session_state.get("g3_growth", st.session_state.get("g3_grow", 8.0)))
        if _g3_tam_default != 500 or _g3_grow_default != 8.0:
            st.markdown('<div class="ok-card">✅ G3 시장성 분석 데이터 자동 인계됨</div>', unsafe_allow_html=True)
        g3_tam  = st.number_input("TAM (백만 USD)", min_value=0, value=_g3_tam_default, key="smk_tam")
        g3_grow = st.number_input("시장 성장률 (%)", min_value=0.0, value=_g3_grow_default, key="smk_grow")
        if st.button("⚡ SMK 통합 생성 (G3+G4+G5)", type="primary", key="smk_run"):
            with st.spinner("SMK 생성 중... (30~60초)"):
                r = api_post("/service/smk-from-pipeline", {
                    "tech_id": st.session_state.tech_id,
                    "tech_name": st.session_state.tech_name,
                    "g3_data": {"tam_usd_million": g3_tam, "growth_rate": g3_grow / 100},
                    "g4_data": st.session_state.g4_data or {},
                    "g5_data": st.session_state.g5_data or {},
                })
            if r:
                out = r.get("output_doc", r)
                st.success("✅ SMK 생성 완료")
                # 핵심 출력 요약
                for key, label in [
                    ("value_proposition", "📌 핵심 가치"),
                    ("gtm_strategy", "🎯 GTM 전략"),
                    ("pricing_strategy", "💰 가격 전략"),
                    ("competitive_positioning", "🏆 경쟁 포지셔닝"),
                ]:
                    val = out.get(key)
                    if val:
                        st.markdown(f"**{label}**")
                        st.info(val if isinstance(val, str) else str(val))
                with st.expander("전체 SMK JSON"):
                    render_output_doc(r, collapsed=True)

    if st.session_state.pop("_g5_tab", None) == "roadmap":
        st.markdown('<div class="info-card">📌 <b>전체 로드맵 페이지</b>는 이 탭으로 통합되었습니다 — 아래 🗺️ 실행 로드맵 탭을 사용하세요.</div>', unsafe_allow_html=True)

    with tab_rm:
        st.subheader("🗺️ 실행 로드맵")
        st.caption("사업화전략을 G-Stage별 마일스톤 로드맵으로 구체화합니다.")
        trl_cur = st.slider("현재 TRL", 1, 9, st.session_state.trl, key="rm_cur")
        trl_tgt = st.slider("목표 TRL", trl_cur, 9, 9, key="rm_tgt")
        tech_type_rm = st.selectbox("기술 유형", ["general", "biotech", "ICT", "device", "material"], key="rm_ttype")
        region_rm    = st.selectbox("목표 국가", ["KOR", "USA", "EU", "JPN", "CHN"], key="rm_region")
        if st.button("🗺️ 실행 로드맵 생성", type="primary", key="rm_gen"):
            with st.spinner("사업화 로드맵 생성 중..."):
                r = api_post("/g5/roadmap", {
                    "tech_id": st.session_state.tech_id,
                    "input_data": {"tech_name": st.session_state.tech_name,
                                   "trl_current": trl_cur, "trl_target": trl_tgt,
                                   "tech_type": tech_type_rm, "region": region_rm},
                })
            if r:
                out = r.get("output_doc", r)
                ms = out.get("milestones", [])
                if ms:
                    import pandas as pd
                    st.dataframe(pd.DataFrame(ms), use_container_width=True)
                with st.expander("전체 JSON"):
                    render_output_doc(r, collapsed=True)


# ════════════════════════════════════════════════════════════════
# G6 — 가치평가 (DCF / CCA / ROA)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g6":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("💰 G6 기술 가치평가")
    render_stage_bar(current=6)

    tab_dcf, tab_cca, tab_roa, tab_compare = st.tabs(["📈 DCF 수익접근법", "🏪 CCA 시장접근법", "⚙️ ROA 실물옵션", "🔀 방법론 비교"])

    def _g6_revenue_inputs(suffix: str):
        st.subheader("연도별 매출 예측 (USD)")
        revenues = {}
        cols_r = st.columns(5)
        for i, y in enumerate(range(2025, 2030)):
            revenues[str(y)] = cols_r[i].number_input(
                f"{y}", min_value=0, value=int(1e6*(y-2024)), step=100_000, key=f"rev_{suffix}_{y}")
        return revenues

    with tab_dcf:
        st.markdown('<div class="info-card">💡 미래 현금흐름을 할인율로 현재가치화합니다. 수익성이 명확한 기술에 적합합니다.</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            disc_dcf = st.slider("할인율 WACC (%)", 5, 40, 15, key="g6_disc_dcf") / 100
            royalty_dcf = st.slider("로열티율 (%)", 1, 20, 5, key="g6_roy_dcf") / 100
        with c2:
            growth_dcf = st.slider("터미널 성장률 (%)", 0, 10, 3, key="g6_grow_dcf") / 100
            tax_dcf = st.slider("법인세율 (%)", 10, 40, 22, key="g6_tax_dcf") / 100
        rev_dcf = _g6_revenue_inputs("dcf")
        if st.button("▶ DCF 가치평가 실행", type="primary", key="g6_run_dcf"):
            with st.spinner("DCF 계산 중..."):
                result = api_post("/valuation/dcf", {
                    "tech_id": st.session_state.tech_id, "tech_name": st.session_state.tech_name,
                    "revenue_forecast": rev_dcf, "discount_rate": disc_dcf,
                    "royalty_rate": royalty_dcf, "terminal_growth": growth_dcf, "tax_rate": tax_dcf,
                    "method": "dcf",
                })
            if result:
                _save_gate(6, result)
                st.session_state["_g6_dcf_result"] = result
                out = result.get("output_doc", result)
                val = out.get("valuation_usd") or out.get("npv_usd") or out.get("value_usd", 0)
                st.metric("DCF 기술 가치 (NPV)", f"${val:,.0f}" if val else "산출 불가")
                render_gate_card(result.get("gate",""), float(result.get("score",0)),
                                 "G6 DCF 가치평가", result.get("next_actions",[]))
                with st.expander("DCF 상세"):
                    render_output_doc(result)
        elif st.session_state.get("_g6_dcf_result"):
            r = st.session_state["_g6_dcf_result"]
            out = r.get("output_doc", r)
            val = out.get("valuation_usd") or out.get("npv_usd") or out.get("value_usd", 0)
            st.metric("DCF 기술 가치 (NPV)", f"${val:,.0f}" if val else "산출 불가")

    with tab_cca:
        st.markdown('<div class="info-card">💡 유사 거래/기업 사례와 비교하여 상대적 가치를 산정합니다. 시장 데이터가 풍부한 기술에 적합합니다.</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            sector = st.selectbox("산업 섹터", ["ICT/SW","바이오/의료","소재/화학","기계/장비","에너지","기타"], key="g6_sector")
            mkt_mult = st.slider("EV/EBITDA 배수 (배)", 3, 30, 10, key="g6_mult")
        with c2:
            comp_rev = st.number_input("비교 기업 연매출 (USD)", min_value=0, value=5_000_000, step=100_000, key="g6_comp_rev")
            tech_share = st.slider("기술 기여도 (%)", 5, 80, 30, key="g6_tshare") / 100
        if st.button("▶ CCA 가치평가 실행", type="primary", key="g6_run_cca"):
            with st.spinner("CCA 계산 중..."):
                result = api_post("/valuation/dcf", {
                    "tech_id": st.session_state.tech_id, "tech_name": st.session_state.tech_name,
                    "method": "cca", "sector": sector, "ev_ebitda_multiple": mkt_mult,
                    "comparable_revenue": comp_rev, "tech_contribution": tech_share,
                })
            if result:
                _save_gate(6, result)
                st.session_state["_g6_cca_result"] = result
                out = result.get("output_doc", result)
                val = out.get("valuation_usd") or out.get("value_usd", 0)
                st.metric("CCA 기술 가치", f"${val:,.0f}" if val else "산출 불가")
                with st.expander("CCA 상세"):
                    render_output_doc(result)
        elif st.session_state.get("_g6_cca_result"):
            r = st.session_state["_g6_cca_result"]
            out = r.get("output_doc", r)
            val = out.get("valuation_usd") or out.get("value_usd", 0)
            st.metric("CCA 기술 가치", f"${val:,.0f}" if val else "산출 불가")

    with tab_roa:
        st.markdown('<div class="info-card">💡 블랙-숄즈 모델로 미래 불확실성(옵션가치)을 반영합니다. R&D 초기 단계·혁신 기술에 적합합니다.</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            asset_val = st.number_input("기초자산 가치 (USD, 예상 매출 PV)", min_value=0, value=5_000_000, step=100_000, key="g6_roa_asset")
            invest_cost = st.number_input("투자 비용 (USD, 행사가격)", min_value=0, value=2_000_000, step=100_000, key="g6_roa_cost")
        with c2:
            volatility = st.slider("변동성 σ (%)", 10, 100, 40, key="g6_vol") / 100
            time_yr = st.slider("옵션 만기 (년)", 1, 10, 3, key="g6_time")
            risk_free = st.slider("무위험이자율 (%)", 1, 10, 4, key="g6_rfr") / 100
        if st.button("▶ ROA 가치평가 실행", type="primary", key="g6_run_roa"):
            with st.spinner("블랙-숄즈 계산 중..."):
                result = api_post("/valuation/dcf", {
                    "tech_id": st.session_state.tech_id, "tech_name": st.session_state.tech_name,
                    "method": "roa", "asset_value": asset_val, "investment_cost": invest_cost,
                    "volatility": volatility, "time_to_expiry": time_yr, "risk_free_rate": risk_free,
                })
            if result:
                _save_gate(6, result)
                st.session_state["_g6_roa_result"] = result
                out = result.get("output_doc", result)
                val = out.get("valuation_usd") or out.get("option_value_usd") or out.get("value_usd", 0)
                st.metric("ROA 옵션 가치", f"${val:,.0f}" if val else "산출 불가")
                with st.expander("ROA 상세"):
                    render_output_doc(result)
        elif st.session_state.get("_g6_roa_result"):
            r = st.session_state["_g6_roa_result"]
            out = r.get("output_doc", r)
            val = out.get("valuation_usd") or out.get("option_value_usd") or out.get("value_usd", 0)
            st.metric("ROA 옵션 가치", f"${val:,.0f}" if val else "산출 불가")

    with tab_compare:
        st.markdown("### 🔀 3가지 방법론 비교 분석")
        dcf_r = st.session_state.get("_g6_dcf_result")
        cca_r = st.session_state.get("_g6_cca_result")
        roa_r = st.session_state.get("_g6_roa_result")
        _done = [x for x in [dcf_r, cca_r, roa_r] if x]
        if not _done:
            st.markdown('<div class="warn-card">⚠️ 비교를 위해 최소 1개 이상의 방법론을 먼저 실행하세요.</div>', unsafe_allow_html=True)
        else:
            def _get_val(r):
                if not r: return None
                out = r.get("output_doc", r)
                return out.get("valuation_usd") or out.get("npv_usd") or out.get("option_value_usd") or out.get("value_usd")
            vals = {"DCF": _get_val(dcf_r), "CCA": _get_val(cca_r), "ROA": _get_val(roa_r)}
            avail = {k: v for k, v in vals.items() if v is not None}
            cols_m = st.columns(len(avail))
            for i, (mname, mval) in enumerate(avail.items()):
                cols_m[i].metric(f"{mname} 가치", f"${mval:,.0f}")
            if len(avail) >= 2:
                mvals = list(avail.values())
                avg_val = sum(mvals) / len(mvals)
                lo_val  = min(mvals)
                hi_val  = max(mvals)
                st.markdown(f"""
<div class="ok-card">
<b>📊 종합 가치 범위</b><br>
최저: <b>${lo_val:,.0f}</b> | 평균: <b>${avg_val:,.0f}</b> | 최고: <b>${hi_val:,.0f}</b><br>
<small>⚡ 가중 평균 적용 시 시장 상황에 따라 보수적(DCF 50%, CCA 30%, ROA 20%) 또는 낙관적 조정 가능</small>
</div>""", unsafe_allow_html=True)
                try:
                    import plotly.graph_objects as go
                    fig = go.Figure(go.Bar(
                        x=list(avail.keys()), y=list(avail.values()),
                        marker_color=["#3b82f6","#8b5cf6","#22c55e"][:len(avail)],
                        text=[f"${v:,.0f}" for v in avail.values()], textposition="auto"
                    ))
                    fig.update_layout(title="방법론별 가치 비교 (USD)", height=280, margin=dict(t=40,b=20))
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass
            gate_result = next((r for r in [dcf_r, cca_r, roa_r] if r and r.get("gate")), None)
            if gate_result:
                render_gate_card(gate_result.get("gate",""), float(gate_result.get("score",0)),
                                 "G6 가치평가 종합", gate_result.get("next_actions",[]))


# ════════════════════════════════════════════════════════════════
# G10 KPI 대시보드
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g10":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("📈 G10 성과 모니터링")
    render_stage_bar(current=10)

    KPI_META = {
        "revenue_usd":                ("매출액",     "USD", 1_000_000),
        "royalty_usd":                ("로열티",     "USD",   100_000),
        "investment_raised_usd":      ("투자유치",   "USD",   500_000),
        "poc_to_commercial_rate_pct": ("PoC→사업화", "%",          30),
        "tech_utilization_rate_pct":  ("기술활용율", "%",          70),
        "new_customers":              ("신규고객",   "건",         10),
    }

    tab_dash, tab_gate_map, tab_record, tab_alert = st.tabs(["📊 대시보드", "🗺️ 전체 게이트 현황", "✏️ KPI 기록", "🔔 알림"])

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

    with tab_gate_map:
        st.subheader("🗺️ G0~G10 전체 게이트 현황")
        st.caption("현재 기술의 각 Stage Gate 판정 결과를 한눈에 확인합니다.")
        gates = st.session_state.get("stage_gates", {})
        if not gates:
            st.markdown('<div class="warn-card">⚠️ 아직 평가된 Gate가 없습니다. G0부터 순서대로 분석을 진행하세요.</div>', unsafe_allow_html=True)
        else:
            try:
                import plotly.graph_objects as go
                x_labels = [f"G{i}" for i in range(11)]
                y_scores = [gates.get(i, {}).get("score", 0) for i in range(11)]
                gate_vals = [gates.get(i, {}).get("gate", "—") for i in range(11)]
                colors = [
                    "#4ade80" if g == "Go" else "#eab308" if g == "Hold" else
                    "#ef4444" if g == "Kill" else "#334155"
                    for g in gate_vals
                ]
                fig = go.Figure(go.Bar(
                    x=x_labels, y=y_scores, marker_color=colors,
                    text=[f"{g}<br>{s:.0f}점" if s > 0 else g for g, s in zip(gate_vals, y_scores)],
                    textposition="auto",
                ))
                fig.update_layout(
                    title=f"{st.session_state.tech_name or '기술'} — G0~G10 Gate 현황",
                    yaxis=dict(range=[0, 110], title="점수"),
                    height=320, margin=dict(t=50, b=20),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"),
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

            completed = sum(1 for i in range(11) if i in gates)
            go_cnt    = sum(1 for i in range(11) if gates.get(i, {}).get("gate") == "Go")
            hold_cnt  = sum(1 for i in range(11) if gates.get(i, {}).get("gate") == "Hold")
            kill_cnt  = sum(1 for i in range(11) if gates.get(i, {}).get("gate") == "Kill")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("평가 완료", f"{completed}/11")
            mc2.metric("🟢 Go", go_cnt)
            mc3.metric("🟡 Hold", hold_cnt)
            mc4.metric("🔴 Kill", kill_cnt)

            st.markdown("**상세 Gate 결과**")
            for i in range(11):
                if i in gates:
                    g = gates[i]
                    icon = "🟢" if g["gate"]=="Go" else "🟡" if g["gate"]=="Hold" else "🔴"
                    gid, gname, _ = STAGE_META.get(i, (f"G{i}", f"Stage {i}", "📌"))
                    st.markdown(
                        f"<div class='gate-card-v2 {'go' if g['gate']=='Go' else 'hold' if g['gate']=='Hold' else 'kill'}' "
                        f"style='padding:10px 16px;margin:4px 0'>"
                        f"{icon} <b>{gid} {gname}</b> — {g['gate']} "
                        f"<span style='float:right;font-size:22px;font-weight:800'>{g['score']:.0f}</span></div>",
                        unsafe_allow_html=True,
                    )

        audit = st.session_state.get("gate_audit", [])
        if audit:
            st.divider()
            st.markdown(f"**📋 Gate 결정 이력 ({len(audit)}건)**")
            for entry in reversed(audit[-10:]):
                icon = "🟢" if entry["gate"]=="Go" else "🟡" if entry["gate"]=="Hold" else "🔴"
                st.caption(f"{entry['date']} {entry['ts']} | {entry['icon']} {entry['name']} | {icon} {entry['gate']} {entry['score']:.0f}점")

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
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("📄 보고서 파이프라인 센터")
    render_stage_bar()

    _REPORT_META_UI = {
        "R1_investment":    ("💰", "R1 투자·인수 심사",   "PCML 기반 투자 타당성"),
        "R2_enforcement":   ("⚖️", "R2 권리행사·분쟁",    "FTO · 분쟁 전략"),
        "R3_commercialize": ("🚀", "R3 사업화·R&D 실행",  "TRL 로드맵 + BM"),
        "R4_portfolio":     ("📋", "R4 포트폴리오·제출",  "Asset Tier · HHI"),
        "R5_valuation":     ("📊", "R5 기술가치평가",     "3접근법 + WACC"),
        "R6_ir":            ("📈", "R6 투자자 IR 브리프", "IR Deck 요약"),
        "R7_license":       ("🤝", "R7 라이선스·기술이전","Term Sheet 자동"),
        "R8_gov_ir":        ("🏛️", "R8 정부지원·IR 제출", "KIAT/KEIT 제출용"),
        "R9_sps":           ("🔍", "R9 선행기술조사(SPS)","신규성·진보성 분석"),
    }

    # G9에서 넘어온 prefill 처리
    _prefill = st.session_state.pop("_rpt_prefill", None)
    if _prefill:
        _prid   = _prefill.get("report_id", "")
        _pname  = _REPORT_META_UI.get(_prid, ("📄", _prid, ""))[1]
        st.markdown(f'<div class="ok-card">✅ G9에서 전달된 <b>{_pname}</b> 결과가 저장 탭에 표시됩니다.</div>', unsafe_allow_html=True)
        st.session_state["_g9_prefill_saved"] = _prefill

    tab_pipe, tab_saved, tab_history = st.tabs([
        "⚡ 보고서 생성 파이프라인", "📂 저장된 보고서", "🕑 파이프라인 이력"
    ])

    # ── 탭1: 파이프라인 ─────────────────────────────────────────
    with tab_pipe:
        st.markdown(
            "<div style='background:#1e293b;border:1px solid #334155;border-radius:10px;"
            "padding:16px 20px;margin-bottom:20px'>"
            "<div style='font-size:13px;font-weight:700;color:#e2e8f0;margin-bottom:6px'>"
            "📌 파이프라인 흐름</div>"
            "<div style='font-size:12px;color:#94a3b8'>"
            "입력 텍스트 · TRL → "
            "<span style='color:#60a5fa'>PCML 분석(StoreA)</span> → "
            "<span style='color:#34d399'>SCR 스크리닝(StoreB)</span> → "
            "<span style='color:#f59e0b'>보고서 선택</span> → "
            "<span style='color:#a78bfa'>LLM 생성</span> → "
            "SQLite 저장 · 다운로드</div></div>",
            unsafe_allow_html=True,
        )

        col_l, col_r = st.columns([2, 1])
        with col_l:
            pipe_text = st.text_area(
                "분석 텍스트 (특허·기술·사업계획)",
                value=st.session_state.get("home_text", ""),
                height=120,
                placeholder="특허 청구항, 기술 개요, 사업계획서 내용 붙여넣기...",
                key="rpt_pipe_text",
            )
        with col_r:
            pipe_trl = st.slider("현재 TRL", 1, 9, st.session_state.trl, key="rpt_trl")
            pipe_tier = st.selectbox("보고서 등급", ["LITE", "FREE", "FULL"],
                                     help="LITE=요약 / FULL=전체 (LLM 키 필요)", key="rpt_tier")

        # 보고서 선택 체크박스
        st.markdown("**생성할 보고서 선택** (빈 선택 = AI 추천 3개 자동)")
        cols_cb = st.columns(3)
        selected_reports = []
        for i, (rid, (icon, label, desc)) in enumerate(_REPORT_META_UI.items()):
            with cols_cb[i % 3]:
                if st.checkbox(f"{icon} {label}", key=f"cb_{rid}", help=desc):
                    selected_reports.append(rid)

        # PCML/SCR 결과 직접 입력 (고급)
        with st.expander("⚙️ 고급: PCML/SCR 결과 직접 입력 (선택)"):
            col_a, col_b = st.columns(2)
            with col_a:
                store_a_json = st.text_area("StoreA (PCML JSON)", height=100,
                                            placeholder='{"pcml_score": 72, ...}',
                                            key="rpt_store_a")
            with col_b:
                store_b_json = st.text_area("StoreB (SCR JSON)", height=100,
                                            placeholder='{"gate": "Go", "scr_score": 68, ...}',
                                            key="rpt_store_b")

        if st.button("⚡ 파이프라인 실행", type="primary", use_container_width=True,
                     key="run_pipeline_btn"):
            tech_id   = st.session_state.tech_id or f"TECH-{int(time.time())}"
            tech_name = st.session_state.tech_name or "미입력 기술"

            store_a_in = {}
            store_b_in = {}
            try:
                if store_a_json.strip():
                    store_a_in = json.loads(store_a_json)
            except Exception:
                st.warning("StoreA JSON 파싱 실패 — 자동 생성으로 대체")
            try:
                if store_b_json.strip():
                    store_b_in = json.loads(store_b_json)
            except Exception:
                st.warning("StoreB JSON 파싱 실패 — 자동 생성으로 대체")

            payload = {
                "tech_id":    tech_id,
                "tech_name":  tech_name,
                "input_text": pipe_text,
                "trl":        pipe_trl,
                "tier":       pipe_tier,
                "report_ids": selected_reports,
                "store_a":    store_a_in,
                "store_b":    store_b_in,
            }

            with st.spinner("파이프라인 실행 중... (LLM 사용 시 30~90초)"):
                result = api_post("/reports/pipeline", payload)

            if result:
                st.session_state["_rpt_pipeline_result"] = result
                st.success(f"✅ 보고서 {len(result.get('generated', []))}건 생성 완료")

        # 결과 표시
        pr = st.session_state.get("_rpt_pipeline_result")
        if pr:
            st.markdown("---")
            # 추천 보고서 표시
            recs = pr.get("recommended", [])
            if recs:
                st.markdown("**🤖 AI 추천 보고서 우선순위**")
                rec_html = "<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px'>"
                for r in recs:
                    color = {"🔴 필수": "#dc2626", "🟠 권장": "#ea580c", "🟡 선택": "#ca8a04"}.get(r.get("priority",""), "#475569")
                    rec_html += (
                        f"<div style='background:#1e293b;border:1px solid #334155;"
                        f"border-radius:8px;padding:8px 12px;font-size:11px'>"
                        f"<span style='color:{color};font-weight:700'>{r.get('priority','')}</span> "
                        f"{r.get('icon','')} {r.get('label',r.get('id',''))}<br>"
                        f"<span style='color:#94a3b8'>{r.get('reason','')}</span></div>"
                    )
                rec_html += "</div>"
                st.markdown(rec_html, unsafe_allow_html=True)

            # 생성된 보고서
            for gen in pr.get("generated", []):
                icon  = gen.get("icon", "📄")
                label = gen.get("label", gen["report_id"])
                fallback = gen.get("fallback", False)
                db_id = gen.get("db_id", "")

                badge = "⚠️ 폴백" if fallback else "✅ LLM"
                with st.expander(f"{icon} {label} [{gen['tier']}] {badge}", expanded=True):
                    findings = gen.get("key_findings", [])
                    if findings:
                        st.markdown("**핵심 결론**")
                        for f in findings:
                            st.markdown(f"- {f}")
                    st.markdown("**미리보기**")
                    st.markdown(gen.get("content_preview", ""))

                    # 전체 보고서 다운로드
                    full = api_get(f"/reports/db/{db_id}", silent=True)
                    if full:
                        content_md = full.get("content_md", "")
                        st.download_button(
                            f"⬇️ {label} 다운로드 (MD)",
                            data=content_md.encode("utf-8"),
                            file_name=f"{gen['report_id']}_{pr['tech_id']}.md",
                            mime="text/markdown",
                            key=f"dl_{db_id}",
                        )

    # ── 탭2: 저장된 보고서 ──────────────────────────────────────
    with tab_saved:
        tech_filter = st.session_state.tech_id
        saved = api_get(f"/reports/db/list?tech_id={tech_filter}", silent=True) or []
        if not saved:
            saved = api_get("/reports/db/list", silent=True) or []

        if not saved:
            st.info("아직 생성된 보고서가 없습니다. 파이프라인을 실행하세요.")
        else:
            st.markdown(f"**{len(saved)}개 보고서 저장됨**")
            for rpt in saved:
                rid   = rpt.get("report_id", "")
                meta  = _REPORT_META_UI.get(rid, ("📄", rid, ""))
                icon, label = meta[0], meta[1]
                created = rpt.get("created_at", 0)
                ts = datetime.datetime.fromtimestamp(created).strftime("%m/%d %H:%M") if created else "?"
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"{icon} **{label}** · `{rpt['tech_id']}` · {ts}")
                with col2:
                    st.markdown(f"`{rpt.get('tier','?')}`")
                with col3:
                    content_md = rpt.get("content_md", "")
                    if content_md:
                        st.download_button(
                            "⬇️ MD", data=content_md.encode("utf-8"),
                            file_name=f"{rid}_{rpt['tech_id']}.md",
                            mime="text/markdown",
                            key=f"saved_dl_{rpt['id']}",
                        )
                st.divider()

    # ── 탭3: 파이프라인 이력 ────────────────────────────────────
    with tab_history:
        runs = api_get("/reports/runs/list", silent=True) or []
        if not runs:
            st.info("파이프라인 실행 이력이 없습니다.")
        else:
            st.markdown(f"**최근 {len(runs)}건 실행 이력**")
            for run in runs:
                ts = datetime.datetime.fromtimestamp(run.get("created_at", 0)).strftime("%Y/%m/%d %H:%M")
                reports_list = json.loads(run.get("reports_generated", "[]")) if isinstance(run.get("reports_generated"), str) else []
                with st.expander(f"🔹 {run.get('tech_name','?')} · {ts} · {len(reports_list)}건"):
                    st.markdown(f"**기술 ID**: `{run.get('tech_id','?')}`")
                    st.markdown(f"**TRL**: {run.get('trl','?')}")
                    st.markdown(f"**생성 보고서**: {', '.join(reports_list)}")
                    preview = run.get("input_text", "")[:200]
                    if preview:
                        st.caption(f"입력 미리보기: {preview}…")


# ════════════════════════════════════════════════════════════════
# 전체 로드맵
# ════════════════════════════════════════════════════════════════
# G0 — 기술발굴 (IDF + 수요조사 + TechScout)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g0":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("🔭 G0 — 기술발굴")
    render_stage_bar(current=0)

    tab_scout, tab_idf, tab_demand, tab_validate = st.tabs(["🔭 TechScout", "📄 IDF 발명공개서", "📋 수요조사서", "✅ 기술성립 검증"])

    with tab_scout:
        st.subheader("기술 후보 발굴 및 분류")
        tech_kw = st.text_area("기술 키워드 또는 발명 아이디어", height=100,
                               placeholder="예) 딥러닝 기반 작물 생장 예측 시스템...")
        kw_domain = st.selectbox("기술 도메인", ["AI/SW", "바이오", "소재", "기계장치", "ICT", "에너지", "환경"])
        if st.button("🔭 기술 발굴 분석", type="primary", disabled=not tech_kw.strip()):
            with st.spinner("기술 후보 분류 중..."):
                r = api_post("/stage/0", {"tech_id": st.session_state.tech_id or "G0-NEW",
                                          "input_data": {"tech_description": tech_kw, "domain": kw_domain}})
            if r:
                _save_gate(0, r)
                render_gate_card(r.get("gate",""), float(r.get("score",0)), "G0 기술발굴", r.get("next_actions",[]))
                if r.get("gate") == "Go":
                    if st.button("▶ G1 IP 구조화로 이동", type="primary"):
                        st.session_state.page = "g1"; st.rerun()

    with tab_idf:
        st.subheader("IDF 발명공개서 자동 생성")
        idf_text = st.text_area("발명 설명 (기술적 특징·효과·활용분야)", height=150,
                                placeholder="예) 본 발명은 센서 데이터와 기상 데이터를 결합하여...")
        if st.button("📄 IDF 생성", type="primary", disabled=not idf_text.strip()):
            with st.spinner("IDF 생성 중..."):
                r = api_post("/service/demand-survey", {"tech_id": st.session_state.tech_id or "G0",
                                                        "input_data": {"tech_description": idf_text}})
            if r:
                st.success("✅ IDF 생성 완료")
                render_output_doc(r.get("output_doc", r))

    with tab_demand:
        st.subheader("수요조사서 자동 생성")
        ds_tech = st.text_area("기술 개요", height=100)
        ds_seg  = st.text_input("목표 시장 세그먼트", placeholder="예) 국내 스마트팜 온실 농가")
        if st.button("📋 수요조사서 생성", type="primary", disabled=not ds_tech.strip()):
            with st.spinner("수요조사서 생성 중..."):
                r = api_post("/service/demand-survey", {"tech_id": st.session_state.tech_id or "G0",
                                                        "input_data": {"tech_description": ds_tech,
                                                                       "target_segment": ds_seg}})
            if r:
                st.success("✅ 수요조사서 생성 완료")
                render_output_doc(r.get("output_doc", r))

    with tab_validate:
        st.subheader("✅ 기술성립 검증 (G0 → G1 진입 전 체크)")
        st.caption("기술이 G1 IP 구조화로 진입하기 전, 3가지 관문을 사전 점검합니다.")

        st.markdown("#### 1️⃣ 기술 독자성 자가 체크")
        check_cols = st.columns(3)
        chk1 = check_cols[0].checkbox("신규성 — 기존 공개 기술과 명확히 구별됨")
        chk2 = check_cols[1].checkbox("진보성 — 당업자가 쉽게 도달할 수 없는 개선")
        chk3 = check_cols[2].checkbox("산업적 이용가능성 — 실제 제품·서비스에 적용 가능")
        passed_prelim = sum([chk1, chk2, chk3])
        if passed_prelim == 3:
            st.markdown('<div class="ok-card">🟢 3/3 충족 — G1 진입 조건 사전 충족</div>', unsafe_allow_html=True)
        elif passed_prelim >= 1:
            st.markdown(f'<div class="warn-card">🟡 {passed_prelim}/3 충족 — 부족한 항목 보완 후 진입 권장</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warn-card">🔴 0/3 — IP 등록 가능성 낮음, 기술 개선 필요</div>', unsafe_allow_html=True)

        st.markdown("#### 2️⃣ 선행 기술 AI 분석")
        val_text = st.text_area("검증할 기술 설명", height=120,
                                placeholder="특허 청구항 또는 기술 요약을 입력하세요…",
                                key="g0_val_text")
        val_domain = st.selectbox("기술 도메인", ["AI/SW", "바이오", "소재", "기계장치", "ICT", "에너지", "환경"], key="g0_val_dom")
        val_scope  = st.multiselect("검증 범위", ["신규성", "진보성", "FTO(자유실시)", "표준 필수 특허"], default=["신규성", "진보성"], key="g0_val_scope")

        if st.button("🔍 선행기술 검증 실행", type="primary", disabled=not val_text.strip(), key="g0_val_run"):
            with st.spinner("선행기술 분석 중... (15~30초)"):
                r = api_post("/stage/0", {
                    "tech_id": st.session_state.tech_id or "G0-VAL",
                    "input_data": {
                        "tech_description": val_text,
                        "domain": val_domain,
                        "validation_scope": val_scope,
                        "mode": "validation",
                    }
                })
            if r:
                _save_gate(0, r)
                render_gate_card(r.get("gate",""), float(r.get("score",0)), "G0 기술성립 검증", r.get("next_actions",[]))
                out = r.get("output_doc", r)
                novelty   = out.get("novelty_assessment") or out.get("novelty")
                inventive = out.get("inventive_step") or out.get("inventive")
                if novelty:
                    st.markdown(f"**신규성 판단**: {novelty}")
                if inventive:
                    st.markdown(f"**진보성 판단**: {inventive}")
                with st.expander("전체 선행기술 분석 결과"):
                    render_output_doc(r, collapsed=True)
                if r.get("gate") == "Go":
                    if st.button("▶ G1 IP 구조화로 이동", type="secondary", key="g0_val_to_g1"):
                        st.session_state.page = "g1"; st.rerun()

        st.markdown("#### 3️⃣ TRL 0→1 진입 조건 체크리스트")
        trl_checks = {
            "기술 원리가 문헌·논문으로 확인됨": False,
            "유사 기술 대비 차별점 1개 이상 명확화됨": False,
            "발명자가 특정됨 (개인 또는 팀)": False,
            "기술 이전 또는 사업화 의향 확인됨": False,
        }
        all_checked = True
        for label in trl_checks:
            checked = st.checkbox(label, key=f"trl_chk_{label[:10]}")
            if not checked:
                all_checked = False
        if all_checked:
            st.success("✅ 모든 항목 충족 — G1 IP 구조화 진입 준비 완료")
            if st.button("▶ G1 IP 구조화 시작", type="primary", key="g0_to_g1_btn"):
                st.session_state.page = "g1"; st.rerun()


# ════════════════════════════════════════════════════════════════
# G2 — 기술성 평가 (TRL + SCR 신규성·진보성)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g2":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("🧪 G2 — 기술성 평가")
    render_stage_bar(current=2)

    tab_trl, tab_scr, tab_pat = st.tabs(["🧪 TRL 평가", "🔍 SCR 신규성", "⚖️ 권리성 평가"])

    with tab_trl:
        st.subheader("TRL (Technology Readiness Level) 평가")
        trl_tech = st.text_area("기술 설명 (구현 수준·실증 현황)", height=120,
                                placeholder="예) 실험실 수준의 프로토타입을 개발 완료하고, 실내 환경에서 검증 완료...")
        trl_cur2 = st.slider("자가진단 TRL", 1, 9, st.session_state.trl, key="g2_trl")
        if st.button("🧪 TRL 평가 실행", type="primary", disabled=not trl_tech.strip()):
            with st.spinner("TRL 평가 중..."):
                r = api_post("/stage/2", {"tech_id": st.session_state.tech_id or "G2",
                                          "input_data": {"tech_description": trl_tech, "trl_self": trl_cur2}})
            if r:
                _save_gate(2, r)
                out = r.get("output_doc", {})
                trl_result = out.get("trl_level", trl_cur2)
                st.metric("평가 TRL", f"TRL {trl_result}", f"자가진단 대비 {trl_result - trl_cur2:+d}")
                render_gate_card(r.get("gate",""), float(r.get("score",0)), "G2 TRL 평가", r.get("next_actions",[]))
                with st.expander("상세 결과"):
                    render_output_doc(r, collapsed=True)

    with tab_scr:
        st.subheader("SCR — 신규성·진보성 스크리닝 (PQE-SCR v4.0)")
        scr_patent = st.text_area("특허 청구항 또는 기술 내용", height=150,
                                  placeholder="청구항 1: ...",
                                  value=st.session_state.get("_ip_text",""))
        scr_scope = st.selectbox("분석 범위", ["basic", "full"], key="g2_scr_scope")
        if st.button("🔍 SCR 신규성 분석", type="primary", disabled=not scr_patent.strip()):
            with st.spinner("선행기술 조사 중... (30~90초)"):
                r = api_post("/ip/screening", {"patent_text": scr_patent, "scope": scr_scope,
                                               "tech_id": st.session_state.tech_id or "G2"})
            if r:
                _save_gate(2, r)
                out = r.get("output_doc", r)
                novelty = out.get("noveltyAnalysis", {})
                status = novelty.get("status", "")
                color_map = {"novel":"🟢","semi-novel":"🟡","known":"🔴"}
                st.markdown(f"**신규성 판정**: {color_map.get(status,'⚪')} {status}")
                hard_stops = out.get("hardStops", [])
                if hard_stops:
                    st.error(f"⛔ Hard Stop {len(hard_stops)}건: {', '.join(hard_stops[:3])}")
                ws = out.get("whiteSpace", [])
                if ws:
                    st.success(f"✅ 화이트스페이스 {len(ws)}개 식별")
                    for w in ws[:3]:
                        st.info(w if isinstance(w, str) else str(w))
                render_gate_card(r.get("gate",""), float(r.get("score",0)), "G2 SCR", r.get("next_actions",[]))
                with st.expander("전체 SCR 결과"):
                    render_output_doc(r, collapsed=True)

    with tab_pat:
        st.subheader("권리성 평가 (특허 등록 가능성)")
        pat_text = st.text_area("특허 청구항", height=120,
                                value=st.session_state.get("_ip_text",""), key="g2_pat_text")
        if st.button("⚖️ 권리성 평가", type="primary", disabled=not pat_text.strip()):
            with st.spinner("권리성 평가 중..."):
                r = api_post("/ip/patentability", {"patent_text": pat_text,
                                                   "tech_id": st.session_state.tech_id or "G2"})
            if r:
                render_output_doc(r.get("output_doc", r))


# ════════════════════════════════════════════════════════════════
# G3 — 시장성 평가 (TAM/SAM/SOM + 경쟁사 + SMK 시장분석부)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g3":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("🌐 G3 — 시장성 평가")
    render_stage_bar(current=3)

    tab_tam, tab_comp, tab_smk_mkt = st.tabs(["📊 TAM/SAM/SOM", "🥊 경쟁사 분석", "📈 SMK 시장분석"])

    with tab_tam:
        st.subheader("시장 규모 분석 (TAM / SAM / SOM)")
        col1, col2 = st.columns(2)
        with col1:
            tam = st.number_input("TAM (백만 USD)", min_value=0, value=5000, step=100, key="g3_tam")
            growth = st.slider("시장 성장률 (%/년)", 0.0, 50.0, 8.0, key="g3_growth")
        with col2:
            target_mkt_g3 = st.text_input("목표 시장 세그먼트", "국내 스마트팜 온실 농가", key="g3_seg")
            region_g3 = st.selectbox("목표 국가", ["KOR","USA","EU","JPN","CHN"], key="g3_region")
        tech_desc_g3 = st.text_area("기술/제품 설명", height=80, key="g3_desc",
                                    placeholder="예) AI 기반 작물 생장 예측 SaaS...")

        # ── 인터랙티브 퍼널 + 파이 + 성장 전망 차트 (입력값 즉시 반영) ──
        import plotly.graph_objects as go
        import plotly.express as px
        _tam_v = float(tam)
        _sam_v = float(st.session_state.get("_g3_sam_result", _tam_v * 0.1))
        _som_v = float(st.session_state.get("_g3_som_result", _tam_v * 0.01))
        # tam 값이 바뀌면 저장된 비율을 유지하되 절대값 재계산
        _stored_tam = st.session_state.get("_g3_tam_result", _tam_v)
        if _stored_tam and _stored_tam != _tam_v:
            _ratio_sam = _sam_v / _stored_tam if _stored_tam else 0.1
            _ratio_som = _som_v / _stored_tam if _stored_tam else 0.01
            _sam_v = _tam_v * _ratio_sam
            _som_v = _tam_v * _ratio_som

        col_ch1, col_ch2, col_ch3 = st.columns(3)
        with col_ch1:
            fig_f = go.Figure(go.Funnel(
                y=["TAM (전체시장)", "SAM (접근가능)", "SOM (획득가능)"],
                x=[_tam_v, _sam_v, _som_v],
                texttemplate=[f"${_tam_v:,.0f}M", f"${_sam_v:,.0f}M ({_sam_v/_tam_v*100:.1f}%)",
                               f"${_som_v:,.0f}M ({_som_v/_tam_v*100:.1f}%)"] if _tam_v else ["","",""],
                textinfo="text",
                marker_color=["#6366f1","#8b5cf6","#a78bfa"],
                connector={"line": {"color":"rgba(99,102,241,.3)","width":1}},
            ))
            fig_f.update_layout(margin=dict(l=0,r=0,t=28,b=0), height=240,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0", title=dict(text="시장 퍼널", font=dict(size=13)))
            st.plotly_chart(fig_f, use_container_width=True)

        with col_ch2:
            _pie_labels = ["TAM", "SAM", "SOM"]
            _pie_vals   = [_tam_v, _sam_v, _som_v]
            fig_p = px.pie(
                names=_pie_labels, values=_pie_vals,
                color_discrete_sequence=["#6366f1","#8b5cf6","#a78bfa"],
                hole=0.45,
            )
            fig_p.update_traces(
                texttemplate="%{label}<br>$%{value:,.0f}M",
                textposition="inside", textfont_size=11,
            )
            fig_p.update_layout(
                margin=dict(l=0,r=0,t=28,b=0), height=240,
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0", showlegend=False,
                title=dict(text="TAM / SAM / SOM 비율", font=dict(size=13)),
            )
            st.plotly_chart(fig_p, use_container_width=True)

        with col_ch3:
            _yrs = [str(2025+i) for i in range(5)]
            _vals = [_tam_v * ((1+growth/100)**i) for i in range(5)]
            fig_g = go.Figure(go.Bar(
                x=_yrs, y=_vals,
                marker_color=["#6366f1","#7c3aed","#8b5cf6","#a78bfa","#c4b5fd"],
                text=[f"${v:,.0f}M" for v in _vals], textposition="outside",
            ))
            fig_g.update_layout(margin=dict(l=0,r=0,t=28,b=0), height=240,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0", yaxis_visible=False,
                title=dict(text=f"TAM 5년 전망 (CAGR {growth:.1f}%)", font=dict(size=13)))
            st.plotly_chart(fig_g, use_container_width=True)

        if st.button("🌐 시장성 분석 실행", type="primary", disabled=not tech_desc_g3.strip()):
            with st.spinner("시장성 분석 중..."):
                r = api_post("/stage/3", {
                    "tech_id": st.session_state.tech_id or "G3",
                    "input_data": {"tech_description": tech_desc_g3, "tam_usd_million": tam,
                                   "growth_rate": growth/100, "target_market": target_mkt_g3,
                                   "region": region_g3},
                })
            if r:
                _save_gate(3, r)
                out = r.get("output_doc", {})
                _sam_api = float(out.get("sam_usd_million", _tam_v * 0.1))
                _som_api = float(out.get("som_usd_million", _tam_v * 0.01))
                st.session_state["_g3_tam_result"] = _tam_v
                st.session_state["_g3_sam_result"] = _sam_api
                st.session_state["_g3_som_result"] = _som_api
                c1, c2, c3 = st.columns(3)
                c1.metric("TAM", f"${_tam_v:,.0f}M")
                c2.metric("SAM", f"${_sam_api:,.0f}M", delta=f"{_sam_api/_tam_v*100:.1f}% of TAM" if _tam_v else None)
                c3.metric("SOM", f"${_som_api:,.0f}M", delta=f"{_som_api/_tam_v*100:.1f}% of TAM" if _tam_v else None)
                render_gate_card(r.get("gate",""), float(r.get("score",0)), "G3 시장성", r.get("next_actions",[]))
                with st.expander("상세 결과"):
                    render_output_doc(r, collapsed=True)
                st.rerun()  # 퍼널 차트 즉시 갱신

    with tab_comp:
        st.subheader("경쟁사 분석 및 생태계 매핑")
        comp_desc = st.text_area("기술/제품 설명 (경쟁사 분석용)", height=100, key="g3_comp_desc")
        if st.button("🥊 경쟁사 분석", type="primary", disabled=not comp_desc.strip()):
            with st.spinner("경쟁사 분석 중..."):
                r = api_post("/gap/ecosystem-match", {"tech_id": st.session_state.tech_id or "G3",
                                                      "input_data": {"tech_description": comp_desc}})
            if r:
                render_output_doc(r.get("output_doc", r))

    with tab_smk_mkt:
        st.subheader("SMK 시장분석부 — S(전략)·M(시장)·K(킬기준)")
        st.caption("G3 시장 데이터를 기반으로 사업화 킬기준과 전략 방향을 도출합니다.")
        smk_desc = st.text_area("기술/사업 개요", height=100, key="g3_smk_desc")
        smk_tam2 = st.number_input("TAM (백만 USD)", min_value=0, value=500, key="g3_smk_tam")
        if st.button("📈 SMK 시장분석 생성", type="primary", disabled=not smk_desc.strip()):
            with st.spinner("SMK 시장분석 생성 중..."):
                r = api_post("/service/smk", {"tech_id": st.session_state.tech_id or "G3",
                                              "input_data": {"tech_description": smk_desc,
                                                             "tam_usd_million": smk_tam2}})
            if r:
                st.success("✅ SMK 시장분석 완료")
                render_output_doc(r.get("output_doc", r))


# ════════════════════════════════════════════════════════════════
# G7 — PoC 실증 (기술 동작 검증)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g7":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("🔬 G7 — PoC 실증")
    render_stage_bar(current=7)

    st.caption("Proof of Concept — **기술이 명세대로 동작하는가?** 성능·재현성·확장성을 검증합니다.")
    st.info("💡 PoC = 기술 동작 검증 | PoB (G8) = 사업 동작 검증 (유료 고객 존재 여부)")

    tab_plan, tab_result, tab_check = st.tabs(["📋 PoC 계획", "📊 PoC 결과", "✅ 체크리스트"])

    with tab_plan:
        st.subheader("PoC 실증 계획 수립")
        poc_tech = st.text_area("검증 대상 기술 설명", height=100,
                                placeholder="예) 딥러닝 기반 작물 수확량 예측 모델의 실외 온실 적용 검증...")
        poc_kpi  = st.text_area("핵심 성능 지표 (KPI)", height=60,
                                placeholder="예) 예측 정확도 ≥85%, 추론 속도 ≤200ms, 연속 30일 무중단...")
        poc_env  = st.text_input("실증 환경", placeholder="예) 경남 밀양 딸기 온실 3동, 센서 12개")
        poc_dur  = st.number_input("실증 기간 (일)", min_value=1, value=30)
        if st.button("📋 PoC 계획 생성", type="primary", disabled=not poc_tech.strip()):
            with st.spinner("PoC 계획 생성 중..."):
                r = api_post("/stage/7", {"tech_id": st.session_state.tech_id or "G7",
                                          "input_data": {"tech_description": poc_tech, "kpi_targets": poc_kpi,
                                                         "test_environment": poc_env, "duration_days": poc_dur}})
            if r:
                st.session_state["_poc_plan"] = r.get("output_doc", r)
                st.success("✅ PoC 계획 생성 완료")
                render_output_doc(r.get("output_doc", r))

    with tab_result:
        st.subheader("PoC 결과 등록 및 판정")
        poc_achieved = st.slider("목표 KPI 달성률 (%)", 0, 100, 80)
        poc_issues   = st.text_area("발견된 기술적 이슈", height=80,
                                    placeholder="예) 저조도 환경에서 정확도 12% 하락, 배터리 소모 과다...")
        poc_repro    = st.checkbox("재현성 확인됨 (3회 이상 반복 실험)")
        poc_scale    = st.checkbox("스케일업 가능성 확인됨 (파일럿 → 상용 규모)")
        if st.button("📊 PoC 결과 판정", type="primary"):
            gate_poc = "Go" if (poc_achieved >= 80 and poc_repro) else "Hold" if poc_achieved >= 60 else "Kill"
            score_poc = poc_achieved * 0.6 + (20 if poc_repro else 0) + (20 if poc_scale else 0)
            _save_gate(7, {"gate": gate_poc, "score": min(score_poc, 100),
                           "output_doc": {"kpi_achieved_pct": poc_achieved, "reproducible": poc_repro,
                                          "scalable": poc_scale, "issues": poc_issues}})
            render_gate_card(gate_poc, min(score_poc, 100), "G7 PoC 실증",
                             ["G8 PoB 진행"] if gate_poc == "Go" else ["PoC 재설계", "기술 수정"])
            if gate_poc == "Go":
                if st.button("▶ G8 PoB/MRL로 이동", type="primary"):
                    st.session_state.page = "g8"; st.rerun()

    with tab_check:
        st.subheader("PoC 검증 체크리스트")
        r = api_get("/verify/poc", silent=True)
        if r:
            items = r.get("checklist", [])
            for i, item in enumerate(items):
                st.checkbox(item.get("description", item) if isinstance(item, dict) else item,
                            key=f"poc_ck_{i}")
        else:
            default_checks = [
                "기술 명세서 대비 성능 목표 달성 (KPI ≥목표치)",
                "실험 환경에서 3회 이상 재현 성공",
                "파일럿 규모 확장 시 성능 유지 확인",
                "핵심 리스크 (하드웨어 고장·SW 버그) 해소",
                "PoC 결과보고서 작성 완료",
                "이해관계자 데모 및 피드백 수령",
            ]
            for i, c in enumerate(default_checks):
                st.checkbox(c, key=f"poc_def_{i}")


# ════════════════════════════════════════════════════════════════
# G8 — PoB / MRL / ARL (사업 동작 검증)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g8":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("📊 G8 — PoB / MRL / ARL")
    render_stage_bar(current=8)

    st.caption("Proof of Business — **사업이 실제로 동작하는가?** 초기 유료고객·LTV/CAC 실측·규제 경로를 검증합니다.")

    tab_pob, tab_mrl, tab_reg, tab_team = st.tabs(
        ["💰 PoB 실증", "🏭 MRL / ARL", "📜 규제 경로", "👥 팀 역량"]
    )

    with tab_pob:
        st.subheader("PoB — Proof of Business (사업 동작 검증)")
        st.info("PoB 기준: ① 유료 고객 존재 ② 재구매 또는 계약 갱신 ③ LTV > CAC × 3 이상")
        col1, col2 = st.columns(2)
        with col1:
            paying_cust = st.number_input("초기 유료 고객 수",      min_value=0, value=0)
            acv         = st.number_input("평균 계약 금액 (ACV, USD/년)", min_value=0, value=0, step=1000)
            churn       = st.slider("월 이탈률 (%)", 0.0, 20.0, 5.0)
        with col2:
            ltv         = st.number_input("LTV (USD, 추정)",  min_value=0, value=0, step=1000)
            cac         = st.number_input("CAC (USD, 실측)",  min_value=0, value=0, step=100)
            renew       = st.checkbox("갱신·재구매 1건 이상 확인")
        if st.button("💰 PoB 판정", type="primary"):
            ltv_cac = (ltv / cac) if cac > 0 else 0
            gate_pob = "Go" if (paying_cust >= 1 and ltv_cac >= 3 and renew) else \
                       "Hold" if (paying_cust >= 1 or ltv_cac >= 1) else "Kill"
            score_pob = min(100, paying_cust * 10 + (30 if ltv_cac >= 3 else 15 if ltv_cac >= 1 else 0)
                                + (20 if renew else 0))
            _save_gate(8, {"gate": gate_pob, "score": score_pob,
                           "output_doc": {"paying_customers": paying_cust, "acv_usd": acv,
                                          "ltv_cac_ratio": round(ltv_cac, 2), "renewal": renew}})
            c1, c2, c3 = st.columns(3)
            c1.metric("유료 고객", paying_cust)
            c2.metric("LTV/CAC", f"{ltv_cac:.1f}x", "목표 ≥3x")
            c3.metric("갱신", "✅" if renew else "❌")
            render_gate_card(gate_pob, score_pob, "G8 PoB",
                             ["G9 거래·투자 진행"] if gate_pob == "Go" else ["추가 고객 확보", "CAC 최적화"])
            if gate_pob == "Go":
                if st.button("▶ G9 거래·투자로 이동", type="primary"):
                    st.session_state.page = "g9"; st.rerun()

    with tab_mrl:
        st.subheader("MRL / ARL — 제조·응용 성숙도 평가")
        mrl_text = st.text_area("기술/제품 현황 설명", height=100, key="g8_mrl_desc")
        if st.button("📊 MRL/ARL 평가", type="primary", disabled=not mrl_text.strip()):
            with st.spinner("성숙도 평가 중..."):
                r = api_post("/stage/8", {"tech_id": st.session_state.tech_id or "G8",
                                          "input_data": {"tech_description": mrl_text}})
            if r:
                render_output_doc(r.get("output_doc", r))

    with tab_reg:
        st.subheader("규제·인증 경로 로드맵")
        reg_text = st.text_area("제품/기술 설명 (규제 분석용)", height=100, key="g8_reg_desc")
        reg_region2 = st.selectbox("목표 국가", ["KOR","USA","EU","JPN"], key="g8_reg_region")
        if st.button("📜 규제 경로 분석", type="primary", disabled=not reg_text.strip()):
            with st.spinner("규제 분석 중..."):
                r = api_post("/execution/regulatory", {"tech_id": st.session_state.tech_id or "G8",
                                                       "input_data": {"tech_description": reg_text,
                                                                      "region": reg_region2}})
            if r:
                render_output_doc(r.get("output_doc", r))

    with tab_team:
        st.subheader("팀 역량 평가 (NSF I-Corps 5차원)")
        team_text = st.text_area("팀 구성 및 역량 설명", height=100, key="g8_team_desc")
        if st.button("👥 팀 역량 평가", type="primary", disabled=not team_text.strip()):
            with st.spinner("팀 역량 평가 중..."):
                r = api_post("/execution/team", {"tech_id": st.session_state.tech_id or "G8",
                                                 "input_data": {"team_description": team_text}})
            if r:
                render_output_doc(r.get("output_doc", r))


# ════════════════════════════════════════════════════════════════
# G9 — 거래·투자 (Deal 구조화 + 라이선싱 + 투자유치)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "g9":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    render_context_banner()
    st.title("🤝 G9 — 거래·투자")
    render_stage_bar(current=9)

    tab_deal, tab_license, tab_invest, tab_exit = st.tabs(
        ["🤝 Deal 구조화", "📄 라이선싱", "💼 투자유치", "🚪 엑시트 전략"]
    )

    with tab_deal:
        st.subheader("Deal 구조화 전략")
        deal_text = st.text_area("기술 및 사업 현황 설명", height=120,
                                 placeholder="예) TRL 7, PoC 완료, 유료 고객 3개사, ACV 50만원...")
        deal_type = st.selectbox("거래 유형", ["라이선싱", "기술이전", "JV(합작)", "M&A", "전략적 투자"])
        if st.button("🤝 Deal 구조화", type="primary", disabled=not deal_text.strip()):
            with st.spinner("Deal 전략 생성 중..."):
                r = api_post("/stage/9", {"tech_id": st.session_state.tech_id or "G9",
                                          "input_data": {"tech_description": deal_text, "deal_type": deal_type}})
            if r:
                _save_gate(9, r)
                render_gate_card(r.get("gate",""), float(r.get("score",0)), "G9 거래·투자", r.get("next_actions",[]))
                with st.expander("Deal 전략 상세"):
                    render_output_doc(r.get("output_doc", r))

    with tab_license:
        st.subheader("라이선싱·기술이전 전략")
        lic_text = st.text_area("특허/기술 설명", height=100, key="g9_lic_desc")
        lic_royalty = st.slider("희망 로열티율 (%)", 1, 25, 5, key="g9_lic_royalty")
        if st.button("📄 라이선싱 전략 생성", type="primary", disabled=not lic_text.strip()):
            with st.spinner("라이선싱 전략 생성 중..."):
                r = api_post("/gap/patent-maintenance", {"tech_id": st.session_state.tech_id or "G9",
                                                         "input_data": {"tech_description": lic_text,
                                                                        "royalty_rate": lic_royalty / 100}})
            if r:
                st.session_state["_g9_lic_result"] = r
                render_output_doc(r.get("output_doc", r))
        if st.session_state.get("_g9_lic_result"):
            if st.button("📄 보고서 센터에 저장 (R7)", key="g9_lic_to_rpt"):
                st.session_state["_rpt_prefill"] = {"report_id": "R7_license", "result": st.session_state["_g9_lic_result"]}
                st.session_state.page = "reports"; st.rerun()

    with tab_invest:
        st.subheader("투자유치 전략 (IR Deck 포함)")
        inv_text  = st.text_area("기업/기술 현황", height=100, key="g9_inv_desc")
        inv_stage = st.selectbox("투자 단계", ["Pre-Seed", "Seed", "Series A", "Series B", "Late-Stage"])
        inv_amt   = st.number_input("목표 투자 금액 (억 원)", min_value=0, value=5, step=1)
        if st.button("💼 투자 전략 + IR Deck 생성", type="primary", disabled=not inv_text.strip()):
            with st.spinner("IR Deck 생성 중..."):
                r = api_post("/gap/ir-deck", {"tech_id": st.session_state.tech_id or "G9",
                                              "input_data": {"tech_description": inv_text,
                                                             "investment_stage": inv_stage,
                                                             "target_amount_million_krw": inv_amt * 100}})
            if r:
                st.session_state["_g9_ir_result"] = r
                render_output_doc(r.get("output_doc", r))
        if st.session_state.get("_g9_ir_result"):
            if st.button("📄 보고서 센터에 저장 (R6)", key="g9_ir_to_rpt"):
                st.session_state["_rpt_prefill"] = {"report_id": "R6_ir", "result": st.session_state["_g9_ir_result"]}
                st.session_state.page = "reports"; st.rerun()

    with tab_exit:
        st.subheader("엑시트 전략 (M&A / IPO)")
        exit_text = st.text_area("기업/기술 현황", height=100, key="g9_exit_desc")
        if st.button("🚪 엑시트 전략 분석", type="primary", disabled=not exit_text.strip()):
            with st.spinner("엑시트 전략 분석 중..."):
                r = api_post("/gap/exit-strategy", {"tech_id": st.session_state.tech_id or "G9",
                                                    "input_data": {"tech_description": exit_text}})
            if r:
                st.session_state["_g9_exit_result"] = r
                render_output_doc(r.get("output_doc", r))
        if st.session_state.get("_g9_exit_result"):
            if st.button("📄 보고서 센터에 저장 (R9)", key="g9_exit_to_rpt"):
                st.session_state["_rpt_prefill"] = {"report_id": "R9_exit", "result": st.session_state["_g9_exit_result"]}
                st.session_state.page = "reports"; st.rerun()


# ════════════════════════════════════════════════════════════════
# 로드맵 (레거시 — G5 실행 로드맵 탭으로 이동 권장)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "roadmap":
    # roadmap 페이지는 G5 실행 로드맵 탭으로 통합 — MECE 구조 준수
    st.session_state.page = "g5"
    st.session_state["_g5_tab"] = "roadmap"
    st.rerun()


# ════════════════════════════════════════════════════════════════
# 관리자 콘솔 (통합)
# ════════════════════════════════════════════════════════════════
elif st.session_state.page == "admin":
    _h = api_get("/health", silent=True); _aok = _h is not None
    _th = st.session_state.get("theme","dark"); _bg = st.session_state.get("bg_on",True)
    st.markdown(f"<script>document.body.setAttribute('data-theme','{_th}');document.body.classList.{'add' if _bg else 'remove'}('bg-on');</script>", unsafe_allow_html=True)
    with st.sidebar:
        render_app_sidebar(_aok)
    st.title("⚙️ 관리자 콘솔")

    tab_health, tab_metrics, tab_jobs, tab_govern, tab_login = st.tabs(
        ["🩺 헬스 체크", "📊 API 메트릭", "📋 Job 모니터", "🛡 AI 거버넌스", "🔐 인증"]
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
                        render_output_doc(job["result"], collapsed=True)
                if job.get("error"):
                    st.error(job["error"])

    with tab_govern:
        st.subheader("AI 에이전트 실행 이력 (Governance Log)")
        st.caption("모든 API POST 호출을 기록합니다. 승인/거부로 에이전트 행동을 감사할 수 있습니다.")
        logs = list(reversed(st.session_state.get("_agent_log", [])))

        # 통계 카드
        total = len(logs)
        approved   = sum(1 for l in logs if l.get("approved") is True)
        rejected   = sum(1 for l in logs if l.get("approved") is False)
        unreviewed = total - approved - rejected
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("전체 호출",  total)
        s2.metric("승인",        approved,   delta="✅")
        s3.metric("거부",        rejected,   delta="⛔" if rejected else None)
        s4.metric("미검토",      unreviewed, delta="🔵" if unreviewed else None)

        if st.button("🗑 이력 초기화", key="adm_gov_clear"):
            st.session_state["_agent_log"] = []
            st.rerun()

        st.divider()

        if not logs:
            st.markdown('<div class="info-card">AI 에이전트 호출 이력이 없습니다. 분석을 실행하면 여기에 기록됩니다.</div>',
                        unsafe_allow_html=True)
        else:
            for i, entry in enumerate(logs[:30]):
                approved_val = entry.get("approved")
                status_col = "#4ade80" if approved_val is True else "#f87171" if approved_val is False else "#475569"
                status_icon = "✅" if approved_val is True else "⛔" if approved_val is False else "🔵"
                http_col = "#4ade80" if entry.get("status") == 200 else "#f87171"

                _ep = entry["endpoint"]; _pr = entry["params"]
                _dt_str = entry["date"]; _ts_str = entry["ts"]
                _res = entry.get("result",""); _st = entry.get("status","?")
                _res_html = f'<div style="font-size:9px;color:#64748b;margin-top:1px">{_res}</div>' if _res else ""
                row_html = (
                    f'<div style="display:flex;align-items:center;gap:8px;'
                    f'padding:8px;border-radius:7px;border:1px solid rgba(255,255,255,.05);'
                    f'background:#1a1d27;margin:4px 0">'
                    f'<span style="font-size:14px">{status_icon}</span>'
                    f'<div style="flex:1;min-width:0">'
                    f'<div style="font-size:10px;color:#60a5fa;font-family:monospace">{_ep}</div>'
                    f'<div style="font-size:9px;color:#475569;margin-top:2px">{_pr}</div>'
                    f'{_res_html}'
                    f'</div>'
                    f'<div style="text-align:right;flex-shrink:0">'
                    f'<div style="font-size:8px;color:#334155">{_dt_str} {_ts_str}</div>'
                    f'<span style="font-size:9px;color:{http_col}">{_st}</span>'
                    f'</div></div>'
                )
                st.markdown(row_html, unsafe_allow_html=True)

                # 승인/거부 버튼 (미검토 항목만)
                if approved_val is None:
                    idx = len(logs) - 1 - i  # 원본 인덱스
                    ba, bb = st.columns(2)
                    if ba.button("✅ 승인", key=f"gov_ok_{i}", use_container_width=True):
                        st.session_state["_agent_log"][idx]["approved"] = True
                        st.rerun()
                    if bb.button("⛔ 거부", key=f"gov_no_{i}", use_container_width=True):
                        st.session_state["_agent_log"][idx]["approved"] = False
                        st.rerun()

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
