"""CSV 데이터 로딩과 세션 등록 제품 병합 기능."""

from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

PRODUCT_COLUMNS = ["제품명", "소재", "가공방법", "사용화학물질", "제품용도", "수출국"]
REGULATION_COLUMNS = [
    "국가",
    "규제명",
    "대상물질",
    "적용제품",
    "기준",
    "시행일",
    "확인사항",
    "필요자료",
    "대응방안",
]
ACTION_COLUMNS = [
    "국가",
    "규제명",
    "대응요약",
    "즉시조치",
    "권장시험",
    "필요자료상세",
    "담당부서",
    "권장일정",
    "완료기준",
    "실무주의사항",
    "공식출처",
]
TIMELINE_COLUMNS = [
    "국가",
    "규제명",
    "규제상태",
    "발표일",
    "확정일",
    "주요시행일",
    "유예기간",
    "최근확인일",
]


def _validate_columns(frame: pd.DataFrame, required: list[str], file_name: str) -> None:
    """필수 컬럼 누락 시 사용자가 수정 위치를 바로 알 수 있게 오류를 낸다."""
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{file_name}에 필수 컬럼이 없습니다: {', '.join(missing)}")


def _file_signature(paths: Iterable[Path]) -> tuple[tuple[str, int, int], ...]:
    """CSV가 교체되면 Streamlit 캐시도 자동으로 갱신되게 한다."""
    return tuple(
        (str(path), path.stat().st_mtime_ns, path.stat().st_size)
        for path in paths
    )


@st.cache_data(show_spinner=False)
def _load_products_cached(signature: tuple[tuple[str, int, int], ...]) -> pd.DataFrame:
    """예시 제품 DB를 UTF-8 CSV에서 불러온다."""
    del signature  # 함수 인자가 캐시 키로 사용되며, 본문에서는 파일을 직접 읽는다.
    frame = pd.read_csv(DATA_DIR / "products.csv", encoding="utf-8-sig").fillna("")
    _validate_columns(frame, PRODUCT_COLUMNS, "products.csv")
    return frame[PRODUCT_COLUMNS].copy()


def load_products() -> pd.DataFrame:
    """예시 제품 DB를 파일 변경 감지 캐시로 불러온다."""
    product_path = DATA_DIR / "products.csv"
    return _load_products_cached(_file_signature([product_path]))


@st.cache_data(show_spinner=False)
def _load_regulations_cached(signature: tuple[tuple[str, int, int], ...]) -> pd.DataFrame:
    """규제 DB와 실행형 대응방안 DB를 국가·규제명 기준으로 결합한다."""
    del signature  # 규제 관련 CSV 중 하나라도 바뀌면 새 캐시 키가 된다.
    frame = pd.read_csv(DATA_DIR / "regulations.csv", encoding="utf-8-sig").fillna("")
    _validate_columns(frame, REGULATION_COLUMNS, "regulations.csv")
    actions = pd.read_csv(
        DATA_DIR / "regulation_actions.csv",
        encoding="utf-8-sig",
    ).fillna("")
    _validate_columns(actions, ACTION_COLUMNS, "regulation_actions.csv")
    timeline = pd.read_csv(
        DATA_DIR / "regulation_timeline.csv",
        encoding="utf-8-sig",
    ).fillna("")
    _validate_columns(timeline, TIMELINE_COLUMNS, "regulation_timeline.csv")
    merged = frame.merge(
        actions[ACTION_COLUMNS],
        on=["국가", "규제명"],
        how="left",
        validate="one_to_one",
    )
    return merged.merge(
        timeline[TIMELINE_COLUMNS],
        on=["국가", "규제명"],
        how="left",
        validate="one_to_one",
    ).fillna("")


def load_regulations() -> pd.DataFrame:
    """규제·대응·일정 CSV 변경을 감지해 항상 현재 DB를 반환한다."""
    paths = [
        DATA_DIR / "regulations.csv",
        DATA_DIR / "regulation_actions.csv",
        DATA_DIR / "regulation_timeline.csv",
    ]
    return _load_regulations_cached(_file_signature(paths))


def merge_session_products(
    base_products: pd.DataFrame, session_products: Iterable[dict] | None
) -> pd.DataFrame:
    """CSV 제품과 현재 세션에서 진단한 제품을 하나의 제품 목록으로 합친다."""
    rows = list(session_products or [])
    if not rows:
        return base_products.copy()

    session_frame = pd.DataFrame(rows)
    for column in PRODUCT_COLUMNS:
        if column not in session_frame.columns:
            session_frame[column] = ""

    combined = pd.concat(
        [base_products[PRODUCT_COLUMNS], session_frame[PRODUCT_COLUMNS]],
        ignore_index=True,
    )
    # 같은 이름으로 다시 진단한 경우 가장 최근 입력을 사용한다.
    return combined.drop_duplicates(subset=["제품명"], keep="last").reset_index(drop=True)
