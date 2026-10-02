"""규제 진단 결과와 상세 대응방안 화면."""

from html import escape
import re

import streamlit as st

from utils.data_loader import load_regulations
from utils.ui import page_heading, render_footer, risk_badge, setup_page


REGULATION_NAME_ALIASES = {
    "KC 가정용 섬유제품 안전기준": "가정용 섬유제품 안전기준",
}


def _pipe_items(value: object) -> list[str]:
    """파이프 또는 줄바꿈으로 구분한 실행 항목을 목록으로 변환한다."""
    text = str(value or "").strip()
    if not text:
        return []
    return [item.strip() for item in re.split(r"\s*\|\s*|\r?\n+", text) if item.strip()]


def _detail_items(value: object) -> list[str]:
    """상세 항목은 파이프를 우선하고 기존 쉼표 형식도 지원한다."""
    items = _pipe_items(value)
    if len(items) == 1 and "," in items[0]:
        return [item.strip() for item in items[0].split(",") if item.strip()]
    return items


def _render_detail_list(value: object, empty_text: str = "추가 확인 필요") -> None:
    """규제 DB의 구분 문자열을 읽기 쉬운 불릿 목록으로 표시한다."""
    items = _detail_items(value)
    if not items:
        st.caption(empty_text)
        return
    for item in items:
        st.markdown(f"- {escape(item)}")


setup_page("진단 결과")
page_heading(
    "ASSESSMENT RESULT",
    "규제 진단 결과",
    "매칭된 규제와 점수 근거를 확인하고 우선 대응항목을 검토하세요.",
)

result = st.session_state.get("current_result")

if not result:
    st.warning("아직 진단 결과가 없습니다. 먼저 제품 정보를 입력해 주세요.")
    if st.button("제품 정보 입력하기", type="primary"):
        st.switch_page("pages/1_Product_Input.py")
    render_footer()
    st.stop()

product = result["제품"]
score = int(result["score"])
level = result["위험도"]

# 세션에 저장된 과거 진단도 최신 대응방안 DB로 보강한다.
latest_regulations = {
    (str(row.get("국가", "")), str(row.get("규제명", ""))): row
    for row in load_regulations().to_dict(orient="records")
}
matches = []
for match in result["규제"]:
    lookup_name = REGULATION_NAME_ALIASES.get(
        str(match.get("규제명", "")),
        str(match.get("규제명", "")),
    )
    latest = latest_regulations.get(
        (str(match.get("국가", "")), lookup_name),
        {},
    )
    matches.append({**match, **latest})

st.markdown(f"### {escape(product['제품명'])}")
st.caption(
    f"{product.get('소재', '-')} · {product.get('가공방법', '-') or '가공정보 없음'} · "
    f"판매·수출국 {product.get('수출국', '-')}"
)

