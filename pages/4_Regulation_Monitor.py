"""국가별 공식 출처를 주기 확인하는 최신 규제 모니터링 화면."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from texreg_core.monitor_ui import (
    inject_monitor_styles,
    render_monitor_flow,
    render_monitor_hero,
    render_monitor_metrics,
    render_monitor_notice,
)
from texreg_core.regulatory_monitor import (
    load_monitor_snapshot,
    load_monitor_sources,
    load_registered_sources,
)
from texreg_core.ui import page_heading, render_footer, setup_page


setup_page("최신 규제 모니터링")
inject_monitor_styles()


EVENT_LABELS = {
    "registered_source_changed": "등록 규제 원문 변경",
    "new_official_candidate": "신규 공식 문서 후보",
}
SOURCE_TYPE_LABELS = {
    "registered_document": "등록 규제 원문",
    "json_feed": "공식 API",
    "korea_law_api": "공식 API",
    "atom_feed": "공식 Atom 피드",
    "html_index": "공식 공고 목록",
}
STATUS_LABELS = {
    "baseline": "기준 지문 생성",
    "unchanged": "변경 없음",
    "changed": "변경 감지",
    "error": "확인 실패",
}


def _format_datetime(value: object) -> str:
    if not value:
        return "-"
    try:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert("Asia/Seoul")
        return timestamp.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(value)[:16]


heading_col, action_col = st.columns([4.2, 1], vertical_alignment="center")
with heading_col:
    page_heading(
        "REGULATORY INTELLIGENCE",
        "최신 규제 모니터링",
        "공식 출처의 신규 공고와 등록 규제 원문 변경을 자동 수집해 검토 후보로 제공합니다.",
    )
with action_col:
    st.link_button(
        "모니터 즉시 실행",
        "https://github.com/skider54-sudo/textile-regulation-app/actions/workflows/regulatory-monitor.yml",
        width="stretch",
        help="GitHub Actions에서 Run workflow를 누르면 예약 시간 전에도 즉시 확인할 수 있습니다.",
    )

state, events = load_monitor_snapshot()
configured_sources = [*load_registered_sources(), *load_monitor_sources()]
source_rows = list(state.get("sources", []))
if not source_rows:
    source_rows = [
        {
            **source,
            "checked_at": "",
            "status": "waiting",
            "http_status": 0,
            "error_message": "첫 자동 확인 대기",
        }
        for source in configured_sources
    ]

generated_at = str(state.get("generated_at", ""))
pending_events = [event for event in events if event.get("review_status") == "pending"]
changed_sources = [row for row in source_rows if row.get("status") == "changed"]
error_sources = [row for row in source_rows if row.get("status") == "error"]

render_monitor_hero(_format_datetime(generated_at) if generated_at else "", bool(generated_at))
render_monitor_metrics(
    [
        ("공식 모니터링 출처", f"{len(source_rows)}개", "등록 규제 원문 + 국가별 공고"),
        ("검토 대기 후보", f"{len(pending_events)}개", "담당자 확인 전 자동 반영 금지"),
        ("변경 감지 출처", f"{len(changed_sources)}개", "직전 지문 또는 후보 목록과 비교"),
        ("확인 실패", f"{len(error_sources)}개", "실패를 변경 없음으로 처리하지 않음"),
    ]
)
render_monitor_notice()
render_monitor_flow()

review_tab, sources_tab, operation_tab = st.tabs(
    ["검토 대기", "공식 출처 상태", "운영·승인 안내"]
)

with review_tab:
    st.markdown("### 신규·변경 규제 검토함")
    st.caption("첫 실행은 기준 지문만 만들며, 두 번째 실행부터 새 후보와 변경을 기록합니다.")
    if not pending_events:
        st.success("현재 검토 대기 중인 신규·변경 후보가 없습니다.")
    else:
        countries = sorted({str(event.get("국가", "")) for event in pending_events if event.get("국가")})
        filter_col, type_col = st.columns(2)
        with filter_col:
            selected_country = st.selectbox("국가 필터", ["전체", *countries])
        with type_col:
            selected_type = st.selectbox("유형 필터", ["전체", "신규 공식 문서 후보", "등록 규제 원문 변경"])
        visible_events = []
        for event in pending_events:
            event_label = EVENT_LABELS.get(str(event.get("event_type", "")), "기타 변경")
            if selected_country != "전체" and event.get("국가") != selected_country:
                continue
            if selected_type != "전체" and event_label != selected_type:
                continue
            visible_events.append(
                {
                    "감지 시각": _format_datetime(event.get("detected_at")),
                    "국가": event.get("국가", "-"),
                    "유형": event_label,
                    "제목": event.get("title", "-"),
                    "발표일": event.get("published_at") or "-",
                    "공식 원문": event.get("url", ""),
                    "검토 상태": "검토 대기",
                }
            )
        st.dataframe(
            pd.DataFrame(visible_events),
            width="stretch",
            hide_index=True,
            column_config={
                "제목": st.column_config.TextColumn("제목", width="large"),
                "공식 원문": st.column_config.LinkColumn("공식 원문", display_text="열기"),
            },
        )
        st.download_button(
            "검토 후보 JSON 다운로드",
            data=json.dumps(pending_events, ensure_ascii=False, indent=2),
            file_name="regulatory_review_candidates.json",
            mime="application/json",
            width="stretch",
        )

with sources_tab:
    st.markdown("### 공식 출처 확인 현황")
    st.caption("예약 실행은 6시간 간격이며, 오류가 난 출처는 다음 실행 때 다시 확인합니다.")
    status_table = pd.DataFrame(
        [
            {
                "국가": row.get("국가", "-"),
                "출처명": row.get("출처명", "-"),
                "출처 유형": SOURCE_TYPE_LABELS.get(str(row.get("source_type", "")), row.get("source_type", "-")),
                "상태": STATUS_LABELS.get(str(row.get("status", "")), "실행 대기"),
                "확인 시각": _format_datetime(row.get("checked_at")),
                "HTTP": str(row.get("http_status") or "-"),
                "공식 출처": row.get("url", ""),
                "비고": row.get("error_message") or "-",
            }
            for row in source_rows
        ]
    )
    st.dataframe(
        status_table,
        width="stretch",
        hide_index=True,
        column_config={
            "출처명": st.column_config.TextColumn("출처명", width="large"),
            "공식 출처": st.column_config.LinkColumn("공식 출처", display_text="열기"),
            "비고": st.column_config.TextColumn("비고", width="large"),
        },
    )

with operation_tab:
    st.markdown("### 승인 DB 반영 절차")
    st.markdown(
        """
1. 검토 대기 후보의 공식 원문을 열어 법적 상태와 적용 범위를 확인합니다.
2. 발표일·확정일·시행일·유예기간 및 섬유제품 적용 예외를 검토합니다.
3. 승인된 내용만 `regulations.csv`, `regulation_actions.csv`, `regulation_timeline.csv`에 반영합니다.
4. 테스트를 통과한 규제 DB를 배포한 뒤 저장 제품을 현재 기준으로 재진단합니다.

자동 수집 결과만으로 적합·부적합을 확정하거나 Risk Score를 자동 변경하지 않습니다.
        """
    )
    st.info(
        "대한민국 국가법령정보 Open API는 GitHub 저장소의 KOREA_LAW_OC 비밀값이 설정되어야 합니다. "
        "키가 없더라도 나머지 공식 출처 모니터링은 계속 실행됩니다."
    )

render_footer()
