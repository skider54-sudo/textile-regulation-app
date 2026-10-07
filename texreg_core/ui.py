"""모든 페이지에서 사용하는 블루·화이트 기업형 UI 구성 요소."""

from __future__ import annotations

from html import escape

import streamlit as st


RISK_COLORS = {
    "높음": ("#B42318", "#FEF3F2"),
    "보통": ("#B54708", "#FFFAEB"),
    "낮음": ("#067647", "#ECFDF3"),
}

REGULATION_STATUS_COLORS = {
    "시행 중": ("#067647", "#ECFDF3"),
    "시행 예정": ("#B54708", "#FFFAEB"),
    "제안·검토": ("#3538CD", "#EEF4FF"),
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
        .input-guide {
            background: linear-gradient(90deg, rgba(20, 40, 160, .07), rgba(20, 40, 160, .02));
            border: 1px solid rgba(20, 40, 160, .14);
            border-radius: 14px;
            display: grid;
            gap: 3px;
            margin: 4px 0 18px;
            padding: 16px 18px;
        }
        .input-guide__eyebrow { color: var(--blue); font-size: .72rem; font-weight: 800; letter-spacing: .13em; }
        .input-guide strong { color: var(--ink); font-size: .98rem; }
        .input-guide > span:last-child { color: var(--muted); font-size: .84rem; }
        .input-section-heading {
            align-items: center;
            border-bottom: 1px solid var(--line);
            display: flex;
            gap: 13px;
            margin: 0 0 18px;
            padding: 2px 0 14px;
        }
        .input-section-number {
            align-items: center;
            background: var(--blue);
            border-radius: 10px;
            color: #fff;
            display: inline-flex;
            font-size: .72rem;
            font-weight: 800;
            height: 34px;
            justify-content: center;
            letter-spacing: .05em;
            min-width: 38px;
        }
        .input-section-heading div { display: grid; gap: 2px; }
        .input-section-heading strong { color: var(--ink); font-size: 1.04rem; }
        .input-section-heading div span { color: var(--muted); font-size: .82rem; }
        .input-subheading {
            border-top: 1px solid var(--line);
            color: var(--ink);
            font-size: .9rem;
            font-weight: 750;
            margin: 18px 0 12px;
            padding-top: 16px;
        }
        .composition-total {
            border-radius: 9px;
            font-size: .82rem;
            font-weight: 700;
            margin: 7px 0 2px;
            padding: 9px 12px;
        }
        .composition-total.valid { background: #EBF7F0; border: 1px solid #BCE2CA; color: #137044; }
        .composition-total.invalid { background: #FFF4ED; border: 1px solid #F4CFB8; color: #B64E12; }
        .composition-total.unknown { background: #F2F5FA; border: 1px solid #D9E0EB; color: #5C6678; }
        .submit-note { color: var(--muted); font-size: .78rem; line-height: 1.6; margin: 4px 2px 12px; text-align: center; }
        .layer-visual {
            background: linear-gradient(145deg, #F8FAFF 0%, #FFFFFF 56%, #F2F5FB 100%);
            border: 1px solid #DDE3F0;
            border-radius: 20px;
            display: grid;
            gap: 22px;
            grid-template-columns: minmax(180px, .72fr) minmax(360px, 1.5fr);
            margin-top: 16px;
            overflow: hidden;
            padding: 22px;
        }
        .layer-visual__copy { align-self: center; }
        .layer-visual__copy span { color: var(--blue); font-size: .7rem; font-weight: 900; letter-spacing: .13em; }
        .layer-visual__copy strong { color: var(--ink); display: block; font-size: 1.12rem; margin: 6px 0; }
        .layer-visual__copy p { color: var(--muted); font-size: .8rem; line-height: 1.55; margin: 0; }
        .layer-stack { display: grid; gap: 7px; }
        .layer-stack__item {
            align-items: center;
            display: grid;
            gap: 10px;
            grid-template-columns: 28px minmax(100px, .8fr) minmax(140px, 1.2fr);
        }
        .layer-stack__number {
            align-items: center; background: #18275B; border-radius: 50%; color: #FFFFFF;
            display: inline-flex; font-size: .68rem; font-weight: 900; height: 26px; justify-content: center; width: 26px;
        }
        .layer-stack__slab {
            border: 1px solid rgba(38, 59, 126, .22); border-radius: 7px; box-shadow: 0 7px 12px rgba(28, 42, 92, .12);
            height: 30px; transform: skewX(-10deg);
        }
        .layer-stack__item:nth-child(1) .layer-stack__slab { background: linear-gradient(135deg, #284794, #7F9FE0); }
        .layer-stack__item:nth-child(2) .layer-stack__slab { background: linear-gradient(135deg, #9E8A6C, #D8C9B3); }
        .layer-stack__item:nth-child(3) .layer-stack__slab { background: linear-gradient(135deg, #7485A9, #C0CBE0); }
        .layer-stack__item:nth-child(4) .layer-stack__slab { background: linear-gradient(135deg, #4774AA, #A7C6E7); }
        .layer-stack__item:nth-child(5) .layer-stack__slab { background: linear-gradient(135deg, #2E394A, #6E7D90); }
        .layer-stack__item.inactive { opacity: .38; }
        .layer-stack__meta { min-width: 0; }
        .layer-stack__meta strong { color: #26314B; display: block; font-size: .78rem; }
        .layer-stack__meta span { color: var(--muted); display: block; font-size: .74rem; overflow-wrap: anywhere; }
        .trace-guide {
            background: #F5F7FC; border-left: 3px solid var(--blue); border-radius: 0 12px 12px 0;
            color: #4D5873; font-size: .8rem; line-height: 1.6; margin: 16px 0 12px; padding: 11px 14px;
        }
        .trace-card {
            background: #FFFFFF; border: 1px solid var(--line); border-radius: 15px; margin-bottom: 9px; padding: 13px 14px;
        }
        .trace-card__header { align-items: center; display: flex; justify-content: space-between; margin-bottom: 9px; }
        .trace-card__header strong { color: var(--ink); }
        .trace-card__grid { display: grid; gap: 10px; grid-template-columns: repeat(4, minmax(0, 1fr)); }
        .trace-card__grid span { color: var(--muted); display: block; font-size: .68rem; font-weight: 800; margin-bottom: 3px; }
        .trace-card__grid div { color: #26314B; font-size: .8rem; overflow-wrap: anywhere; }
        .status-badge { border-radius: 999px; display: inline-block; font-size: .75rem; font-weight: 800; padding: .28rem .65rem; }
        .regulation-timeline {
            display: grid; gap: 9px; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 12px 0 18px;
        }
        .timeline-cell { background: #FFFFFF; border: 1px solid var(--line); border-radius: 13px; min-height: 82px; padding: 11px 12px; }
        .timeline-cell span { color: var(--muted); display: block; font-size: .68rem; font-weight: 800; margin-bottom: 5px; }
        .timeline-cell strong { color: #26314B; display: block; font-size: .78rem; line-height: 1.45; overflow-wrap: anywhere; }
        .snapshot-banner {
            align-items: center; background: linear-gradient(120deg, #101D5C, #1428A0 62%, #315CE7);
            border-radius: 18px; color: #FFFFFF; display: flex; justify-content: space-between;
            margin: 8px 0 16px; padding: 18px 20px;
        }
        .snapshot-banner span { display: block; font-size: .67rem; font-weight: 900; letter-spacing: .12em; opacity: .72; }
        .snapshot-banner strong { display: block; font-size: 1.12rem; margin-top: 4px; }
        .snapshot-banner__meta { font-size: .74rem; line-height: 1.6; opacity: .82; text-align: right; }
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
            display: grid; grid-template-columns: minmax(240px, 1fr) 110px 110px 110px;
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
            .layer-visual { grid-template-columns: 1fr; padding: 17px; }
            .layer-stack__item { grid-template-columns: 26px 90px minmax(0, 1fr); }
            .trace-card__grid, .regulation-timeline { grid-template-columns: 1fr 1fr; }
            .snapshot-banner { align-items: flex-start; flex-direction: column; gap: 10px; }
            .snapshot-banner__meta { text-align: left; }
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
        st.page_link("pages/3_Risk_Dashboard.py", label="제품 데이터베이스")
        st.markdown("---")
        st.caption("Prototype 2.5 · 12 markets")


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


def regulation_status_badge(status: str) -> str:
    """규제의 현재 단계를 시행 중·시행 예정·제안 검토 배지로 표시한다."""
    foreground, background = REGULATION_STATUS_COLORS.get(status, ("#475467", "#F2F4F7"))
    return (
        f'<span class="status-badge" style="color:{foreground};background:{background};">'
        f"{escape(status or '상태 확인 필요')}</span>"
    )


def render_layer_stack(
    base_fabric: object,
    membrane: object,
    coating: object,
    lamination: object,
    finishing: object,
    *,
    title: str = "Layered Structure",
) -> None:
    """제품의 기능성 구조를 다섯 개 층으로 시각화한다."""
    layers = [
        (5, "Finishing", finishing),
        (4, "Lamination", lamination),
        (3, "Coating", coating),
        (2, "Membrane", membrane),
        (1, "Base fabric", base_fabric),
    ]
    inactive_values = {"", "없음", "미입력", "선택 안 함"}
    layer_html = "".join(
        f"""
        <div class="layer-stack__item {'inactive' if str(value or '').strip() in inactive_values else ''}">
            <span class="layer-stack__number">{number}</span>
            <div class="layer-stack__slab"></div>
            <div class="layer-stack__meta">
                <strong>{escape(label)}</strong>
                <span>{escape(str(value or '없음'))}</span>
            </div>
        </div>
        """
        for number, label, value in layers
    )
    st.markdown(
        f"""
        <div class="layer-visual">
            <div class="layer-visual__copy">
                <span>STRUCTURE MAP</span>
                <strong>{escape(title)}</strong>
                <p>제품을 구성하는 원단과 기능성 층을 위에서 아래 순서로 보여줍니다.</p>
            </div>
            <div class="layer-stack">{layer_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
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
