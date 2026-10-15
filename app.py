"""TexReg Insight 포털형 홈 화면."""

from inspect import signature

import streamlit as st

from texreg_core.data_loader import load_products, load_regulations
from texreg_core.palette_runtime import inject_brand_palette
from texreg_core.portal_ui import inject_portal_styles, render_portal_header
from texreg_core.sidebar_runtime import install_sidebar_patch

install_sidebar_patch()

from texreg_core.ui import render_footer, setup_page, stat_card


if "sidebar_state" in signature(setup_page).parameters:
    setup_page("Home", sidebar_state="collapsed")
else:
    # 배포 직후 이전 공용 UI 모듈이 잠시 남아 있어도 홈을 정상 구동한다.
    setup_page("Home")
inject_portal_styles()
inject_brand_palette()

products = load_products()
regulations = load_regulations()
has_result = bool(st.session_state.get("current_result"))

render_portal_header()

st.markdown(
    f"""
    <section class="portal-hero">
        <div class="portal-hero__copy">
            <div class="portal-hero__eyebrow">GLOBAL TEXTILE COMPLIANCE PORTAL</div>
            <h1>섬유제품 규제 진단을<br>한곳에서.</h1>
            <p>제품의 소재·구조·가공 정보와 판매 시장을 바탕으로 관련 규제를 선별하고 Risk Score와 실행 가능한 대응과제를 제시합니다.</p>
        </div>
        <div class="portal-hero__facts" aria-label="서비스 현황">
            <div class="portal-fact"><span>판매 시장</span><strong>12개 국가·권역</strong></div>
            <div class="portal-fact"><span>규제 데이터</span><strong>{len(regulations)}개 항목</strong></div>
            <div class="portal-fact"><span>예시 제품</span><strong>{len(products)}개 제품</strong></div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

cta_col, note_col = st.columns([1.25, 3.75])
with cta_col:
    if st.button("내 제품 규제 진단하기", type="primary", width="stretch"):
        st.switch_page("pages/1_Product_Input.py")
with note_col:
    st.caption("약 2분이면 제품별 1차 스크리닝 결과를 확인할 수 있습니다.")

st.markdown(
    """
    <div class="portal-section-heading">
        <strong>진단 프로세스</strong>
        <span>원하는 단계를 선택해 업무를 시작하세요.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(key="home_portal_steps"):
    step_columns = st.columns(3, gap="medium")
    with step_columns[0]:
        open_input = st.button(
            "**01  제품 정보 입력**\n\n소재·구조·가공과 판매 시장을 등록합니다.  →",
            key="home_step_input",
            width="stretch",
        )
    with step_columns[1]:
        open_diagnosis = st.button(
            "**02  규제 진단**\n\n관련 규제와 종합 Risk Score를 확인합니다.  →",
            key="home_step_diagnosis",
            width="stretch",
        )
    with step_columns[2]:
        open_response = st.button(
            "**03  대응 가이드**\n\n필요 자료와 우선 대응 순서를 검토합니다.  →",
            key="home_step_response",
            width="stretch",
        )

if open_input:
    st.switch_page("pages/1_Product_Input.py")
if open_diagnosis or open_response:
    # 아직 진단하지 않았다면 입력 화면부터 시작하고, 결과가 있으면 세션을 유지한 채 이동한다.
    st.switch_page(
        "pages/2_Diagnosis_Result.py" if has_result else "pages/1_Product_Input.py"
    )

st.markdown(
    """
    <div class="portal-section-heading">
        <strong>규제 포털 현황</strong>
        <span>CSV 규제 데이터와 저장된 제품 진단을 기반으로 표시합니다.</span>
    </div>
    """,
    unsafe_allow_html=True,
)
stat_columns = st.columns(3)
with stat_columns[0]:
    stat_card("예시 제품", f"{len(products)}개", "제품 데이터베이스에서 관리")
with stat_columns[1]:
    stat_card("규제 항목", f"{len(regulations)}개", "12개 판매 시장")
with stat_columns[2]:
    stat_card("진단 방식", "규칙 기반", "국가·물질·공정·소재·용도")

db_col, spacer = st.columns([1.25, 3.75])
with db_col:
    if st.button("제품 데이터베이스 열기", width="stretch"):
        st.switch_page("pages/3_Risk_Dashboard.py")

render_footer()
