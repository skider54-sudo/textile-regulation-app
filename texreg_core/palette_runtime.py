"""모든 화면에 마지막으로 적용하는 원창머티리얼 계열 브랜드 팔레트."""

from __future__ import annotations

import streamlit as st


def inject_brand_palette() -> None:
    """기존 레이아웃은 유지하고 브랜드 포인트 색상만 통일한다."""
    st.markdown(
        """
        <style>
        :root {
            --blue: #243A8F;
            --blue-deep: #17285F;
            --blue-soft: #EEF2FA;
            --ink: #101114;
            --muted: #747477;
            --line: #E4E6EC;
            --surface: #FFFFFF;
            --canvas: #F7F8FA;
        }
        .stApp {
            background: linear-gradient(180deg, #FFFFFF 0%, var(--canvas) 36%, #FFFFFF 100%);
        }
        div.stButton > button, div.stFormSubmitButton > button {
            box-shadow: 0 8px 22px rgba(36,58,143,.15);
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            box-shadow: 0 11px 26px rgba(36,58,143,.21);
        }
        .portal-brand__mark {
            background: linear-gradient(145deg, #C7354A 0%, #C7354A 42%, #3F5FB7 58%, #243A8F 100%);
        }
        .portal-hero {
            background: linear-gradient(128deg, #FBFCFF 0%, #F0F3FA 58%, #F8EFF2 100%);
            border-color: #DCE2EE;
        }
        .portal-hero::after {
            background: radial-gradient(circle, rgba(199,53,74,.12), transparent 66%);
        }
        .portal-hero__eyebrow, .page-kicker { color: #C7354A; }
        .portal-fact { border-color: rgba(205,214,233,.92); }
        .portal-fact strong { color: #243A70; }
        .st-key-home_portal_steps div.stButton > button:hover {
            background: #F5F7FC;
            border-color: #BCC9E3;
        }
        .st-key-home_portal_steps div.stButton > button:focus-visible {
            outline-color: rgba(36,58,143,.25);
        }
        .input-guide {
            background: linear-gradient(90deg, rgba(36,58,143,.07), rgba(199,53,74,.025));
            border-color: rgba(36,58,143,.14);
        }
        .layer-visual {
            background: linear-gradient(145deg, #F8FAFE 0%, #FFFFFF 56%, #F0F3F9 100%);
            border-color: #DDE3EF;
        }
        .layer-stack__number { background: #243A70; }
        .layer-stack__slab {
            border-color: rgba(36,58,143,.2);
            box-shadow: 0 7px 12px rgba(36,58,143,.1);
        }
        .layer-stack__item:nth-child(1) .layer-stack__slab {
            background: linear-gradient(135deg, #3F5FB7, #A7B7DD);
        }
        .trace-guide { background: #F4F6FB; color: #4F5A73; }
        .snapshot-banner {
            background: linear-gradient(120deg, #17285F, #243A8F 62%, #3F5FB7);
            border-left: 4px solid #C7354A;
        }
        .workflow-step--active, .archive-step--active { background: #F4F6FB; }
        .archive-step--active .archive-step__number { background: #243A8F; }
        .product-trigger {
            background: #F6F8FC;
            border-color: #D8DFEC;
        }
        .product-trigger strong { color: #34405C; }
        .response-summary {
            background: #F1F4FA;
            color: #34405C;
        }
        .archive-metric__icon {
            background: #EEF2FA;
            color: #3F5FB7;
        }
        .archive-metric:nth-child(3) .archive-metric__icon { background: #FCF0F2; color: #C7354A; }
        .archive-guide__number {
            background: #EEF2FA;
            color: #243A8F;
        }
        .archive-reading-note {
            background: #F1F4FA;
            border-color: #D8DFEC;
            color: #445273;
        }
        .archive-storage {
            background: linear-gradient(135deg, #F9FAFD, #F1F4FA);
            border-color: #DDE3EF;
        }
        .archive-storage__item strong { color: #34405C; }
        </style>
        """,
        unsafe_allow_html=True,
    )
