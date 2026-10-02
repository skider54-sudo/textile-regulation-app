"""모든 페이지에서 사용하는 블루·화이트 기업형 UI 구성 요소."""

from __future__ import annotations

from html import escape

import streamlit as st


RISK_COLORS = {
    "높음": ("#B42318", "#FEF3F2"),
    "보통": ("#B54708", "#FFFAEB"),
    "낮음": ("#067647", "#ECFDF3"),
}


def setup_page(title: str) -> None:
    """페이지 기본 설정과 공통 스타일을 적용한다."""
    st.set_page_config(
        page_title=f"{title} | TexReg Insight",
        page_icon="TR",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --blue: #1428A0;
            --blue-deep: #081B72;
            --blue-soft: #EEF2FF;
            --ink: #101114;
            --muted: #64676D;
            --line: #E6E8EC;
            --surface: #FFFFFF;
            --canvas: #F7F8FA;
        }
        html, body, [class*="css"] { font-family: Arial, "Noto Sans KR", sans-serif; }
        .stApp {
            background: linear-gradient(180deg, #FFFFFF 0%, var(--canvas) 36%, #FFFFFF 100%);
            color: var(--ink);
        }
        .block-container { max-width: 1280px; padding-top: 2.4rem; padding-bottom: 4.5rem; }
        [data-testid="stHeader"] { background: rgba(255,255,255,.88); backdrop-filter: blur(12px); }
        [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid var(--line); }
        [data-testid="stSidebar"] * { color: #18191C; }
        [data-testid="stSidebarNav"] { display: none; }
        [data-testid="stSidebar"] a { text-decoration: none; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
        [data-testid="stPageLink-NavLink"] {
            border-radius: 999px;
            padding: .72rem .95rem;
            margin: .18rem 0;
            font-weight: 700;
        }
        [data-testid="stPageLink-NavLink"]:hover { background: var(--blue-soft); color: var(--blue); }
        h1, h2, h3 { color: var(--ink); letter-spacing: -0.045em; }
        h1 { font-size: 2.55rem !important; font-weight: 800 !important; }
        h2 { font-size: 1.7rem !important; }
        h3 { margin-top: 2.1rem !important; }
        p, label, .stMarkdown { line-height: 1.66; }
        div.stButton > button, div.stFormSubmitButton > button {
            border-radius: 999px;
            border: 1px solid var(--blue);
            background: var(--blue);
            color: white;
            font-weight: 800;
            min-height: 48px;
            box-shadow: 0 8px 22px rgba(20, 40, 160, 0.16);
            transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            border-color: var(--blue-deep);
            background: var(--blue-deep);
            color: white;
            transform: translateY(-1px);
            box-shadow: 0 11px 26px rgba(20, 40, 160, 0.22);
        }
        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #ECEEF2;
            border-radius: 22px;
            padding: 1.2rem 1.25rem;
            box-shadow: 0 10px 30px rgba(17, 28, 66, 0.055);
        }
        div[data-testid="stMetric"] label { color: var(--muted); }
        div[data-testid="stMetricValue"] { color: var(--ink); font-weight: 800; }
        div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea {
            border-radius: 14px !important;
            border-color: #D9DCE3 !important;
        }
        [data-testid="stForm"] {
            background: #FFFFFF;
            border: 1px solid #EAECF0;
            border-radius: 24px;
            padding: 1.35rem 1.5rem 1.55rem;
            box-shadow: 0 14px 42px rgba(17, 28, 66, 0.055);
        }
        .hero {
            position: relative;
            overflow: hidden;
            min-height: 420px;
            display: flex;
            align-items: center;
            background:
                radial-gradient(circle at 82% 18%, rgba(74,112,255,.22), transparent 28%),
                linear-gradient(135deg, #F7F9FF 0%, #EEF2FF 55%, #E6ECFF 100%);
            border: 1px solid #E2E7FA;
            border-radius: 34px;
            padding: 4.3rem 4.6rem;
            margin-bottom: 1.35rem;
            box-shadow: 0 22px 60px rgba(17, 28, 66, 0.09);
        }
        .hero-copy { position: relative; z-index: 2; width: min(70%, 760px); }
        .hero-kicker { color: var(--blue); font-size: .76rem; font-weight: 900; letter-spacing: .16em; }
        .hero h1 { color: var(--ink); font-size: 3.65rem !important; line-height: 1.08; margin: .65rem 0 1.05rem; max-width: 760px; }
        .hero p { color: #4D5159; font-size: 1.06rem; max-width: 650px; margin: 0; }
        .hero-tags { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: 1.45rem; }
        .hero-tags span {
            background: rgba(255,255,255,.78); border: 1px solid #D7DDF4; border-radius: 999px;
            color: #38405A; font-size: .78rem; font-weight: 800; padding: .42rem .72rem;
        }
        .hero-orbit {
            position: absolute; right: 6.5%; top: 50%; transform: translateY(-50%);
            width: 245px; height: 245px; border-radius: 50%;
            background: linear-gradient(145deg, #2F5BFF 0%, #1428A0 58%, #081B72 100%);
            box-shadow: 0 28px 65px rgba(20, 40, 160, .32), inset 0 1px 1px rgba(255,255,255,.35);
            display: flex; align-items: center; justify-content: center; color: white;
        }
        .orbit-score { font-size: 4.1rem; line-height: .9; font-weight: 900; letter-spacing: -.07em; }
        .orbit-label { font-size: .72rem; margin-top: .7rem; letter-spacing: .12em; font-weight: 800; opacity: .78; }
        .page-kicker { color: var(--blue); font-weight: 900; letter-spacing: .14em; font-size: .73rem; }
        .page-lead { color: var(--muted); margin-top: -.5rem; margin-bottom: 1.55rem; }
        .panel {
            background: white;
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 1.35rem 1.45rem;
            box-shadow: 0 12px 34px rgba(17, 28, 66, .055);
        }
        .flow-card {
            min-height: 168px;
            background: white;
            border: 1px solid #EAECF0;
            border-radius: 22px;
            padding: 1.35rem;
            box-shadow: 0 12px 32px rgba(17, 28, 66, .05);
            transition: transform .18s ease, box-shadow .18s ease;
        }
        .flow-card:hover { transform: translateY(-3px); box-shadow: 0 17px 38px rgba(17, 28, 66, .09); }
        .flow-number { color: var(--blue); font-size: 1.4rem; font-weight: 900; letter-spacing: -.04em; }
        .flow-card h3 { font-size: 1.05rem !important; margin: 1.2rem 0 .4rem !important; letter-spacing: -.025em; }
        .flow-card p { color: var(--muted); font-size: .88rem; margin: 0; }
        .stat-card {
            background: white; border: 1px solid #EAECF0; border-radius: 22px; padding: 1.25rem 1.35rem;
            box-shadow: 0 12px 32px rgba(17, 28, 66, .05);
        }
        .stat-label { color: var(--muted); font-size: .82rem; }
        .stat-value { color: var(--ink); font-size: 1.85rem; font-weight: 900; margin-top: .25rem; letter-spacing: -.04em; }
        .risk-badge { display: inline-block; border-radius: 999px; padding: .28rem .72rem; font-size: .8rem; font-weight: 800; }
        .reg-row {
            display: grid; grid-template-columns: minmax(240px, 1fr) 120px 120px;
            gap: 1rem; align-items: center; background: white; border: 1px solid var(--line);
            border-radius: 18px; padding: 1rem 1.1rem; margin-bottom: .65rem;
            box-shadow: 0 7px 22px rgba(17, 28, 66, .035);
        }
        .reg-name { color: var(--ink); font-weight: 800; }
        .reg-label { color: var(--muted); font-size: .72rem; display: block; margin-bottom: .2rem; }
        .detail-label { color: var(--blue); font-size: .76rem; font-weight: 900; letter-spacing: .04em; }
        .detail-value { color: var(--ink); margin-top: .3rem; }
        .callout { border-left: 4px solid var(--blue); background: var(--blue-soft); padding: 1rem 1.15rem; border-radius: 0 14px 14px 0; }
        .product-trigger {
            display: flex; flex-direction: column; gap: .28rem; margin: .9rem 0 1.2rem;
            border: 1px solid #DDE3FA; border-radius: 16px; padding: .9rem 1rem; background: #F8F9FF;
        }
        .product-trigger span { color: var(--blue); font-size: .74rem; font-weight: 900; letter-spacing: .04em; }
        .product-trigger strong { color: #27314C; font-size: .9rem; }
        .response-summary {
            border-left: 4px solid var(--blue); background: #F3F6FF; border-radius: 0 16px 16px 0;
            padding: 1rem 1.15rem; color: #293552; line-height: 1.7; margin-bottom: 1.1rem;
        }
        .action-list { display: grid; gap: .65rem; margin-bottom: 1.2rem; }
        .action-step {
            display: grid; grid-template-columns: 42px 1fr; gap: .85rem; align-items: center;
            border: 1px solid var(--line); border-radius: 16px; padding: .85rem 1rem; background: #FFFFFF;
            box-shadow: 0 6px 18px rgba(17, 28, 66, .035); color: #303641;
        }
        .action-index {
            width: 34px; height: 34px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
            background: var(--blue); color: #FFFFFF; font-size: .72rem; font-weight: 900;
        }
        .action-meta {
            min-height: 112px; border: 1px solid var(--line); border-radius: 17px; padding: 1rem 1.05rem;
            background: #FFFFFF; box-shadow: 0 7px 22px rgba(17, 28, 66, .035);
        }
        .action-meta span, .completion-box span { display: block; color: var(--muted); font-size: .73rem; font-weight: 800; margin-bottom: .45rem; }
        .action-meta strong { display: block; color: var(--ink); line-height: 1.55; }
        .completion-box {
            margin-top: .8rem; border: 1px solid #B7E4D1; background: #F0FBF7; border-radius: 17px;
            padding: 1rem 1.1rem; color: #065F46;
        }
        .completion-box strong { line-height: 1.6; }
        .score-number { color: var(--blue); font-size: 3rem; line-height: 1; font-weight: 900; }
        .score-total { color: var(--muted); font-size: 1rem; }
        .sidebar-brand { padding: .45rem 0 1.3rem; border-bottom: 1px solid var(--line); margin-bottom: 1rem; display: flex; align-items: center; gap: .75rem; }
        .brand-mark {
            width: 40px; height: 40px; display: inline-flex; align-items: center; justify-content: center;
            border-radius: 50%; background: var(--blue); color: white !important; font-size: .75rem; font-weight: 900; letter-spacing: -.03em;
        }
        .sidebar-brand strong { color: var(--ink); font-size: 1.12rem; letter-spacing: -.025em; }
        .sidebar-brand small { color: #777B84; display: block; margin-top: .1rem; font-size: .67rem; letter-spacing: .06em; }
        .footer-note { color: #7B8794; font-size: .78rem; border-top: 1px solid var(--line); padding-top: 1rem; margin-top: 2rem; }
        [data-testid="stAlert"] { border-radius: 16px; }
        @media (max-width: 900px) {
            .hero { min-height: auto; padding: 2.8rem 2rem; }
            .hero-copy { width: 100%; }
            .hero h1 { font-size: 2.65rem !important; }
            .hero-orbit { display: none; }
        }
        @media (max-width: 700px) {
            .block-container { padding-top: 1.35rem; }
            .hero { border-radius: 24px; padding: 2.3rem 1.45rem; }
            .hero h1 { font-size: 2.2rem !important; }
            .reg-row { grid-template-columns: 1fr; gap: .55rem; }
            .action-step { grid-template-columns: 36px 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_sidebar()


def render_sidebar() -> None:
    """기본 Streamlit 메뉴 대신 서비스 전용 탐색 메뉴를 표시한다."""
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <span class="brand-mark">TR</span>
                <span>
                    <strong>TexReg Insight</strong>
                    <small>GLOBAL COMPLIANCE</small>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("app.py", label="Home")
        st.page_link("pages/1_Product_Input.py", label="제품 규제 진단")
        st.page_link("pages/2_Diagnosis_Result.py", label="진단 결과")
        st.page_link("pages/3_Risk_Dashboard.py", label="Risk Dashboard")
        st.markdown("---")
        st.caption("Prototype 2.1 · Five markets")


def page_heading(kicker: str, title: str, description: str) -> None:
    """페이지 제목을 동일한 시각 체계로 표시한다."""
    st.markdown(f'<div class="page-kicker">{escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="page-lead">{escape(description)}</div>', unsafe_allow_html=True)


def risk_badge(level: str) -> str:
    """위험도 텍스트를 접근성 있는 색상 배지 HTML로 반환한다."""
    foreground, background = RISK_COLORS.get(level, ("#475467", "#F2F4F7"))
    return (
        f'<span class="risk-badge" style="color:{foreground};background:{background};">'
        f"{escape(level)}</span>"
    )


def stat_card(label: str, value: str, note: str | None = None) -> None:
    """홈과 결과 화면의 간단한 요약 카드."""
    note_html = f'<div class="stat-label">{escape(note)}</div>' if note else ""
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{escape(label)}</div>
            <div class="stat-value">{escape(value)}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """프로토타입 데이터의 법률 자문 비해당 안내."""
    st.markdown(
        """
        <div class="footer-note">
        본 화면의 규제 정보와 점수는 시연용 예시 데이터에 기반한 1차 스크리닝 결과입니다.
        실제 수출 전에는 최신 법령, 적용 예외 및 공인 시험 결과를 별도로 확인해야 합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
