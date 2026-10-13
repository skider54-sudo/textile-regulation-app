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


def setup_page(title: str, *, sidebar_state: str = "expanded") -> None:
    """페이지 기본 설정과 공통 스타일을 적용한다."""
    st.set_page_config(
        page_title=f"{title} | TexReg Insight",
        page_icon="TR",
        layout="wide",
        initial_sidebar_state=sidebar_state,
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
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
            border-radius: 999px;
            padding: .72rem .95rem;
            margin: .18rem 0;
            font-weight: 700;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover { background: var(--blue-soft); color: var(--blue); }
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
        .portal-header {
            align-items: center; background: rgba(255,255,255,.96); border: 1px solid var(--line);
            border-radius: 18px; box-shadow: 0 8px 28px rgba(17,28,66,.045); display: flex;
            gap: 24px; justify-content: space-between; margin-bottom: 18px; padding: 13px 18px;
        }
        .portal-brand { align-items: center; color: var(--ink) !important; display: flex; gap: 11px; text-decoration: none !important; }
        .portal-brand__mark {
            align-items: center; background: linear-gradient(145deg, #264FE5, #1428A0); border-radius: 11px;
            color: #FFFFFF; display: inline-flex; font-size: .72rem; font-weight: 900; height: 38px;
            justify-content: center; letter-spacing: -.02em; width: 38px;
        }
        .portal-brand strong { display: block; font-size: 1rem; letter-spacing: -.025em; }
        .portal-brand small { color: #7B8495; display: block; font-size: .64rem; letter-spacing: .08em; margin-top: 1px; }
        .portal-nav { align-items: center; display: flex; flex-wrap: wrap; gap: 5px; justify-content: flex-end; }
        .portal-nav span {
            border-radius: 10px; color: #4E586B !important; font-size: .8rem; font-weight: 750;
            padding: 8px 11px; text-decoration: none !important; transition: background .16s ease, color .16s ease;
        }
        .portal-hero {
            background: linear-gradient(128deg, #F8FAFF 0%, #EDF2FF 58%, #E2E9FF 100%);
            border: 1px solid #DCE4FA; border-radius: 27px; box-shadow: 0 18px 50px rgba(17,28,66,.075);
            display: grid; gap: 34px; grid-template-columns: minmax(0,1.5fr) minmax(260px,.7fr);
            margin-bottom: 18px; overflow: hidden; padding: 42px 46px; position: relative;
        }
        .portal-hero::after {
            background: radial-gradient(circle, rgba(42,82,220,.19), transparent 66%); content: "";
            height: 330px; position: absolute; right: -80px; top: -145px; width: 330px;
        }
        .portal-hero__copy { position: relative; z-index: 1; }
        .portal-hero__eyebrow { color: var(--blue); font-size: .72rem; font-weight: 900; letter-spacing: .15em; }
        .portal-hero h1 { font-size: 3.1rem !important; line-height: 1.1; margin: 9px 0 13px; max-width: 720px; }
        .portal-hero p { color: #525D71; font-size: 1rem; margin: 0; max-width: 680px; }
        .portal-hero__facts { align-content: center; display: grid; gap: 9px; position: relative; z-index: 1; }
        .portal-fact {
            background: rgba(255,255,255,.82); border: 1px solid rgba(202,213,243,.9); border-radius: 14px;
            display: flex; justify-content: space-between; padding: 11px 13px;
        }
        .portal-fact span { color: #697386; font-size: .75rem; }
        .portal-fact strong { color: #15265D; font-size: .82rem; }
        .portal-section-heading { align-items: flex-end; display: flex; justify-content: space-between; margin: 29px 2px 12px; }
        .portal-section-heading strong { color: var(--ink); font-size: 1.22rem; }
        .portal-section-heading span { color: var(--muted); font-size: .78rem; }
        .st-key-home_portal_steps div.stButton > button {
            align-items: flex-start; background: #FFFFFF; border: 1px solid var(--line); border-radius: 18px;
            box-shadow: 0 10px 28px rgba(17,28,66,.045); color: var(--ink); justify-content: flex-start;
            font-weight: 600; min-height: 142px; padding: 20px; text-align: left; width: 100%;
        }
        .st-key-home_portal_steps div.stButton > button:hover {
            background: #F8FAFF; border-color: #B9C7F6; color: var(--blue);
            box-shadow: 0 15px 34px rgba(17,28,66,.085); transform: translateY(-2px);
        }
        .st-key-home_portal_steps div.stButton > button:focus-visible {
            outline: 3px solid rgba(20,40,160,.28); outline-offset: 3px;
        }
        .st-key-home_portal_steps div.stButton > button p {
            color: var(--muted); font-size: .86rem; line-height: 1.65; text-align: left; white-space: pre-line;
        }
        .st-key-home_portal_steps div.stButton > button strong { color: var(--ink); font-size: 1rem; }
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
        .workflow-steps {
            background: #FFFFFF; border: 1px solid #DEE3ED; border-radius: 18px; display: grid; gap: 0;
            grid-template-columns: repeat(3,minmax(0,1fr)); margin: 5px 0 22px; overflow: hidden;
            box-shadow: 0 8px 24px rgba(17,28,66,.035);
        }
        .workflow-step {
            align-items: center; color: inherit !important; display: grid; gap: 12px;
            grid-template-columns: 42px minmax(0,1fr) 16px; min-height: 88px; padding: 14px 18px;
            position: relative; text-decoration: none !important;
        }
        .workflow-step:not(:last-child) { border-right: 1px solid var(--line); }
        .workflow-step__number {
            align-items: center; background: #F0F2F6; border-radius: 50%; color: #8992A3; display: inline-flex;
            font-size: .72rem; font-weight: 900; height: 38px; justify-content: center; width: 38px;
        }
        .workflow-step strong { color: #4E586B; display: block; font-size: .92rem; }
        .workflow-step small { color: #8A93A3; display: block; font-size: .7rem; line-height: 1.4; margin-top: 2px; }
        .workflow-step__arrow { color: #C7CED9; font-size: 1.2rem; }
        .workflow-step--active { background: #F7F9FF; }
        .workflow-step--active .workflow-step__number { background: var(--blue); color: #FFFFFF; }
        .workflow-step--active strong { color: var(--ink); }
        .workflow-step--complete .workflow-step__number { background: #EAF7F2; color: #087453; }
        .workflow-step--complete strong { color: #426257; }
        .risk-alert {
            align-items: center; border: 1px solid; border-left-width: 5px; border-radius: 17px; display: grid;
            gap: 14px; grid-template-columns: 46px minmax(0,1fr) auto; margin: 7px 0 20px; padding: 17px 18px;
        }
        .risk-alert--medium { background: #FFFCF5; border-color: #E8CC8D; color: #684B18; }
        .risk-alert--high { background: #FFF7F6; border-color: #E7AAA5; color: #7A271A; }
        .risk-alert__icon {
            align-items: center; background: rgba(255,255,255,.76); border: 1px solid currentColor; border-radius: 13px;
            display: inline-flex; font-size: 1.15rem; font-weight: 900; height: 42px; justify-content: center; width: 42px;
        }
        .risk-alert strong { display: block; font-size: 1.05rem; margin-bottom: 3px; }
        .risk-alert p { color: inherit; font-size: .8rem; line-height: 1.55; margin: 0; opacity: .86; }
        .risk-alert__meta { text-align: right; white-space: nowrap; }
        .risk-alert__meta span { display: block; font-size: .67rem; font-weight: 800; opacity: .72; }
        .risk-alert__meta b { display: block; font-size: 1.15rem; margin-top: 2px; }
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
            .portal-hero { grid-template-columns: 1fr; padding: 34px 32px; }
            .portal-hero__facts { grid-template-columns: repeat(3,minmax(0,1fr)); }
            .workflow-steps { grid-template-columns: 1fr; }
            .workflow-step { grid-template-columns: 38px minmax(0,1fr); }
            .workflow-step:not(:last-child) { border-bottom: 1px solid var(--line); border-right: 0; }
            .workflow-step__arrow { display: none; }
        }
        @media (max-width: 700px) {
            .block-container { padding-top: 1.35rem; }
            .reg-row { grid-template-columns: 1fr; gap: .55rem; }
            .action-step { grid-template-columns: 36px 1fr; }
            .layer-visual { grid-template-columns: 1fr; padding: 17px; }
            .layer-stack__item { grid-template-columns: 26px 90px minmax(0, 1fr); }
            .trace-card__grid, .regulation-timeline { grid-template-columns: 1fr 1fr; }
            .snapshot-banner { align-items: flex-start; flex-direction: column; gap: 10px; }
            .snapshot-banner__meta { text-align: left; }
            .portal-header { align-items: flex-start; flex-direction: column; gap: 9px; }
            .portal-nav { justify-content: flex-start; }
            .portal-nav span { padding: 6px 8px; }
            .portal-hero { border-radius: 22px; padding: 28px 22px; }
            .portal-hero h1 { font-size: 2.2rem !important; }
            .portal-hero__facts { grid-template-columns: 1fr; }
            .portal-section-heading { align-items: flex-start; flex-direction: column; gap: 3px; }
            .workflow-steps { grid-template-columns: 1fr; }
            .workflow-step { min-height: 74px; }
            .workflow-step:not(:last-child) { border-bottom: 1px solid var(--line); border-right: 0; }
            .risk-alert { align-items: flex-start; grid-template-columns: 42px minmax(0,1fr); }
            .risk-alert__meta { grid-column: 2; text-align: left; }
        }
        @media (prefers-reduced-motion: reduce) {
            div.stButton > button, div.stFormSubmitButton > button {
                transition: none;
            }
            div.stButton > button:hover, div.stFormSubmitButton > button:hover {
                transform: none;
            }
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


def render_portal_header() -> None:
    """홈 화면 상단에 서비스 정체성과 주요 영역을 안내한다."""
    st.markdown(
        """
        <header class="portal-header">
            <div class="portal-brand">
                <span class="portal-brand__mark">TR</span>
                <span>
                    <strong>TexReg Insight</strong>
                    <small>TEXTILE REGULATION PORTAL</small>
                </span>
            </div>
            <nav class="portal-nav" aria-label="서비스 주요 영역">
                <span>제품 정보</span>
                <span>규제 진단</span>
                <span>대응 가이드</span>
                <span>제품 데이터베이스</span>
            </nav>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_process_steps(active_step: int) -> None:
    """제품 입력부터 대응 가이드까지의 현재 진행 단계를 표시한다."""
    steps = [
        (1, "제품 정보", "기본 정보와 제품 구성"),
        (2, "규제 진단", "검토 항목과 위험도 확인"),
        (3, "대응 가이드", "필요한 자료와 다음 조치"),
    ]
    step_html = []
    for index, title, description in steps:
        state_class = ""
        number = f"{index:02d}"
        current = ""
        if index == active_step:
            state_class = " workflow-step--active"
            current = ' aria-current="step"'
        elif index < active_step:
            state_class = " workflow-step--complete"
            number = "✓"
        arrow = '<span class="workflow-step__arrow" aria-hidden="true">›</span>' if index < 3 else ""
        step_html.append(
            f'<div class="workflow-step{state_class}"{current}>'
            f'<span class="workflow-step__number">{number}</span>'
            f'<span><strong>{escape(title)}</strong><small>{escape(description)}</small></span>'
            f"{arrow}</div>"
        )
    st.markdown(
        f'<div class="workflow-steps" aria-label="진단 진행 과정">{"".join(step_html)}</div>',
        unsafe_allow_html=True,
    )


def render_risk_alert(
    product_name: object,
    level: str,
    score: int,
    regulation_count: int,
    top_regulation: object | None = None,
) -> None:
    """종합 위험도가 보통 이상일 때 결과 상단에 우선 확인 메시지를 표시한다."""
    if level not in {"보통", "높음"}:
        return

    is_high = level == "높음"
    modifier = "risk-alert--high" if is_high else "risk-alert--medium"
    heading = "즉시 대응 검토가 필요합니다" if is_high else "우선 확인이 필요합니다"
    action = (
        "출시·출하 전 핵심 규제의 적용 여부와 시험·공급망 증빙을 먼저 확인하세요."
        if is_high
        else "매칭된 규제의 성분·공정 정보와 공급망 증빙을 우선 점검하세요."
    )
    regulation_text = (
        f" 특히 {escape(str(top_regulation))}부터 확인하는 것이 좋습니다."
        if top_regulation
        else ""
    )
    st.markdown(
        f"""
        <div class="risk-alert {modifier}" role="alert">
            <span class="risk-alert__icon" aria-hidden="true">!</span>
            <div>
                <strong>{heading}</strong>
                <p>{escape(str(product_name))}의 종합 위험도는 {escape(level)}이며 관련 규제 {int(regulation_count)}건이 확인되었습니다. {action}{regulation_text}</p>
            </div>
            <div class="risk-alert__meta"><span>RISK SCORE</span><b>{int(score)} / 100</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
