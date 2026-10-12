"""포털·진단 흐름 전용 UI.

Streamlit Cloud가 배포 직후 기존 모듈을 잠시 캐시한 상태에서도 새 화면을
안전하게 불러올 수 있도록, 기존 공용 ``ui`` 모듈과 분리해 둔다.
"""

from __future__ import annotations

from html import escape

import streamlit as st


def inject_portal_styles() -> None:
    """포털 홈, 진행 단계, 위험 알림에 필요한 추가 스타일을 삽입한다."""
    st.markdown(
        """
        <style>
        .portal-header {
            align-items: center; background: rgba(255,255,255,.96);
            border: 1px solid var(--line, #E6E8EC); border-radius: 18px;
            box-shadow: 0 8px 28px rgba(17,28,66,.045); display: flex;
            gap: 24px; justify-content: space-between; margin-bottom: 18px;
            padding: 13px 18px;
        }
        .portal-brand {
            align-items: center; color: var(--ink, #101114) !important;
            display: flex; gap: 11px; text-decoration: none !important;
        }
        .portal-brand__mark {
            align-items: center; background: linear-gradient(145deg, #264FE5, #1428A0);
            border-radius: 11px; color: #FFFFFF; display: inline-flex;
            font-size: .72rem; font-weight: 900; height: 38px; justify-content: center;
            letter-spacing: -.02em; width: 38px;
        }
        .portal-brand strong { display: block; font-size: 1rem; letter-spacing: -.025em; }
        .portal-brand small {
            color: #7B8495; display: block; font-size: .64rem;
            letter-spacing: .08em; margin-top: 1px;
        }
        .portal-nav {
            align-items: center; display: flex; flex-wrap: wrap; gap: 5px;
            justify-content: flex-end;
        }
        .portal-nav span {
            border-radius: 10px; color: #4E586B !important; font-size: .8rem;
            font-weight: 750; padding: 8px 11px; text-decoration: none !important;
        }
        .portal-hero {
            background: linear-gradient(128deg, #F8FAFF 0%, #EDF2FF 58%, #E2E9FF 100%);
            border: 1px solid #DCE4FA; border-radius: 27px;
            box-shadow: 0 18px 50px rgba(17,28,66,.075); display: grid; gap: 34px;
            grid-template-columns: minmax(0,1.5fr) minmax(260px,.7fr);
            margin-bottom: 18px; overflow: hidden; padding: 42px 46px; position: relative;
        }
        .portal-hero::after {
            background: radial-gradient(circle, rgba(42,82,220,.19), transparent 66%);
            content: ""; height: 330px; position: absolute; right: -80px;
            top: -145px; width: 330px;
        }
        .portal-hero__copy { position: relative; z-index: 1; }
        .portal-hero__eyebrow {
            color: var(--blue, #1428A0); font-size: .72rem; font-weight: 900;
            letter-spacing: .15em;
        }
        .portal-hero h1 {
            font-size: 3.1rem !important; line-height: 1.1; margin: 9px 0 13px;
            max-width: 720px;
        }
        .portal-hero p { color: #525D71; font-size: 1rem; margin: 0; max-width: 680px; }
        .portal-hero__facts {
            align-content: center; display: grid; gap: 9px; position: relative; z-index: 1;
        }
        .portal-fact {
            background: rgba(255,255,255,.82); border: 1px solid rgba(202,213,243,.9);
            border-radius: 14px; display: flex; justify-content: space-between;
            padding: 11px 13px;
        }
        .portal-fact span { color: #697386; font-size: .75rem; }
        .portal-fact strong { color: #15265D; font-size: .82rem; }
        .portal-section-heading {
            align-items: flex-end; display: flex; justify-content: space-between;
            margin: 29px 2px 12px;
        }
        .portal-section-heading strong {
            color: var(--ink, #101114); font-size: 1.22rem;
        }
        .portal-section-heading span { color: var(--muted, #64676D); font-size: .78rem; }
        .st-key-home_portal_steps div.stButton > button {
            align-items: flex-start; background: #FFFFFF;
            border: 1px solid var(--line, #E6E8EC); border-radius: 18px;
            box-shadow: 0 10px 28px rgba(17,28,66,.045);
            color: var(--ink, #101114); justify-content: flex-start; font-weight: 600;
            min-height: 142px; padding: 20px; text-align: left; width: 100%;
        }
        .st-key-home_portal_steps div.stButton > button:hover {
            background: #F8FAFF; border-color: #B9C7F6;
            color: var(--blue, #1428A0); box-shadow: 0 15px 34px rgba(17,28,66,.085);
            transform: translateY(-2px);
        }
        .st-key-home_portal_steps div.stButton > button:focus-visible {
            outline: 3px solid rgba(20,40,160,.28); outline-offset: 3px;
        }
        .st-key-home_portal_steps div.stButton > button p {
            color: var(--muted, #64676D); font-size: .86rem; line-height: 1.65;
            text-align: left; white-space: pre-line;
        }
        .st-key-home_portal_steps div.stButton > button strong {
            color: var(--ink, #101114); font-size: 1rem;
        }
        .workflow-steps {
            background: #FFFFFF; border: 1px solid #DEE3ED; border-radius: 18px;
            box-shadow: 0 8px 24px rgba(17,28,66,.035); display: grid; gap: 0;
            grid-template-columns: repeat(3,minmax(0,1fr)); margin: 5px 0 22px;
            overflow: hidden;
        }
        .workflow-step {
            align-items: center; color: inherit !important; display: grid; gap: 12px;
            grid-template-columns: 42px minmax(0,1fr) 16px; min-height: 88px;
            padding: 14px 18px; position: relative; text-decoration: none !important;
        }
        .workflow-step:not(:last-child) {
            border-right: 1px solid var(--line, #E6E8EC);
        }
        .workflow-step__number {
            align-items: center; background: #F0F2F6; border-radius: 50%; color: #8992A3;
            display: inline-flex; font-size: .72rem; font-weight: 900; height: 38px;
            justify-content: center; width: 38px;
        }
        .workflow-step strong { color: #4E586B; display: block; font-size: .92rem; }
        .workflow-step small {
            color: #8A93A3; display: block; font-size: .7rem; line-height: 1.4;
            margin-top: 2px;
        }
        .workflow-step__arrow { color: #C7CED9; font-size: 1.2rem; }
        .workflow-step--active { background: #F7F9FF; }
        .workflow-step--active .workflow-step__number {
            background: var(--blue, #1428A0); color: #FFFFFF;
        }
        .workflow-step--active strong { color: var(--ink, #101114); }
        .workflow-step--complete .workflow-step__number {
            background: #EAF7F2; color: #087453;
        }
        .workflow-step--complete strong { color: #426257; }
        .risk-alert {
            align-items: center; border: 1px solid; border-left-width: 5px;
            border-radius: 17px; display: grid; gap: 14px;
            grid-template-columns: 46px minmax(0,1fr) auto; margin: 7px 0 20px;
            padding: 17px 18px;
        }
        .risk-alert--medium { background: #FFFCF5; border-color: #E8CC8D; color: #684B18; }
        .risk-alert--high { background: #FFF7F6; border-color: #E7AAA5; color: #7A271A; }
        .risk-alert__icon {
            align-items: center; background: rgba(255,255,255,.76);
            border: 1px solid currentColor; border-radius: 13px; display: inline-flex;
            font-size: 1.15rem; font-weight: 900; height: 42px; justify-content: center;
            width: 42px;
        }
        .risk-alert strong { display: block; font-size: 1.05rem; margin-bottom: 3px; }
        .risk-alert p {
            color: inherit; font-size: .8rem; line-height: 1.55; margin: 0; opacity: .86;
        }
        .risk-alert__meta { text-align: right; white-space: nowrap; }
        .risk-alert__meta span {
            display: block; font-size: .67rem; font-weight: 800; opacity: .72;
        }
        .risk-alert__meta b { display: block; font-size: 1.15rem; margin-top: 2px; }
        @media (max-width: 900px) {
            .portal-hero { grid-template-columns: 1fr; padding: 34px 32px; }
            .portal-hero__facts { grid-template-columns: repeat(3,minmax(0,1fr)); }
            .workflow-steps { grid-template-columns: 1fr; }
            .workflow-step { grid-template-columns: 38px minmax(0,1fr); }
            .workflow-step:not(:last-child) {
                border-bottom: 1px solid var(--line, #E6E8EC); border-right: 0;
            }
            .workflow-step__arrow { display: none; }
        }
        @media (max-width: 700px) {
            .portal-header { align-items: flex-start; flex-direction: column; gap: 9px; }
            .portal-nav { justify-content: flex-start; }
            .portal-nav span { padding: 6px 8px; }
            .portal-hero { border-radius: 22px; padding: 28px 22px; }
            .portal-hero h1 { font-size: 2.2rem !important; }
            .portal-hero__facts { grid-template-columns: 1fr; }
            .portal-section-heading {
                align-items: flex-start; flex-direction: column; gap: 3px;
            }
            .workflow-step { min-height: 74px; }
            .risk-alert {
                align-items: flex-start; grid-template-columns: 42px minmax(0,1fr);
            }
            .risk-alert__meta { grid-column: 2; text-align: left; }
        }
        @media (prefers-reduced-motion: reduce) {
            .st-key-home_portal_steps div.stButton > button { transition: none; }
            .st-key-home_portal_steps div.stButton > button:hover { transform: none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        arrow = (
            '<span class="workflow-step__arrow" aria-hidden="true">›</span>'
            if index < 3
            else ""
        )
        step_html.append(
            f'<div class="workflow-step{state_class}"{current}>'
            f'<span class="workflow-step__number">{number}</span>'
            f'<span><strong>{escape(title)}</strong>'
            f'<small>{escape(description)}</small></span>'
            f"{arrow}</div>"
        )
    st.markdown(
        f'<div class="workflow-steps" aria-label="진단 진행 과정">'
        f'{"".join(step_html)}</div>',
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
                <p>{escape(str(product_name))}의 종합 위험도는 {escape(level)}이며
                관련 규제 {int(regulation_count)}건이 확인되었습니다.
                {action}{regulation_text}</p>
            </div>
            <div class="risk-alert__meta">
                <span>RISK SCORE</span><b>{int(score)} / 100</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
