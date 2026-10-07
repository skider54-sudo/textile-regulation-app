"""진단 시점의 제품·규제 스냅샷을 조회하는 제품 데이터베이스 화면."""

from html import escape
import json
import os
import re
from uuid import NAMESPACE_URL, uuid5

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_products, load_regulations
from utils.history import (
    export_history_json,
    get_diagnosis_snapshot,
    history_db_path,
    list_diagnosis_history,
    save_diagnosis_snapshot,
)
from utils.matching import diagnose_product
from utils.source_monitor import check_regulation_sources, latest_source_statuses
from utils.ui import (
    page_heading,
    regulation_status_badge,
    render_footer,
    risk_badge,
    setup_page,
)


setup_page("제품 데이터베이스")
page_heading(
    "PRODUCT & REGULATION ARCHIVE",
    "제품 데이터베이스",
    "진단 당시의 제품 정보와 규제 스냅샷을 보존하고 현재 규제 DB와의 변화를 추적합니다.",
)


COMPARE_FIELDS = {
    "규제상태": "규제 상태",
    "기준": "규제 기준",
    "시행일": "시행 정보",
    "주요시행일": "주요 시행일",
    "유예기간": "유예·전환기간",
    "최근확인일": "최근 확인일",
    "대응요약": "대응 목표",
    "공식출처": "공식 출처",
}

SOURCE_LABELS = {
    "manual": "사용자 진단",
    "session_recovered": "세션 복구",
    "reassessment": "현재 기준 재진단",
    "example": "예시 데이터",
}

SOURCE_STATE_LABELS = {
    "baseline": "기준 지문 생성",
    "unchanged": "변경 없음",
    "changed": "변경 감지·검토 필요",
    "error": "확인 실패",
}


def _format_datetime(value: object) -> str:
    """ISO 진단시각을 한국 시간 기준의 읽기 쉬운 형식으로 표시한다."""
    try:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert("Asia/Seoul")
        return timestamp.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(value or "-").replace("T", " ")[:16]


def _pipe_items(value: object) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"\s*\|\s*|\r?\n+", str(value or ""))
        if item.strip()
    ]


def _ensure_session_result_is_saved() -> None:
    """기능 도입 전에 생성된 현재 세션 결과도 한 번만 이력으로 복구한다."""
    result = st.session_state.get("current_result")
    if not result or result.get("history_id"):
        return
    try:
        result["history_id"] = save_diagnosis_snapshot(result, source="session_recovered")
        st.session_state.pop("history_save_error", None)
    except Exception as error:
        st.session_state["history_save_error"] = str(error)


