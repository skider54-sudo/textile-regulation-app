"""TexReg Insight 홈 화면."""

import streamlit as st

from texreg_core.data_loader import load_products, load_regulations
from texreg_core.ui import render_footer, setup_page, stat_card


setup_page("Home")

products = load_products()
regulations = load_regulations()

st.markdown(
    f"""
    <section class="hero">
        <div class="hero-copy">
            <div class="hero-kicker">TEXTILE COMPLIANCE INTELLIGENCE</div>
            <h1>복잡한 국내외 규제,<br>한눈에 명확하게.</h1>
            <p>제품 정보와 판매 시장을 바탕으로 관련 환경·화학물질 규제를 선별하고 Risk Score와 우선 대응과제를 제시합니다.</p>
            <div class="hero-tags">
                <span>EU</span><span>미국</span><span>영국</span><span>일본</span><span>중국</span><span>캐나다</span><span>호주</span><span>대한민국</span>
                <span>{len(regulations)} Regulations</span>
            </div>
        </div>
        <div class="hero-orbit" aria-hidden="true">
            <div style="text-align:center;">
                <div class="orbit-score">100</div>
                <div class="orbit-label">RISK SCORE</div>
            </div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

button_col, note_col = st.columns([1.25, 3.75])
with button_col:
    if st.button("내 제품 규제 진단하기", type="primary", width="stretch"):
        st.switch_page("pages/1_Product_Input.py")
with note_col:
    st.caption("약 2분이면 제품별 1차 스크리닝 결과를 확인할 수 있습니다.")

st.markdown("### 진단 프로세스")
steps = [
    ("01", "제품 정보 입력", "소재, 가공, 화학물질, 용도와 수출국을 등록합니다."),
    ("02", "관련 규제 매칭", "국가와 핵심 키워드 기반으로 검토 대상 규제를 찾습니다."),
    ("03", "Risk Score 산정", "조건이 많이 일치할수록 규제별 기여점수와 총점이 올라갑니다."),
    ("04", "대응방안 확인", "필요자료, 확인사항과 우선 조치를 규제별로 제시합니다."),
]
step_columns = st.columns(4)
for column, (number, title, description) in zip(step_columns, steps):
    with column:
        st.markdown(
            f"""
            <div class="flow-card">
                <span class="flow-number">{number}</span>
                <h3>{title}</h3>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("### 프로토타입 데이터")
stat_columns = st.columns(3)
with stat_columns[0]:
    stat_card("예시 제품", f"{len(products)}개", "CSV에서 관리")
with stat_columns[1]:
    stat_card("규제 항목", f"{len(regulations)}개", "8개 판매 시장")
with stat_columns[2]:
    stat_card("진단 방식", "규칙 기반", "국가·물질·공정·소재·용도")

render_footer()