score_col, risk_col, count_col = st.columns([1.2, 1, 1])
with score_col:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">Risk Score</div>
            <div><span class="score-number">{score}</span><span class="score-total"> / 100</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with risk_col:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">종합 위험도</div>
            <div style="margin-top:.8rem;">{risk_badge(level)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with count_col:
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">관련 규제</div>
            <div class="stat-value">{len(matches)}개</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.progress(score / 100, text=f"Risk Score {score}점")

st.markdown("### 관련 규제 목록")
if not matches:
    st.success("현재 예시 규칙에서는 직접 매칭된 규제가 없습니다. 수출국 기본점검과 공급망 증빙은 계속 관리하세요.")
else:
    for match in matches:
        st.markdown(
            f"""
            <div class="reg-row">
                <div>
                    <span class="reg-label">규제명</span>
                    <span class="reg-name">{escape(str(match['규제명']))}</span>
                </div>
                <div>
                    <span class="reg-label">관련성</span>
                    <strong>{escape(str(match['관련성']))}</strong>
                </div>
                <div>
                    <span class="reg-label">위험도</span>
                    {risk_badge(str(match['위험도']))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

if matches:
    st.markdown("### 실행형 상세 대응방안")
    selected_name = st.selectbox(
        "상세 확인할 규제",
        [match["규제명"] for match in matches],
        label_visibility="collapsed",
    )
    selected = next(match for match in matches if match["규제명"] == selected_name)

    st.markdown(
        f"""
        <div class="callout">
            <strong>{escape(str(selected['규제명']))}</strong><br>
            <span style="color:#52606D;">{escape(str(selected.get('기준', '')))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    product_triggers = [
        reason
        for reason in selected.get("매칭근거", [])
        if not str(reason).startswith("대상 시장")
    ]
    if product_triggers:
        trigger_text = " · ".join(escape(str(reason)) for reason in product_triggers)
        st.markdown(
            f"""
            <div class="product-trigger">
                <span>이 제품의 우선 확인 포인트</span>
                <strong>{trigger_text}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    response_summary = selected.get("대응요약") or selected.get("대응방안", "-")
    st.markdown("#### 대응 목표")
    st.markdown(f'<div class="response-summary">{escape(str(response_summary))}</div>', unsafe_allow_html=True)

    st.markdown("#### 1. 즉시 실행 순서")
    action_steps = _pipe_items(selected.get("즉시조치") or selected.get("대응방안"))
    step_html = "".join(
        f"""
        <div class="action-step">
            <span class="action-index">{index:02d}</span>
            <div>{escape(step)}</div>
        </div>
        """
        for index, step in enumerate(action_steps, start=1)
    )
    st.markdown(f'<div class="action-list">{step_html}</div>', unsafe_allow_html=True)

    st.markdown("#### 2. 확인·시험과 증빙")
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("**권장 확인·시험**")
            _render_detail_list(selected.get("권장시험") or selected.get("확인사항"))
    with right:
        with st.container(border=True):
            st.markdown("**확보해야 할 자료**")
            _render_detail_list(selected.get("필요자료상세") or selected.get("필요자료"))

    st.markdown("#### 3. 책임·일정과 완료 기준")
    owner_col, schedule_col, priority_col = st.columns(3)
    with owner_col:
        st.markdown(
            f'<div class="action-meta"><span>주관·협업 부서</span><strong>{escape(str(selected.get("담당부서", "품질·규제 담당")))}</strong></div>',
            unsafe_allow_html=True,
        )
    with schedule_col:
        st.markdown(
            f'<div class="action-meta"><span>권장 완료 시점</span><strong>{escape(str(selected.get("권장일정", "출하 전")))}</strong></div>',
            unsafe_allow_html=True,
        )
    with priority_col:
        st.markdown(
            f'<div class="action-meta"><span>대응 우선순위</span><div>{risk_badge(str(selected.get("우선순위", "보통")))}</div></div>',
            unsafe_allow_html=True,
        )

    completion = selected.get("완료기준") or "검토 결과와 근거자료가 제품별 기술문서에 승인·보관된 상태"
    st.markdown(
        f"""
        <div class="completion-box">
            <span>완료 기준</span>
            <strong>{escape(str(completion))}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    caution = str(selected.get("실무주의사항", "")).strip()
    if caution:
        st.warning(f"실무상 주의: {caution}")

    source_url = str(selected.get("공식출처", "")).strip()
    if source_url.startswith(("https://", "http://")):
        st.link_button("공식 규제 원문 확인", source_url, width="stretch")
    st.caption(
        "규제 데이터 검토 기준일: 2026-10-01 · 실제 출시 전에는 공식 원문 최신본과 적용 예외를 다시 확인하세요."
    )

    with st.expander("매칭 근거와 점수 산정 방식"):
        for reason in selected.get("매칭근거", []):
            st.markdown(f"- {reason}")
        st.caption(
            f"이 규제의 기여점수는 {selected['기여점수']}점입니다. "
            "총점은 상위 3개 규제 기여도를 차등 반영합니다. 100점은 3개 이상 시장, "
            "8개 이상 관련 규제, 50점 이상 핵심규제 3개가 모두 충족될 때만 부여합니다."
        )

action_col1, action_col2, spacer = st.columns([1, 1, 2])
with action_col1:
    if st.button("다른 제품 진단", width="stretch"):
        st.switch_page("pages/1_Product_Input.py")
with action_col2:
    if st.button("Dashboard 보기", type="primary", width="stretch"):
        st.switch_page("pages/3_Risk_Dashboard.py")

render_footer()
