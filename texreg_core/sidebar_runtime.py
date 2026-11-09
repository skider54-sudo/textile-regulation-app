"""Streamlit Cloud의 이전 UI 모듈 캐시를 우회하는 사이드바 런타임 패치."""

from __future__ import annotations

from importlib import import_module

import streamlit as st

from texreg_core.brand_assets import brand_logo_data_uri


def render_sidebar() -> None:
    """현재 배포에 존재하는 페이지만 사용해 탐색 메뉴를 표시한다."""
    logo_uri = brand_logo_data_uri()
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-brand">
                <img class="sidebar-brand__logo" src="{logo_uri}"
                     alt="TexReg Insight · Textile Regulation Portal">
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


def install_sidebar_patch() -> None:
    """캐시된 공용 UI가 있어도 삭제된 페이지를 참조하지 않도록 교체한다."""
    # import 문은 패키지 속성에 남은 예전 모듈을 다시 잡을 수 있으므로,
    # sys.modules를 기준으로 동작하는 import_module로 현재 캐시 대상을 가져온다.
    ui_module = import_module("texreg_core.ui")

    ui_module.render_sidebar = render_sidebar
