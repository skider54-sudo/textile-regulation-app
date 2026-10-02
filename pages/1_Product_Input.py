"""섬유제품 정보 입력 화면."""

import streamlit as st

from utils.data_loader import load_regulations
from utils.matching import diagnose_product
from utils.ui import page_heading, render_footer, setup_page


setup_page("제품 규제 진단")
page_heading(
    "PRODUCT SCREENING",
    "제품 정보 입력",
    "제품 특성을 입력하면 국내외 판매 시장별 환경·화학물질 규제를 1차 진단합니다.",
)

with st.form("product_form", clear_on_submit=False):
    st.markdown("#### 기본 정보")
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input(
            "제품명 *",
            placeholder="예: EcoShell Jacket",
            help="대시보드에서 구분할 수 있는 제품명을 입력하세요.",
        )
        materials = st.multiselect(
            "소재 *",
            [
                "Polyester",
                "Recycled Polyester",
                "Nylon",
                "Cotton",
                "Organic Cotton",
                "Polypropylene",
                "Linen",
                "Spandex",
                "Wool",
                "Acrylic",
                "기타",
            ],
            placeholder="혼방 소재는 두 개 이상 선택",
            help="예: 스포츠 레깅스는 Nylon과 Spandex를 함께 선택할 수 있습니다.",
        )
        custom_material = st.text_input(
            "기타 소재 (직접 입력)",
            placeholder="예: Modal, Tencel 또는 Nylon 82% / Spandex 18%",
            help="'기타' 선택 여부와 관계없이 목록에 없는 소재나 상세 혼용률을 입력할 수 있습니다.",
        )
    with col2:
        product_use = st.selectbox(
            "제품 용도 *",
            [
                "일상 의류",
                "아웃도어 의류",
                "스포츠 의류",
                "스포츠 수영복",
                "유아용 의류",
                "유아용 섬유",
                "아동용 의류",
                "생활용 섬유",
                "가방",
                "캠핑용 텐트",
                "산업용 보호장갑",
                "의료용 가운",
                "자동차 내장재",
                "기타",
            ],
        )
        destinations = st.multiselect(
            "판매·수출국 *",
            ["EU", "미국", "영국", "일본", "대한민국"],
            placeholder="하나 이상 선택",
        )

    st.markdown("#### 공정 및 화학물질")
    col3, col4 = st.columns(2)
    with col3:
        processes = st.multiselect(
            "가공방법",
            [
                "염색",
                "발수",
                "방수",
                "코팅",
                "PU 코팅",
                "수지가공",
                "난연 코팅",
                "워싱",
                "편직",
                "부직포",
                "재활용 원사 가공",
            ],
            placeholder="해당 공정을 모두 선택",
        )
        custom_process = st.text_input("기타 가공방법", placeholder="예: 난연 가공")
    with col4:
        chemicals = st.multiselect(
            "사용 화학물질",
            [
                "PFAS계 불소수지",
                "PFAS-free 발수제",
                "C6 fluorotelomer 발수제",
                "PFOA",
                "PFOS",
                "아조염료",
                "분산염료",
                "산성염료",
                "포름알데히드계 수지가공제",
                "프탈레이트",
                "DMF",
                "SCCP",
                "안티몬",
                "중점관리물질(성분명 확인 필요)",
                "실리콘계 발수제",
                "없음",
            ],
            placeholder="알고 있는 성분을 모두 선택",
        )
        custom_chemical = st.text_input(
            "기타 화학물질",
            placeholder="SDS 기준 물질명 또는 상품명",
        )

    st.info("규제 DB와 점수 기준은 프로토타입용 예시입니다. 입력값이 구체적일수록 매칭 근거가 명확해집니다.")
    submitted = st.form_submit_button("규제 진단하기", type="primary", width="stretch")

if submitted:
    selected_materials = [value for value in materials if value != "기타"]
    if custom_material.strip():
        selected_materials.append(custom_material.strip())

    if not product_name.strip() or not selected_materials or not destinations:
        st.error("제품명, 소재, 판매·수출국은 반드시 입력해 주세요.")
    else:
        process_values = [*processes, custom_process.strip()]
        chemical_values = [*chemicals, custom_chemical.strip()]
        product = {
            "제품명": product_name.strip(),
            "소재": ", ".join(dict.fromkeys(selected_materials)),
            "가공방법": ", ".join(value for value in process_values if value),
            "사용화학물질": ", ".join(value for value in chemical_values if value) or "미입력",
            "제품용도": product_use,
            "수출국": ", ".join(destinations),
        }

        result = diagnose_product(product, load_regulations())
        st.session_state["current_result"] = result
        registered = st.session_state.setdefault("registered_products", [])
        registered.append(product)
        st.session_state["registered_products"] = registered
        st.switch_page("pages/2_Diagnosis_Result.py")

render_footer()
