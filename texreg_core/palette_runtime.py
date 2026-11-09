"""모든 화면에 마지막으로 적용하는 TexReg Insight 브랜드 팔레트."""

from __future__ import annotations

import streamlit as st


def inject_brand_palette() -> None:
    """기존 레이아웃은 유지하고 브랜드 포인트 색상만 통일한다."""
    st.markdown(
        """
        <style>
        :root {
            --blue: #034992;
            --blue-deep: #011F46;
            --blue-soft: #EEF5FB;
            --red: #DC1925;
            --ink: #07192F;
            --muted: #607085;
            --line: #DBE4EE;
            --surface: #FFFFFF;
            --canvas: #F4F8FC;
        }
        .stApp {
            background:
                radial-gradient(circle at 92% 2%, rgba(220,25,37,.055), transparent 24rem),
                linear-gradient(180deg, #FFFFFF 0%, var(--canvas) 36%, #FFFFFF 100%);
        }
        div.stButton > button, div.stFormSubmitButton > button {
            box-shadow: 0 8px 22px rgba(3,73,146,.17);
        }
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {
            box-shadow: 0 11px 26px rgba(1,31,70,.24);
        }
        .portal-header {
            border-color: #D5E2EF;
            box-shadow: 0 10px 32px rgba(1,31,70,.07);
        }
        .portal-brand {
            align-items: center; display: flex; flex: 0 1 auto; min-width: 220px;
        }
        .portal-brand__logo {
            display: block; height: 64px; max-width: min(270px, 34vw);
            object-fit: contain; object-position: left center; width: auto;
        }
        .sidebar-brand {
            align-items: center; border-bottom: 1px solid var(--line); display: flex;
            margin-bottom: 1rem; padding: .35rem 0 1.15rem;
        }
        .sidebar-brand__logo {
            display: block; height: auto; max-width: 218px; object-fit: contain;
            object-position: left center; width: 100%;
        }
        .portal-brand__logo, .sidebar-brand__logo {
            filter: drop-shadow(0 5px 11px rgba(1,31,70,.08));
        }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
            background: var(--blue-soft); color: var(--blue);
        }
        div[data-testid="stMetric"], [data-testid="stForm"], .panel, .stat-card {
            border-color: #E0E8F0;
            box-shadow: 0 12px 34px rgba(1,31,70,.055);
        }
        .portal-hero {
            background: linear-gradient(128deg, #FBFDFF 0%, #EAF3FB 58%, #FFF1F2 100%);
            border-color: #D5E2EF;
        }
        .portal-hero::after {
            background: radial-gradient(circle, rgba(220,25,37,.14), transparent 66%);
        }
        .portal-hero__eyebrow, .page-kicker { color: #DC1925; }
        .portal-fact { border-color: rgba(190,210,229,.94); }
        .portal-fact strong { color: #033066; }
        .st-key-home_portal_steps div.stButton > button:hover {
            background: #F2F7FC;
            border-color: #9DC3E5;
        }
        .st-key-home_portal_steps div.stButton > button:focus-visible {
            outline-color: rgba(3,73,146,.27);
        }
        .input-guide {
            background: linear-gradient(90deg, rgba(3,73,146,.08), rgba(220,25,37,.035));
            border-color: rgba(3,73,146,.16);
        }
        .layer-visual {
            background: linear-gradient(145deg, #F3F8FC 0%, #FFFFFF 56%, #EAF3FB 100%);
            border-color: #D5E2EF;
        }
        .layer-stack__number { background: #033066; }
        .layer-stack__slab {
            border-color: rgba(3,73,146,.22);
            box-shadow: 0 7px 12px rgba(3,73,146,.12);
        }
        .layer-stack__item:nth-child(1) .layer-stack__slab {
            background: linear-gradient(135deg, #034992, #72B4EA);
        }
        .trace-guide { background: #F0F6FB; color: #405B75; }
        .snapshot-banner {
            background: linear-gradient(120deg, #011F46, #033066 58%, #034992);
            border-left: 4px solid #DC1925;
        }
        .workflow-step--active, .archive-step--active { background: #F0F6FB; }
        .archive-step--active .archive-step__number { background: #034992; }
        .product-trigger {
            background: #F2F7FC;
            border-color: #D5E2EF;
        }
        .product-trigger strong { color: #294762; }
        .response-summary {
            background: #EEF5FB;
            color: #294762;
        }
        .archive-metric__icon {
            background: #E7F1FA;
            color: #034992;
        }
        .archive-metric:nth-child(3) .archive-metric__icon { background: #FFF0F1; color: #DC1925; }
        .archive-guide__number {
            background: #E7F1FA;
            color: #034992;
        }
        .archive-reading-note {
            background: #EEF5FB;
            border-color: #D5E2EF;
            color: #405B75;
        }
        .archive-storage {
            background: linear-gradient(135deg, #F8FBFD, #EEF5FB);
            border-color: #D5E2EF;
        }
        .archive-storage__item strong { color: #294762; }
        @media (max-width: 700px) {
            .portal-brand { min-width: 0; }
            .portal-brand__logo { height: 58px; max-width: min(245px, 80vw); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
