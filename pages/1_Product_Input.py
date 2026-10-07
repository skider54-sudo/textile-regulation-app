import json

import streamlit as st

from texreg_core.data_loader import load_regulations
from texreg_core.history import save_diagnosis_snapshot
from texreg_core.matching import diagnose_product
from texreg_core.ui import page_heading, render_footer, render_layer_stack, setup_page


setup_page("제품 규제 진단")


MATERIAL_OPTIONS = [
    "선택 안 함",
    "Polyester",
    "Nylon",
    "Cotton",
    "Organic Cotton",
    "Spandex",
    "Wool",
    "Rayon",
    "Acrylic",
    "Polypropylene",
    "Linen",
    "Modal",
    "Tencel / Lyocell",
    "Recycled Polyester",
    "기타",
    "미확인",
]

DESTINATION_OPTIONS = [
    "EU",
    "미국",
    "영국",
    "일본",
    "중국",
    "베트남",
    "인도",
    "대만",
    "캐나다",
    "호주",
    "뉴질랜드",
    "대한민국",
]

PRODUCT_USE_BY_FORM = {
    "원사": ["의류용 원사", "산업용 원사", "홈텍스타일용 원사", "기타"],
    "원단": [
        "일상 의류",
        "아웃도어 의류",
        "스포츠 의류",
        "작업복",
        "산업용 섬유",
        "생활용 섬유·홈텍스타일",
        "유아용 섬유",
        "기타",
    ],
    "의류 완제품": [
        "일상 의류",
        "아웃도어 의류",
        "스포츠 의류",
        "스포츠 수영복",
        "작업복",
        "유아용 의류",
        "아동용 의류",
        "성인용 잠옷",
        "유아용 잠옷",
        "아동용 잠옷",
        "의료용 가운",
        "기타",
    ],
    "신발": ["일반 신발", "스포츠·아웃도어 신발", "아동용 신발", "안전화·작업화", "기타"],
    "가방·액세서리": ["가방", "패션 액세서리", "아웃도어 장비", "아동용 액세서리", "기타"],
    "산업용 섬유": ["산업용 섬유", "산업용 보호장갑", "자동차 내장재", "필터·보강재", "기타"],
    "부자재": ["의류 부자재", "신발 부자재", "가방 부자재", "산업용 부자재", "기타"],
    "기타": [
        "일상 의류",
        "아웃도어 의류",
        "스포츠 의류",
        "캠핑용 텐트",
        "생활용 섬유·홈텍스타일",
        "산업용",
        "기타",
    ],
}


def _resolve_other(choice, custom_value):
    """'기타' 선택 시 사용자가 적은 실제 값을 반환한다."""
    if choice == "기타":
        return custom_value.strip()
    return choice


def _resolve_multiple(choices, custom_value):
    """다중 선택값에서 '기타'를 실제 입력값으로 바꾸고 빈 값을 제거한다."""
    resolved = []
    for choice in choices:
        if choice == "기타":
            if custom_value.strip():
                resolved.append(custom_value.strip())
        else:
            resolved.append(choice)
    return _unique(resolved)


def _unique(values):
    """입력 순서를 유지하면서 빈 값과 중복을 제거한다."""
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def _join(values):
    values = _unique(values)
    return ", ".join(values) if values else "없음"


page_heading(
    "PRODUCT PROFILE",
    "제품 정보 입력",
    "제품의 형태, 혼용률, 구조와 가공 정보를 입력하면 해당 조건을 규제 DB와 교차 분석합니다.",
)