def _ensure_example_history(products: pd.DataFrame, regulations: pd.DataFrame) -> None:
    """기존 대시보드의 CSV 예시 제품도 클릭 가능한 이력으로 한 번만 저장한다."""
    for product in products.to_dict(orient="records"):
        canonical = json.dumps(product, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        record_id = str(uuid5(NAMESPACE_URL, f"texreg-example-v1:{canonical}"))
        save_diagnosis_snapshot(
            diagnose_product(product, regulations),
            source="example",
            record_id=record_id,
            ignore_existing=True,
        )


def _regulation_comparison(snapshot_matches: list[dict], regulations: pd.DataFrame) -> pd.DataFrame:
    """당시 저장 규제와 현재 DB의 변경 필드를 규제별로 비교한다."""
    current_lookup = {
        (str(row.get("국가", "")), str(row.get("규제명", ""))): row
        for row in regulations.to_dict(orient="records")
    }
    rows = []
    for old in snapshot_matches:
        key = (str(old.get("국가", "")), str(old.get("규제명", "")))
        current = current_lookup.get(key)
        if current is None:
            rows.append(
                {
                    "규제명": old.get("규제명", "-"),
                    "변경 여부": "현재 DB에서 확인 필요",
                    "바뀐 항목": "삭제 또는 명칭 변경",
                    "당시 확인일": old.get("최근확인일", "미확인"),
                    "현재 확인일": "-",
                }
            )
            continue

        changed = [
            label
            for field, label in COMPARE_FIELDS.items()
            if str(old.get(field, "")).strip() != str(current.get(field, "")).strip()
        ]
        rows.append(
            {
                "규제명": old.get("규제명", "-"),
                "변경 여부": "업데이트 있음" if changed else "변경 없음",
                "바뀐 항목": ", ".join(changed) if changed else "-",
                "당시 확인일": old.get("최근확인일", "미확인"),
                "현재 확인일": current.get("최근확인일", "미확인"),
            }
        )
    return pd.DataFrame(rows)


def _source_regulations(snapshot_matches: list[dict], current_matches: list[dict]) -> list[dict]:
    """당시·현재 매칭 규제의 공식 출처를 중복 없이 합친다."""
    combined: dict[tuple[str, str], dict] = {}
    for regulation in [*snapshot_matches, *current_matches]:
        key = (str(regulation.get("국가", "")), str(regulation.get("규제명", "")))
        if key != ("", ""):
            combined[key] = regulation
    return list(combined.values())


def _render_source_monitor(record_id: str, source_regulations: list[dict]) -> None:
    """제품 규제의 공식 원문을 확인하고 페이지 변경 여부를 표시한다."""
    st.markdown("##### 공식 출처 최신성 확인")
    st.caption(
        "공식 페이지의 접속·변경 여부를 확인합니다. "
        "페이지 변경은 법적 의무 변경 확정을 의미하지 않으며, Risk Score는 검토·승인된 규제 DB 기준입니다."
    )
    if not source_regulations:
        st.info("확인할 공식 규제 출처가 없습니다.")
        return

    live_checks_enabled = os.getenv("TEXREG_LIVE_CHECKS", "1").strip().lower() not in {
        "0",
        "false",
        "off",
    }
    if live_checks_enabled:
        with st.spinner("관련 규제의 공식 출처를 확인하는 중입니다..."):
            results = check_regulation_sources(
                source_regulations,
                force=False,
            )
    else:
        results = latest_source_statuses(source_regulations)

    if st.button(
        "공식 출처 지금 다시 확인",
        width="stretch",
        key=f"refresh_sources_{record_id}",
        help="6시간 캐시를 무시하고 공식 원문을 다시 확인합니다.",
    ):
        with st.spinner("공식 출처를 강제 새로고침하는 중입니다..."):
            results = check_regulation_sources(
                source_regulations,
                force=True,
            )

    if not results:
        if live_checks_enabled:
            st.info("아직 공식 출처 확인 결과가 없습니다. 잠시 후 다시 확인해 주세요.")
        else:
            st.info("테스트·오프라인 모드에서는 자동 공식 출처 확인을 생략합니다.")
        return

    changed_count = sum(result.get("state") == "changed" for result in results)
    error_count = sum(result.get("state") == "error" for result in results)
    success_count = len(results) - error_count
    latest_checked = max((str(result.get("checked_at", "")) for result in results), default="")
    summary_columns = st.columns(4)
    summary_columns[0].metric("확인 출처", f"{len(results)}개")
    summary_columns[1].metric("정상 확인", f"{success_count}개")
    summary_columns[2].metric("변경 감지", f"{changed_count}개")
    summary_columns[3].metric("마지막 확인", _format_datetime(latest_checked))

    if changed_count:
        st.warning(
            "공식 페이지 본문 변경이 감지됐습니다. 현재 Risk Score는 기존 승인 DB 기준이며, "
            "시행일·기준·예외조항을 검토해 규제 DB를 갱신해야 합니다."
        )
    if error_count:
        st.warning(
            f"{error_count}개 출처를 현재 확인하지 못했습니다. 실패를 '변경 없음'으로 처리하지 않았습니다."
        )

    rows = []
    for result in results:
        checked_at = _format_datetime(result.get("checked_at"))
        last_success = (
            _format_datetime(result.get("last_successful_at"))
            if result.get("last_successful_at")
            else "-"
        )
        rows.append(
            {
                "관할": result.get("country", "-"),
                "규제명": result.get("regulation_name", "-"),
                "확인 상태": SOURCE_STATE_LABELS.get(str(result.get("state", "")), "미확인"),
                "확인 시각": checked_at,
                "마지막 정상 확인": last_success,
                "HTTP": result.get("http_status") or "-",
                "공식 원문": result.get("source_url", ""),
                "비고": result.get("error_message") or result.get("title") or "-",
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        column_config={
            "규제명": st.column_config.TextColumn("규제명", width="large"),
            "확인 상태": st.column_config.TextColumn("확인 상태", width="medium"),
            "공식 원문": st.column_config.LinkColumn("공식 원문", display_text="열기"),
            "비고": st.column_config.TextColumn("비고", width="large"),
        },
    )
    st.caption(
        "현재 자동 확인은 규제 DB에 등록된 공식 출처를 대상으로 합니다. "
        "완전히 새로운 규제 공고를 발견하려면 관할별 공식 API·RSS 탐지 연계가 추가로 필요합니다."
    )


def _render_timeline(regulation: dict) -> None:
    items = [
        ("규제 상태", regulation_status_badge(str(regulation.get("규제상태", "")))),
        ("발표일", escape(str(regulation.get("발표일") or "미확인"))),
        ("확정일", escape(str(regulation.get("확정일") or "미확인"))),
        (
            "주요 시행일",
            escape(str(regulation.get("주요시행일") or regulation.get("시행일") or "미확인")),
        ),
        ("유예·전환기간", escape(str(regulation.get("유예기간") or "해당 없음"))),
        ("당시 최근 확인일", escape(str(regulation.get("최근확인일") or "미확인"))),
    ]
    html = "".join(
        f'<div class="timeline-cell"><span>{escape(label)}</span><strong>{value}</strong></div>'
        for label, value in items
    )
    st.markdown(f'<div class="regulation-timeline">{html}</div>', unsafe_allow_html=True)


def _render_snapshot_detail(snapshot: dict, regulations: pd.DataFrame) -> None:
    metadata = snapshot["메타데이터"]
    result = snapshot["결과"]
    product = result.get("제품", {})
    matches = result.get("규제", [])

    st.markdown(
        f"""
        <div class="snapshot-banner">
            <div>
                <span>IMMUTABLE SNAPSHOT</span>
                <strong>{escape(str(product.get('제품명', '-')))}</strong>
            </div>
            <div class="snapshot-banner__meta">
                진단 {_format_datetime(metadata.get('diagnosed_at'))}<br>
                {escape(SOURCE_LABELS.get(str(metadata.get('source', '')), str(metadata.get('source', '-'))))}<br>
                규칙 {escape(str(metadata.get('ruleset_version', '-')))} · {escape(str(metadata.get('ruleset_fingerprint', '-')))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary_columns = st.columns(4)
    summary_values = [
        ("당시 Risk Score", f"{int(result.get('score', 0))}점"),
        ("당시 위험도", str(result.get("위험도", "-"))),
        ("관련 규제", f"{len(matches)}개"),
        ("규제 기준일", str(metadata.get("regulation_reviewed_at", "미확인"))),
    ]
    for column, (label, value) in zip(summary_columns, summary_values):
        with column:
            st.metric(label, value)

    with st.expander("저장된 제품 입력정보", expanded=False):
        profile_fields = [
            "제품형태",
            "제품용도",
            "피부접촉",
            "소재",
            "가공방법",
            "사용화학물질",
            "수출국",
            "Membrane",
            "Coating",
            "Lamination",
            "Finishing",
        ]
        profile_rows = [
            {"항목": field, "진단 당시 입력값": product.get(field, "-")}
            for field in profile_fields
            if product.get(field)
        ]
        st.dataframe(pd.DataFrame(profile_rows), width="stretch", hide_index=True)

    st.markdown("#### 진단 당시 문제 규제")
    if not matches:
        st.success("진단 당시 직접 매칭된 규제가 없습니다.")
    else:
        for match in matches:
            st.markdown(
                f"""
                <div class="reg-row">
                    <div><span class="reg-label">규제명</span><span class="reg-name">{escape(str(match.get('규제명', '-')))}</span></div>
                    <div><span class="reg-label">관할</span><strong>{escape(str(match.get('국가', '-')))}</strong></div>
                    <div><span class="reg-label">위험도</span>{risk_badge(str(match.get('위험도', '낮음')))}</div>
                    <div><span class="reg-label">당시 상태</span>{regulation_status_badge(str(match.get('규제상태', '')))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        selected_name = st.selectbox(
            "당시 규제 상세보기",
            [str(match.get("규제명", "-")) for match in matches],
            key=f"history_regulation_{metadata['record_id']}",
        )
        selected = next(match for match in matches if str(match.get("규제명")) == selected_name)
        st.markdown(
            f"""
            <div class="callout">
                <strong>{escape(selected_name)}</strong><br>
                <span style="color:#52606D;">{escape(str(selected.get('기준', '-')))}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_timeline(selected)

        reason_col, action_col = st.columns(2, gap="large")
        with reason_col:
            with st.container(border=True):
                st.markdown("**당시 매칭 근거**")
                for reason in selected.get("매칭근거", []):
                    st.markdown(f"- {escape(str(reason))}")
        with action_col:
            with st.container(border=True):
                st.markdown("**당시 대응 목표**")
                st.write(selected.get("대응요약") or selected.get("대응방안") or "추가 확인 필요")

        with st.expander("당시 실행 순서·필요자료", expanded=False):
            st.markdown("**즉시 실행 순서**")
            for index, action in enumerate(
                _pipe_items(selected.get("즉시조치") or selected.get("대응방안")),
                start=1,
            ):
                st.markdown(f"{index}. {escape(action)}")
            st.markdown("**필요자료**")
            for item in _pipe_items(selected.get("필요자료상세") or selected.get("필요자료")):
                st.markdown(f"- {escape(item)}")
            source_url = str(selected.get("공식출처", "")).strip()
            if source_url.startswith(("https://", "http://")):
                st.link_button("당시 저장된 공식 출처 열기", source_url, width="stretch")

    st.markdown("#### 현재 규제 DB와 비교")
    current_result = diagnose_product(product, regulations)
    old_names = {str(item.get("규제명", "")) for item in matches}
    current_names = {str(item.get("규제명", "")) for item in current_result.get("규제", [])}
    added = sorted(current_names - old_names)
    removed = sorted(old_names - current_names)
    score_change = int(current_result.get("score", 0)) - int(result.get("score", 0))

    comparison_columns = st.columns(3)
    comparison_columns[0].metric(
        "현재 승인 DB 기준 점수",
        f"{current_result.get('score', 0)}점",
        f"{score_change:+d}점",
    )
    comparison_columns[1].metric("새로 매칭된 규제", f"{len(added)}개")
    comparison_columns[2].metric("더 이상 매칭되지 않음", f"{len(removed)}개")
    if added:
        st.info("현재 기준 새로 매칭: " + ", ".join(added))
    if removed:
        st.warning("현재 기준 매칭 해제: " + ", ".join(removed))

    current_problem_rows = []
    for current_match in current_result.get("규제", []):
        current_problem_rows.append(
            {
                "현재 문제 규제": current_match.get("규제명", "-"),
                "관할": current_match.get("국가", "-"),
                "상태": current_match.get("규제상태", "미확인"),
                "위험도": current_match.get("위험도", "낮음"),
                "시행일": current_match.get("주요시행일") or current_match.get("시행일") or "미확인",
                "최근 확인일": current_match.get("최근확인일", "미확인"),
                "현재 매칭 근거": " / ".join(str(reason) for reason in current_match.get("매칭근거", [])),
            }
        )
    if current_problem_rows:
        st.markdown("**현재 문제 규제 전체**")
        st.dataframe(
            pd.DataFrame(current_problem_rows),
            width="stretch",
            hide_index=True,
            column_config={
                "현재 문제 규제": st.column_config.TextColumn("현재 문제 규제", width="large"),
                "현재 매칭 근거": st.column_config.TextColumn("현재 매칭 근거", width="large"),
            },
        )
    else:
        st.success("현재 규제 DB 기준으로 직접 매칭된 규제가 없습니다.")

    _render_source_monitor(
        str(metadata["record_id"]),
        _source_regulations(matches, current_result.get("규제", [])),
    )

    comparison = _regulation_comparison(matches, regulations)
    if not comparison.empty:
        st.dataframe(
            comparison,
            width="stretch",
            hide_index=True,
            column_config={
                "변경 여부": st.column_config.TextColumn("변경 여부", width="small"),
                "바뀐 항목": st.column_config.TextColumn("바뀐 항목", width="large"),
            },
        )

    st.caption("현재 재계산 결과는 미리보기입니다. 아래 버튼을 눌러야 새로운 진단 기록으로 보존됩니다.")
    if st.button(
        "현재 규제 DB로 재진단하고 새 기록 만들기",
        type="primary",
        width="stretch",
        key=f"reassess_{metadata['record_id']}",
    ):
        new_record_id = save_diagnosis_snapshot(
            current_result,
            source="reassessment",
            parent_record_id=str(metadata["record_id"]),
        )
        current_result["history_id"] = new_record_id
        st.session_state["current_result"] = current_result
        st.session_state.pop("history_save_error", None)
        st.rerun()


_ensure_session_result_is_saved()
regulations = load_regulations()

try:
    _ensure_example_history(load_products(), regulations)
    history = list_diagnosis_history()
except Exception as error:
    history = pd.DataFrame()
    st.error(f"제품 데이터베이스를 열지 못했습니다: {error}")

if st.session_state.get("history_save_error"):
    st.warning("현재 세션의 진단 결과를 영구 이력에 저장하지 못했습니다. 저장 위치 권한을 확인해 주세요.")

if history.empty:
    metric_values = [("누적 진단 기록", 0), ("등록 제품", 0), ("고위험 제품", 0), ("규제 DB 최근 확인", "-")]
else:
    latest_by_product = history.drop_duplicates(subset=["product_name"], keep="first")
    metric_values = [
        ("누적 진단 기록", len(history)),
        ("등록 제품", latest_by_product["product_name"].nunique()),
        ("고위험 제품", int((latest_by_product["risk_level"] == "높음").sum())),
        ("규제 DB 최근 확인", max(history["regulation_reviewed_at"].astype(str))),
    ]

metric_columns = st.columns(4)
for column, (label, value) in zip(metric_columns, metric_values):
    with column:
        st.metric(label, f"{value}개" if isinstance(value, int) else value)

history_tab, portfolio_tab, backup_tab = st.tabs(["진단 기록", "현재 포트폴리오", "보관·백업"])

with history_tab:
    if history.empty:
        st.info("아직 저장된 진단 기록이 없습니다. 제품 규제 진단을 실행하면 이곳에 시점별 스냅샷이 쌓입니다.")
        if st.button("첫 제품 진단하기", type="primary"):
            st.switch_page("pages/1_Product_Input.py")
    else:
        history_view = history.copy()
        history_view["진단일시"] = history_view["diagnosed_at"].map(_format_datetime)
        history_view["기록 유형"] = history_view["source"].map(SOURCE_LABELS).fillna(history_view["source"])
        history_view = history_view.rename(
            columns={
                "record_id": "기록 ID",
                "product_name": "제품명",
                "destinations": "판매·수출국",
                "risk_score": "Risk Score",
                "risk_level": "위험도",
                "regulation_count": "관련 규제 수",
                "regulation_reviewed_at": "규제 기준일",
                "ruleset_version": "규칙 버전",
            }
        )
        st.caption("행을 선택하면 진단 당시 규제와 현재 DB의 차이를 아래에서 확인할 수 있습니다.")
        table_event = st.dataframe(
            history_view,
            width="stretch",
            height=min(430, 54 + len(history_view) * 36),
            hide_index=True,
            column_order=[
                "진단일시",
                "기록 유형",
                "제품명",
                "판매·수출국",
                "Risk Score",
                "위험도",
                "관련 규제 수",
                "규제 기준일",
                "규칙 버전",
            ],
            column_config={
                "Risk Score": st.column_config.ProgressColumn(
                    "Risk Score", min_value=0, max_value=100, format="%d"
                ),
                "관련 규제 수": st.column_config.NumberColumn("관련 규제 수", format="%d개"),
            },
            key="diagnosis_history_table",
            on_select="rerun",
            selection_mode="single-row",
        )
        selected_rows = list(table_event.selection.rows)
        selected_position = selected_rows[0] if selected_rows else 0
        selected_record_id = str(history_view.iloc[selected_position]["기록 ID"])
        selected_snapshot = get_diagnosis_snapshot(selected_record_id)
        if selected_snapshot:
            st.divider()
            _render_snapshot_detail(selected_snapshot, regulations)

with portfolio_tab:
    if history.empty:
        st.info("진단 기록이 쌓이면 제품별 최신 Risk Score와 영향 규제 분포가 표시됩니다.")
    else:
        latest = history.drop_duplicates(subset=["product_name"], keep="first").copy()
        latest = latest.rename(
            columns={
                "product_name": "제품명",
                "risk_score": "Risk Score",
                "risk_level": "위험도",
                "regulation_count": "관련 규제 수",
                "diagnosed_at": "최근 진단일",
            }
        )
        latest["최근 진단일"] = latest["최근 진단일"].map(_format_datetime)

        chart_col1, chart_col2 = st.columns([1.35, 1])
        color_map = {"높음": "#D92D20", "보통": "#F79009", "낮음": "#12B76A"}
        with chart_col1:
            st.markdown("#### 제품별 최신 Risk Score")
            chart_frame = latest.sort_values("Risk Score", ascending=True)
            product_chart = px.bar(
                chart_frame,
                x="Risk Score",
                y="제품명",
                color="위험도",
                orientation="h",
                color_discrete_map=color_map,
                text="Risk Score",
            )
            product_chart.update_layout(
                height=max(320, len(chart_frame) * 48),
                margin=dict(l=10, r=15, t=10, b=20),
                xaxis=dict(range=[0, 105], title=None, gridcolor="#E8EDF2"),
                yaxis_title=None,
                legend_title=None,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Arial", color="#243B53"),
            )
            product_chart.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(product_chart, width="stretch", config={"displayModeBar": False})

        with chart_col2:
            st.markdown("#### 최신 위험도 분포")
            distribution = latest.groupby("위험도", as_index=False).size().rename(columns={"size": "제품 수"})
            donut = px.pie(
                distribution,
                names="위험도",
                values="제품 수",
                hole=0.62,
                color="위험도",
                color_discrete_map=color_map,
            )
            donut.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Arial", color="#243B53"),
            )
            donut.update_traces(textinfo="percent+label", sort=False)
            st.plotly_chart(donut, width="stretch", config={"displayModeBar": False})

        impact: dict[str, set[str]] = {}
        for _, latest_row in latest.iterrows():
            snapshot = get_diagnosis_snapshot(str(latest_row["record_id"]))
            if not snapshot:
                continue
            product_name = str(latest_row["제품명"])
            for regulation in snapshot["결과"].get("규제", []):
                impact.setdefault(str(regulation.get("규제명", "-")), set()).add(product_name)
        impact_frame = pd.DataFrame(
            [{"규제명": name, "영향 제품 수": len(products)} for name, products in impact.items()]
        )
        st.markdown("#### 최신 진단 기준 규제별 영향 제품 수")
        if impact_frame.empty:
            st.info("현재 매칭된 규제가 없습니다.")
        else:
            impact_chart = px.bar(
                impact_frame.sort_values("영향 제품 수", ascending=True),
                x="영향 제품 수",
                y="규제명",
                orientation="h",
                text="영향 제품 수",
                color_discrete_sequence=["#1428A0"],
            )
            impact_chart.update_layout(
                height=max(320, len(impact_frame) * 46),
                margin=dict(l=10, r=20, t=10, b=20),
                xaxis=dict(dtick=1, title=None, gridcolor="#E8EDF2"),
                yaxis_title=None,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Arial", color="#243B53"),
            )
            impact_chart.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(impact_chart, width="stretch", config={"displayModeBar": False})

with backup_tab:
    st.markdown("#### 장기 보관 정책")
    st.markdown(
        "진단 기록은 기존 행을 수정하지 않고 새 행으로만 추가됩니다. 규제 DB가 갱신돼도 과거 스냅샷의 점수, 매칭 근거와 대응방안은 그대로 유지됩니다."
    )
    st.code(str(history_db_path()), language=None)
    st.download_button(
        "전체 진단 이력 JSON 백업",
        data=export_history_json(),
        file_name=f"texreg_diagnosis_history_{pd.Timestamp.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        width="stretch",
        disabled=history.empty,
    )
    st.warning(
        "현재 프로토타입은 로컬 SQLite에 저장합니다. 같은 PC에서는 장기 보관되지만, "
        "Streamlit Community Cloud는 재시작·재배포 시 로컬 파일이 유지되지 않을 수 있습니다. "
        "실제 1년 이상 운영하려면 Supabase·PostgreSQL 같은 외부 영구 DB 연결이 필요합니다."
    )

render_footer()
