"""제품 데이터베이스 화면 전용 포털형 UI 구성 요소."""

from __future__ import annotations

from html import escape

import streamlit as st


def inject_archive_styles() -> None:
    """제품 이력·규제 비교 화면에 필요한 전용 스타일을 적용한다."""
    st.markdown(
        """
        <style>
        .archive-steps {
            background: #FFFFFF; border: 1px solid #DFE5EE; border-radius: 18px;
            box-shadow: 0 9px 26px rgba(17,28,66,.04); display: grid;
            grid-template-columns: repeat(3,minmax(0,1fr)); margin: 4px 0 20px;
            overflow: hidden;
        }
        .archive-step {
            align-items: center; display: grid; gap: 12px;
            grid-template-columns: 40px minmax(0,1fr) 16px; min-height: 86px;
            padding: 14px 18px;
        }
        .archive-step:not(:last-child) { border-right: 1px solid #E6EAF0; }
        .archive-step__number {
            align-items: center; background: #F0F3F7; border-radius: 50%; color: #8590A3;
            display: inline-flex; font-size: .72rem; font-weight: 900; height: 38px;
            justify-content: center; width: 38px;
        }
        .archive-step strong { color: #475467; display: block; font-size: .92rem; }
        .archive-step small {
            color: #8A93A3; display: block; font-size: .7rem; line-height: 1.45;
            margin-top: 2px;
        }
        .archive-step__arrow { color: #C7CED9; font-size: 1.15rem; }
        .archive-step--active { background: #F4F6FB; }
        .archive-step--active .archive-step__number { background: #243A8F; color: #FFFFFF; }
        .archive-step--active strong { color: #101828; }
        .archive-step--complete .archive-step__number { background: #EAF7F2; color: #087453; }
        .archive-step--complete strong { color: #426257; }
        .archive-notice {
            align-items: center; background: #FFFDF7; border: 1px solid #E9D7A8;
            border-left: 5px solid #C79B39; border-radius: 17px; display: grid; gap: 14px;
            grid-template-columns: 44px minmax(0,1fr) auto; margin: 0 0 20px;
            padding: 17px 18px;
        }
        .archive-notice__icon {
            align-items: center; background: #FFF4D8; border-radius: 12px; color: #956C17;
            display: inline-flex; font-size: 1.05rem; font-weight: 900; height: 42px;
            justify-content: center; width: 42px;
        }
        .archive-notice strong { color: #3F3522; display: block; font-size: 1.02rem; }
        .archive-notice p { color: #73644A; font-size: .8rem; line-height: 1.55; margin: 3px 0 0; }
        .archive-notice__badge {
            background: #FFF3D6; border-radius: 999px; color: #7C5A16; font-size: .68rem;
            font-weight: 850; padding: 7px 10px; white-space: nowrap;
        }
        .archive-metrics {
            display: grid; gap: 14px; grid-template-columns: repeat(4,minmax(0,1fr));
            margin: 0 0 21px;
        }
        .archive-metric {
            background: #FFFFFF; border: 1px solid #E4E8EF; border-radius: 18px;
            box-shadow: 0 10px 28px rgba(17,28,66,.045); min-height: 116px;
            padding: 17px 19px; position: relative;
        }
        .archive-metric__icon {
            align-items: center; background: #EEF2FA; border-radius: 10px; color: #3F5FB7;
            display: inline-flex; font-size: .82rem; font-weight: 900; height: 34px;
            justify-content: center; position: absolute; right: 16px; top: 16px; width: 34px;
        }
        .archive-metric:nth-child(3) .archive-metric__icon { background: #FCF0F2; color: #C7354A; }
        .archive-metric > span:not(.archive-metric__icon) {
            color: #718096; display: block; font-size: .76rem;
        }
        .archive-metric strong {
            color: #101828; display: block; font-size: 1.85rem; letter-spacing: -.04em;
            line-height: 1.05; margin-top: 13px;
        }
        .archive-metric small { color: #98A2B3; display: block; font-size: .66rem; margin-top: 7px; }
        .archive-table-heading { margin: 2px 0 12px; }
        .archive-table-heading strong { color: #101828; display: block; font-size: 1.12rem; }
        .archive-table-heading span { color: #718096; display: block; font-size: .75rem; margin-top: 3px; }
        .archive-guide {
            background: #FFFFFF; border: 1px solid #E0E6EF; border-radius: 18px;
            box-shadow: 0 10px 28px rgba(17,28,66,.045); margin-bottom: 12px;
            padding: 18px;
        }
        .archive-guide h4 { color: #101828; font-size: 1rem; margin: 0 0 4px; }
        .archive-guide > p { color: #718096; font-size: .72rem; margin: 0 0 16px; }
        .archive-guide__item {
            display: grid; gap: 9px; grid-template-columns: 27px minmax(0,1fr);
            margin-top: 13px;
        }
        .archive-guide__number {
            align-items: center; background: #EEF2FA; border-radius: 50%; color: #243A8F;
            display: inline-flex; font-size: .68rem; font-weight: 900; height: 25px;
            justify-content: center; width: 25px;
        }
        .archive-guide__item strong { color: #344054; display: block; font-size: .78rem; }
        .archive-guide__item small { color: #7D899B; display: block; font-size: .68rem; line-height: 1.5; margin-top: 2px; }
        .archive-reading-note {
            background: #F1F4FA; border: 1px solid #D8DFEC; border-radius: 16px;
            color: #445273; font-size: .72rem; line-height: 1.65; padding: 14px 15px;
        }
        .archive-reading-note strong { display: block; margin-bottom: 4px; }
        .archive-storage {
            background: linear-gradient(135deg,#F9FAFD,#F1F4FA); border: 1px solid #DDE3EF;
            border-radius: 18px; display: grid; gap: 12px;
            grid-template-columns: repeat(3,minmax(0,1fr)); margin: 14px 0 16px;
            padding: 16px;
        }
        .archive-storage__item { background: rgba(255,255,255,.82); border-radius: 13px; padding: 13px; }
        .archive-storage__item span { color: #7B8797; display: block; font-size: .67rem; }
        .archive-storage__item strong { color: #34405C; display: block; font-size: .82rem; margin-top: 4px; }
        .archive-privacy-note { color: #7B8797; font-size: .7rem; margin: -4px 2px 13px; }
        @media (max-width: 950px) {
            .archive-metrics { grid-template-columns: 1fr 1fr; }
            .archive-steps { grid-template-columns: 1fr; }
            .archive-step { grid-template-columns: 38px minmax(0,1fr); }
            .archive-step:not(:last-child) { border-bottom: 1px solid #E6EAF0; border-right: 0; }
            .archive-step__arrow { display: none; }
        }
        @media (max-width: 700px) {
            .archive-metrics, .archive-storage { grid-template-columns: 1fr; }
            .archive-notice { align-items: start; grid-template-columns: 42px minmax(0,1fr); }
            .archive-notice__badge { grid-column: 2; justify-self: start; }
            .archive-metric { min-height: 104px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_archive_steps(active_step: int) -> None:
    """저장 기록을 최신 규제 기준으로 재검토하는 업무 흐름을 표시한다."""
    steps = [
        (1, "진단 기록 선택", "시점별 제품 스냅샷 확인"),
        (2, "당시 규제 확인", "저장 결과와 현재 DB 비교"),
        (3, "대응 업데이트", "최신 기준 재진단·새 기록"),
    ]
    items: list[str] = []
    for index, title, description in steps:
        state_class = ""
        number = f"{index:02d}"
        current = ""
        if index == active_step:
            state_class = " archive-step--active"
            current = ' aria-current="step"'
        elif index < active_step:
            state_class = " archive-step--complete"
            number = "✓"
        arrow = '<span class="archive-step__arrow">›</span>' if index < len(steps) else ""
        items.append(
            f'<div class="archive-step{state_class}"{current}>'
            f'<span class="archive-step__number">{number}</span>'
            f'<span><strong>{escape(title)}</strong><small>{escape(description)}</small></span>'
            f"{arrow}</div>"
        )
    st.markdown(
        f'<div class="archive-steps" aria-label="제품 데이터베이스 활용 과정">'
        f'{"".join(items)}</div>',
        unsafe_allow_html=True,
    )


def render_archive_notice(has_records: bool) -> None:
    """과거 스냅샷과 현재 규제 DB의 관계를 안내한다."""
    if has_records:
        title = "저장된 진단과 현재 규제를 함께 확인하세요"
        description = (
            "기록 행을 선택하면 당시 Risk Score·매칭 근거는 그대로 보존되고, "
            "현재 승인된 규제 DB 기준 결과를 별도로 비교합니다."
        )
    else:
        title = "첫 제품 진단을 시작해 주세요"
        description = "진단을 완료하면 제품·규제 스냅샷이 이 화면에 시점별로 누적됩니다."
    st.markdown(
        f"""
        <div class="archive-notice" role="note">
            <span class="archive-notice__icon" aria-hidden="true">i</span>
            <div><strong>{escape(title)}</strong><p>{escape(description)}</p></div>
            <span class="archive-notice__badge">승인 DB 기준</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_archive_metrics(metrics: list[tuple[str, str, str]]) -> None:
    """제품 데이터베이스 핵심 수치를 카드로 표시한다."""
    icons = ("≡", "□", "!", "✓")
    cards = "".join(
        f'<div class="archive-metric"><span class="archive-metric__icon" aria-hidden="true">'
        f'{icons[index % len(icons)]}</span><span>{escape(label)}</span>'
        f'<strong>{escape(value)}</strong><small>{escape(note)}</small></div>'
        for index, (label, value, note) in enumerate(metrics)
    )
    st.markdown(f'<div class="archive-metrics">{cards}</div>', unsafe_allow_html=True)


def render_archive_guide() -> None:
    """기록표 옆에 현재 화면의 사용 순서를 표시한다."""
    items = [
        ("1", "진단 기록 선택", "제품명과 진단일을 보고 한 행을 선택합니다."),
        ("2", "당시 규제 확인", "저장된 점수·규제·대응자료를 검토합니다."),
        ("3", "현재 기준 재진단", "최신 승인 DB 결과를 새 기록으로 남깁니다."),
    ]
    detail = "".join(
        f'<div class="archive-guide__item"><span class="archive-guide__number">{number}</span>'
        f'<div><strong>{escape(title)}</strong><small>{escape(description)}</small></div></div>'
        for number, title, description in items
    )
    st.markdown(
        f'<div class="archive-guide"><h4>지금 해야 할 일</h4>'
        f'<p>기록 확인부터 최신 재진단까지 순서대로 진행하세요.</p>{detail}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="archive-reading-note">
            <strong>결과를 읽는 방법</strong>
            ‘당시 결과’는 수정되지 않는 기록입니다. ‘현재 승인 DB 기준’은 선택한 제품 정보를
            최신 규제 데이터로 다시 계산한 비교값입니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_storage_summary() -> None:
    """실제 서버 경로 대신 사용자에게 필요한 저장 정책만 표시한다."""
    st.markdown(
        """
        <div class="archive-storage" aria-label="진단 기록 저장 정책">
            <div class="archive-storage__item"><span>저장 형식</span><strong>SQLite 스냅샷</strong></div>
            <div class="archive-storage__item"><span>변경 정책</span><strong>기존 기록 불변 · 새 행 추가</strong></div>
            <div class="archive-storage__item"><span>백업 형식</span><strong>JSON 다운로드</strong></div>
        </div>
        <div class="archive-privacy-note">서버 내부 파일 경로는 보안과 가독성을 위해 화면에 표시하지 않습니다.</div>
        """,
        unsafe_allow_html=True,
    )