st.markdown(
    """
    <div class="input-guide">
        <span class="input-guide__eyebrow">INPUT GUIDE</span>
        <strong>확인된 정보만 입력해도 진단할 수 있습니다.</strong>
        <span>확인이 어려운 항목은 ‘미확인’을 선택하세요. 미확인 정보는 결과 화면에서 추가 확인 과제로 안내됩니다.</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ① 기본 정보
with st.container(border=True):
    st.markdown(
        """
        <div class="input-section-heading">
            <span class="input-section-number">01</span>
            <div><strong>기본 정보</strong><span>이 제품은 무엇이며, 어떻게 사용됩니까?</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    product_name = st.text_input(
        "제품명 *",
        placeholder="예: 여성용 경량 방수 재킷",
        help="내부에서 제품을 구분할 수 있는 모델명 또는 품명을 입력하세요.",
        key="product_name",
    )

    basic_left, basic_right = st.columns(2, gap="large")
    with basic_left:
        product_form = st.selectbox(
            "제품 형태 *",
            list(PRODUCT_USE_BY_FORM),
            index=2,
            help="같은 소재라도 원단, 완제품, 신발 등 제품 형태에 따라 적용 규제가 달라질 수 있습니다.",
            key="product_form",
        )

        use_options = PRODUCT_USE_BY_FORM[product_form]
        if st.session_state.get("product_use") not in use_options:
            st.session_state["product_use"] = use_options[0]
        product_use_choice = st.selectbox(
            "제품 용도 *",
            use_options,
            help="제품 형태에 맞는 용도만 표시됩니다.",
            key="product_use",
        )
        custom_use = st.text_input(
            "기타 제품 용도",
            placeholder="예: 수상 스포츠용 웨트슈트",
            disabled=product_use_choice != "기타",
            key="custom_product_use",
        )

    with basic_right:
        skin_contact = st.selectbox(
            "피부 접촉 여부 *",
            ["직접·장시간 접촉", "일부·간헐적 접촉", "접촉 없음", "미확인"],
            help="착용 또는 사용 중 피부와 접촉하는 수준을 선택하세요.",
            key="skin_contact",
        )

        # 규제 DB가 준비된 시장만 선택지로 제공한다.
        destinations = st.multiselect(
            "판매·수출국 *",
            DESTINATION_OPTIONS,
            placeholder="하나 이상 선택하세요",
            help="여러 국가에 판매하는 경우 모두 선택하세요. 선택 시장별 규제를 함께 진단합니다.",
            key="destinations",
        )


# ② 제품 구조
with st.container(border=True):
    st.markdown(
        """
        <div class="input-section-heading">
            <span class="input-section-number">02</span>
            <div><strong>제품 구조</strong><span>이 제품을 구성하는 원단과 기능성 층을 입력하세요.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    composition_unknown = st.checkbox(
        "혼용률 미확인",
        help="소재는 알지만 정확한 함량을 확인하기 어려운 경우 선택하세요.",
        key="composition_unknown",
    )
    st.caption("Base fabric · 소재를 최대 4개까지 선택하고, 확인된 혼용률의 합계가 100%가 되도록 입력하세요.")

    composition_inputs = []
    for index in range(1, 5):
        material_col, ratio_col, custom_col = st.columns([2.0, 1.0, 2.0], gap="small")
        with material_col:
            material_choice = st.selectbox(
                f"구성 {index} 소재",
                MATERIAL_OPTIONS,
                index=1 if index == 1 else 0,
                key=f"material_{index}",
            )
        with ratio_col:
            ratio = st.number_input(
                f"구성 {index} 함량 (%)",
                min_value=0.0,
                max_value=100.0,
                value=100.0 if index == 1 else 0.0,
                step=1.0,
                disabled=composition_unknown,
                key=f"material_ratio_{index}",
            )
        with custom_col:
            custom_material = st.text_input(
                f"구성 {index} 기타 소재명",
                placeholder="예: Aramid",
                disabled=material_choice != "기타",
                key=f"custom_material_{index}",
            )
        composition_inputs.append((material_choice, ratio, custom_material))

    has_custom_material = any(
        material_choice == "기타" for material_choice, _, _ in composition_inputs
    )
    custom_material_type = st.selectbox(
        "기타 소재 유형",
        ["섬유", "비섬유", "미확인"],
        help=(
            "기타 소재가 섬유인지 명시하면 규제 범위를 더 정확히 판정할 수 있습니다. "
            "여러 기타 소재를 입력했다면 섬유가 하나라도 포함된 경우 ‘섬유’를 선택하세요."
        ),
        disabled=not has_custom_material,
        key="custom_material_type",
    )

    total_ratio = sum(
        ratio
        for material_choice, ratio, _ in composition_inputs
        if material_choice != "선택 안 함"
    )
    if composition_unknown:
        total_class = "unknown"
        total_message = "혼용률 미확인 · 진단 후 공급망 확인 필요"
    elif abs(total_ratio - 100.0) < 0.01:
        total_class = "valid"
        total_message = f"혼용률 합계 {total_ratio:g}% · 입력 완료"
    else:
        total_class = "invalid"
        total_message = f"혼용률 합계 {total_ratio:g}% · 100%가 되도록 조정하세요"
    st.markdown(
        f'<div class="composition-total {total_class}">{total_message}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="input-subheading">기능성 구조 및 후가공</div>', unsafe_allow_html=True)
    structure_left, structure_right = st.columns(2, gap="large")

    with structure_left:
        membrane_choices = st.multiselect(
            "Membrane",
            ["PU 멤브레인", "TPU 멤브레인", "PTFE/ePTFE 멤브레인", "PE 멤브레인", "기타", "미확인"],
            placeholder="적용된 멤브레인을 모두 선택하세요",
            help="복합 구조라면 여러 개를 선택할 수 있습니다. 해당 층이 없으면 비워 두세요.",
            key="membranes",
        )
        custom_membrane = st.text_input(
            "기타 Membrane",
            placeholder="멤브레인 소재 또는 상품명",
            disabled="기타" not in membrane_choices,
            key="custom_membrane",
        )

        coating_choices = st.multiselect(
            "Coating",
            ["PU 코팅", "PVC 코팅", "Acrylic 코팅", "Silicone 코팅", "기타", "미확인"],
            placeholder="적용된 코팅을 모두 선택하세요",
            help="앞·뒷면 또는 복수 층에 다른 코팅이 적용됐다면 모두 선택하세요.",
            key="coatings",
        )
        custom_coating = st.text_input(
            "기타 Coating",
            placeholder="코팅 종류 또는 상품명",
            disabled="기타" not in coating_choices,
            key="custom_coating",
        )

    with structure_right:
        lamination_choices = st.multiselect(
            "Lamination",
            ["PU 접착제", "Hot-melt 접착제", "수계 접착제", "용제형 접착제", "기타", "미확인"],
            placeholder="적용된 접착 시스템을 모두 선택하세요",
            help="부위나 층별로 접착 시스템이 다르면 여러 개를 선택할 수 있습니다.",
            key="laminations",
        )
        custom_lamination = st.text_input(
            "기타 Lamination",
            placeholder="접착제 종류 또는 상품명",
            disabled="기타" not in lamination_choices,
            key="custom_lamination",
        )

        finishings = st.multiselect(
            "Finishing",
            ["DWR 발수 가공", "방오 가공", "난연 가공", "항균 가공", "유연 가공", "주름방지 가공", "워싱", "기타", "미확인"],
            placeholder="적용된 후가공을 모두 선택하세요",
            key="finishings",
        )
        custom_finishing = st.text_input(
            "후가공제·상품명",
            placeholder="예: C0 DWR / 공급업체 상품명 / 미확인",
            help="정확한 성분을 모르면 상품명 또는 ‘미확인’으로 입력하세요.",
            key="custom_finishing",
        )

    preview_components = []
    for material_choice, ratio, custom_material in composition_inputs:
        if material_choice == "선택 안 함":
            continue
        material_name = _resolve_other(material_choice, custom_material) or "기타 소재 (상세 미입력)"
        if composition_unknown:
            preview_components.append(f"{material_name} (함량 미확인)")
        elif ratio > 0:
            preview_components.append(f"{material_name} {ratio:g}%")

    membrane_values = _resolve_multiple(membrane_choices, custom_membrane)
    coating_values = _resolve_multiple(coating_choices, custom_coating)
    lamination_values = _resolve_multiple(lamination_choices, custom_lamination)
    preview_membrane = _join(membrane_values)
    preview_coating = _join(coating_values)
    preview_lamination = _join(lamination_values)
    preview_finishing = _join([*finishings, custom_finishing.strip()])
    render_layer_stack(
        ", ".join(preview_components) or "미확인",
        preview_membrane,
        preview_coating,
        preview_lamination,
        preview_finishing,
        title="제품 구조 미리보기",
    )


# ③ 공정·화학물질
with st.container(border=True):
    st.markdown(
        """
        <div class="input-section-heading">
            <span class="input-section-number">03</span>
            <div><strong>공정·화학물질</strong><span>제조 단계와 확인된 화학물질 정보를 추가하세요.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    detail_left, detail_right = st.columns(2, gap="large")
    with detail_left:
        processes = st.multiselect(
            "주요 가공방법",
            [
                "편직",
                "직조",
                "부직포",
                "봉제",
                "염색",
                "프린팅",
                "발수",
                "방수",
                "코팅",
                "PU 코팅",
                "라미네이팅",
                "수지가공",
                "난연",
                "난연 코팅",
                "항균",
                "유연",
                "재활용 원사 가공",
                "기타",
                "미확인",
            ],
            placeholder="해당 공정을 모두 선택하세요",
            key="processes",
        )
        custom_process = st.text_input(
            "기타 가공방법",
            placeholder="예: 플라즈마 표면처리",
            disabled="기타" not in processes,
            key="custom_process",
        )

    with detail_right:
        chemicals = st.multiselect(
            "사용 화학물질",
            [
                "PFAS계 발수제",
                "PFAS-free 발수제",
                "C6 fluorotelomer 발수제",
                "C8 fluorotelomer 발수제",
                "PFOA",
                "PFOS",
                "포름알데히드계 수지",
                "프탈레이트계 가소제",
                "아조 염료",
                "DMF",
                "SCCP",
                "안티몬",
                "난연제",
                "항균제",
                "중점관리물질(성분명 확인 필요)",
                "미확인",
                "기타",
            ],
            placeholder="확인된 물질을 모두 선택하세요",
            help="정확한 성분을 모르면 ‘미확인’을 선택하세요.",
            key="chemicals",
        )
        custom_chemical = st.text_input(
            "기타 화학물질·상품명",
            placeholder="예: 공급업체 상품명 또는 CAS No.",
            disabled="기타" not in chemicals,
            key="custom_chemical",
        )

    structure_processes = []
    structure_processes.extend(value for value in coating_values if value != "미확인")
    structure_processes.extend(
        f"{value} 라미네이션" for value in lamination_values if value != "미확인"
    )
    structure_processes.extend(value for value in finishings if value not in {"기타", "미확인"})

    selected_processes = [value for value in processes if value not in {"기타", "미확인"}]
    if "기타" in processes:
        selected_processes.append(custom_process.strip() or "기타 가공 (상세 미입력)")
    process_detail_targets = _unique([*selected_processes, *structure_processes])

    st.markdown(
        """
        <div class="trace-guide">
            선택한 공정별로 가공제 상품명, 화학물질명, CAS No., SDS/TDS 확보 상태와 PFAS 여부를 연결할 수 있습니다.
            확인이 어려운 값은 ‘미확인’으로 두면 결과 화면의 추가 확인 과제로 남습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    process_detail_rows = []
    if not process_detail_targets:
        st.caption("주요 가공방법 또는 기능성 후가공을 선택하면 공정별 상세 입력란이 표시됩니다.")
    for sequence, process_name in enumerate(process_detail_targets, start=1):
        with st.expander(f"{sequence:02d} · {process_name} 상세정보", expanded=len(process_detail_targets) <= 2):
            product_col, substance_col, cas_col = st.columns(3, gap="small")
            with product_col:
                trade_name = st.text_input(
                    f"{process_name} 상품명·가공제",
                    placeholder="예: 공급업체 DWR 상품명",
                    key=f"trace_trade_{process_name}",
                )
            with substance_col:
                substance_name = st.text_input(
                    f"{process_name} 화학물질명",
                    placeholder="예: fluorotelomer polymer",
                    key=f"trace_substance_{process_name}",
                )
            with cas_col:
                cas_number = st.text_input(
                    f"{process_name} CAS No.",
                    placeholder="예: 123-45-6 / 미확인",
                    key=f"trace_cas_{process_name}",
                )

            document_col, pfas_col = st.columns(2, gap="small")
            with document_col:
                document_status = st.selectbox(
                    f"{process_name} SDS/TDS",
                    ["미확인", "SDS 확보", "TDS 확보", "SDS·TDS 확보", "공급업체 요청 중", "해당 없음"],
                    key=f"trace_document_{process_name}",
                )
            with pfas_col:
                pfas_status = st.selectbox(
                    f"{process_name} PFAS 여부",
                    ["미확인", "해당 없음", "PFAS-free 확인", "PFAS 사용·포함 가능"],
                    key=f"trace_pfas_{process_name}",
                )

            process_detail_rows.append(
                {
                    "공정": process_name,
                    "상품명": trade_name.strip(),
                    "화학물질명": substance_name.strip(),
                    "CAS No.": cas_number.strip(),
                    "SDS/TDS": document_status,
                    "PFAS 여부": pfas_status,
                }
            )


st.markdown(
    """
    <div class="submit-note">
        진단 결과는 입력 정보와 프로토타입 규제 DB를 기준으로 산출됩니다. 최종 법적 판단 전에는 시험성적서와 공급업체 자료를 확인하세요.
    </div>
    """,
    unsafe_allow_html=True,
)
submit = st.button("규제 진단하기", type="primary", width="stretch", key="diagnose_submit")


if submit:
    errors = []
    if not product_name.strip():
        errors.append("제품명을 입력해 주세요.")
    if not destinations:
        errors.append("판매·수출국을 하나 이상 선택해 주세요.")
    if "기타" in processes and not custom_process.strip():
        errors.append("기타 가공방법을 입력해 주세요.")
    if "기타" in chemicals and not custom_chemical.strip():
        errors.append("기타 화학물질 또는 상품명을 입력해 주세요.")
    if "기타" in finishings and not custom_finishing.strip():
        errors.append("기타 후가공제 또는 상품명을 입력해 주세요.")

    selected_components = []
    for material_choice, ratio, custom_material in composition_inputs:
        if material_choice == "선택 안 함":
            continue
        resolved_material = _resolve_other(material_choice, custom_material)
        if material_choice == "기타" and not resolved_material:
            errors.append("‘기타’로 선택한 소재명을 입력해 주세요.")
            continue
        if composition_unknown or ratio > 0:
            selected_components.append((resolved_material, ratio))

    if not selected_components:
        errors.append("Base fabric 소재를 하나 이상 입력해 주세요.")
    if not composition_unknown and abs(total_ratio - 100.0) >= 0.01:
        errors.append("Base fabric 혼용률 합계를 100%로 맞춰 주세요.")

    product_use = _resolve_other(product_use_choice, custom_use)
    if product_use_choice == "기타" and not product_use:
        errors.append("기타 제품 용도를 입력해 주세요.")

    structure_values = [
        ("Membrane", membrane_choices, custom_membrane),
        ("Coating", coating_choices, custom_coating),
        ("Lamination", lamination_choices, custom_lamination),
    ]
    resolved_structure = {}
    for label, choices, custom_value in structure_values:
        resolved_values = _resolve_multiple(choices, custom_value)
        if "기타" in choices and not custom_value.strip():
            errors.append(f"기타 {label} 정보를 입력해 주세요.")
        resolved_structure[label] = _join(resolved_values)

    if errors:
        st.error("\n".join(f"• {message}" for message in dict.fromkeys(errors)))
    else:
        if composition_unknown:
            material_summary = ", ".join(f"{name} (함량 미확인)" for name, _ in selected_components)
        else:
            material_summary = ", ".join(f"{name} {ratio:g}%" for name, ratio in selected_components)

        known_textile_selected = any(
            material_choice not in {"선택 안 함", "기타", "미확인"}
            for material_choice, _, _ in composition_inputs
        )
        if known_textile_selected or (has_custom_material and custom_material_type == "섬유"):
            material_classification = "섬유"
        elif has_custom_material and custom_material_type == "비섬유":
            material_classification = "비섬유"
        else:
            material_classification = "미확인"

        extra_processes = []
        for value in [*coating_values, *lamination_values, *finishings]:
            if value not in {"미확인", "기타"}:
                extra_processes.append(value)
        if custom_finishing.strip():
            extra_processes.append(custom_finishing.strip())

        extra_chemicals = []
        for value in [*membrane_values, *coating_values, *lamination_values]:
            if value != "미확인":
                extra_chemicals.append(value)
        if custom_finishing.strip():
            extra_chemicals.append(custom_finishing.strip())

        process_values = [value for value in processes if value != "기타"]
        if "기타" in processes and custom_process.strip():
            process_values.append(custom_process.strip())
        process_values.extend(extra_processes)

        chemical_values = [value for value in chemicals if value != "기타"]
        if "기타" in chemicals and custom_chemical.strip():
            chemical_values.append(custom_chemical.strip())
        chemical_values.extend(extra_chemicals)

        for detail in process_detail_rows:
            chemical_values.extend(
                [detail.get("상품명", ""), detail.get("화학물질명", ""), detail.get("CAS No.", "")]
            )
            if detail.get("PFAS 여부") == "PFAS 사용·포함 가능":
                chemical_values.append("PFAS")
            elif detail.get("PFAS 여부") == "PFAS-free 확인":
                chemical_values.append("PFAS-free")

        finishing_summary = _join([*finishings, custom_finishing.strip()])
        product = {
            "제품명": product_name.strip(),
            "소재": material_summary,
            "가공방법": _join(process_values),
            "사용화학물질": _join(chemical_values),
            "제품용도": product_use,
            "수출국": ", ".join(destinations),
            "제품형태": product_form,
            "피부접촉": skin_contact,
            "소재분류": material_classification,
            "혼용률상태": "미확인" if composition_unknown else "확인",
            "Base fabric": material_summary,
            "Membrane": resolved_structure["Membrane"],
            "Coating": resolved_structure["Coating"],
            "Lamination": resolved_structure["Lamination"],
            "Finishing": finishing_summary,
            "공정상세": json.dumps(process_detail_rows, ensure_ascii=False),
        }

        result = diagnose_product(product, load_regulations())
        try:
            result["history_id"] = save_diagnosis_snapshot(result)
            st.session_state.pop("history_save_error", None)
        except Exception as error:  # 진단 자체는 유지하고 저장 실패만 사용자에게 알린다.
            st.session_state["history_save_error"] = str(error)
        st.session_state["current_result"] = result
        st.session_state.setdefault("registered_products", []).append(product)
        st.switch_page("pages/2_Diagnosis_Result.py")


render_footer()
