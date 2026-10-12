"""최신 규제 모니터링 화면 전용 UI."""

from __future__ import annotations

from html import escape

import streamlit as st


def inject_monitor_styles() -> None:
    st.markdown(
        """
        <style>
        .monitor-hero {
            align-items: center; background: linear-gradient(135deg,#101D3B,#173F9D);
            border-radius: 22px; color: #FFFFFF; display: grid; gap: 20px;
            grid-template-columns: minmax(0,1fr) auto; margin: 2px 0 20px;
            padding: 24px 28px; box-shadow: 0 16px 42px rgba(16,29,59,.16);
        }
        .monitor-hero__eyebrow { color: #AFC6FF; font-size: .7rem; font-weight: 900; letter-spacing: .14em; }
        .monitor-hero strong { display: block; font-size: 1.12rem; margin-top: 7px; }
        .monitor-hero p { color: #D7E2FF; font-size: .78rem; line-height: 1.6; margin: 6px 0 0; }
        .monitor-hero__status {
            background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.22);
            border-radius: 14px; min-width: 178px; padding: 13px 16px; text-align: right;
        }
        .monitor-hero__status span { color: #BFD0F7; display: block; font-size: .66rem; }
        .monitor-hero__status b { display: block; font-size: .86rem; margin-top: 4px; }
        .monitor-metrics {
            display: grid; gap: 14px; grid-template-columns: repeat(4,minmax(0,1fr)); margin-bottom: 20px;
        }
        .monitor-metric {
            background: #FFFFFF; border: 1px solid #E0E6EF; border-radius: 18px;
            box-shadow: 0 9px 26px rgba(17,28,66,.045); min-height: 111px; padding: 17px 19px;
        }
        .monitor-metric span { color: #718096; display: block; font-size: .73rem; }
        .monitor-metric strong { color: #101828; display: block; font-size: 1.8rem; line-height: 1; margin-top: 14px; }
        .monitor-metric small { color: #98A2B3; display: block; font-size: .66rem; margin-top: 8px; }
        .monitor-note {
            background: #FFF9EB; border: 1px solid #EFDDAE; border-left: 5px solid #C99A2E;
            border-radius: 16px; color: #6B572D; font-size: .76rem; line-height: 1.65;
            margin: 12px 0 18px; padding: 15px 17px;
        }
        .monitor-note strong { color: #493A1D; display: block; font-size: .84rem; margin-bottom: 3px; }
        .monitor-flow {
            display: grid; gap: 10px; grid-template-columns: repeat(4,minmax(0,1fr)); margin: 14px 0 20px;
        }
        .monitor-flow__item { background: #F7F9FC; border: 1px solid #E3E8F0; border-radius: 15px; padding: 14px; }
        .monitor-flow__item b { color: #1F3EA6; display: block; font-size: .72rem; }
        .monitor-flow__item strong { color: #344054; display: block; font-size: .78rem; margin-top: 5px; }
        .monitor-flow__item small { color: #7C8798; display: block; font-size: .65rem; line-height: 1.5; margin-top: 3px; }
        @media (max-width: 900px) {
            .monitor-metrics, .monitor-flow { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 650px) {
            .monitor-hero { align-items: start; grid-template-columns: 1fr; padding: 22px; }
            .monitor-hero__status { text-align: left; }
            .monitor-metrics, .monitor-flow { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_monitor_hero(last_checked: str, running: bool) -> None:
    status = "자동 확인 운영 중" if running else "첫 자동 확인 대기"
    checked = last_checked or "아직 실행되지 않음"
    st.markdown(
        f"""
        <section class="monitor-hero">
            <div>
                <div class="monitor-hero__eyebrow">OFFICIAL SOURCE WATCH</div>
                <strong>공식 규제 원문과 국가별 공고를 6시간마다 확인합니다.</strong>
                <p>등록 규제의 본문 변경과 신규 공고 후보를 분리해 수집하고 검토 대기 목록으로 보존합니다.</p>
            </div>
            <div class="monitor-hero__status"><span>{escape(status)}</span><b>{escape(checked)}</b></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_monitor_metrics(metrics: list[tuple[str, str, str]]) -> None:
    cards = "".join(
        f'<div class="monitor-metric"><span>{escape(label)}</span><strong>{escape(value)}</strong>'
        f'<small>{escape(note)}</small></div>'
        for label, value, note in metrics
    )
    st.markdown(f'<div class="monitor-metrics">{cards}</div>', unsafe_allow_html=True)


def render_monitor_notice() -> None:
    st.markdown(
        """
        <div class="monitor-note" role="note">
            <strong>자동 감지는 법률 판단이 아닙니다.</strong>
            공식 페이지 변경이나 신규 문서 후보가 감지되어도 Risk Score는 즉시 바뀌지 않습니다.
            담당자가 적용 범위·시행일·예외를 확인하고 승인 DB를 갱신한 뒤 제품을 재진단합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_monitor_flow() -> None:
    items = [
        ("01", "자동 수집", "공식 API·Atom·공고 페이지 확인"),
        ("02", "변경 감지", "신규 문서와 원문 지문 변화 분리"),
        ("03", "담당자 검토", "법적 효력·범위·시행일 확인"),
        ("04", "승인 후 재진단", "규제 DB 반영과 제품 영향 분석"),
    ]
    html = "".join(
        f'<div class="monitor-flow__item"><b>{number}</b><strong>{escape(title)}</strong>'
        f'<small>{escape(description)}</small></div>'
        for number, title, description in items
    )
    st.markdown(f'<div class="monitor-flow">{html}</div>', unsafe_allow_html=True)

