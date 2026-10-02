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


def _validate_columns(frame: pd.DataFrame, required: list[str], file_name: str) -> None:
    """필수 컬럼 누락 시 사용자가 수정 위치를 바로 알 수 있게 오류를 낸다."""
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{file_name}에 필수 컬럼이 없습니다: {', '.join(missing)}")


@st.cache_data(show_spinner=False)
def load_products() -> pd.DataFrame:
    """예시 제품 DB를 UTF-8 CSV에서 불러온다."""
    frame = pd.read_csv(DATA_DIR / "products.csv", encoding="utf-8-sig").fillna("")
    _validate_columns(frame, PRODUCT_COLUMNS, "products.csv")
    return frame[PRODUCT_COLUMNS].copy()


@st.cache_data(show_spinner=False)
def load_regulations() -> pd.DataFrame:
    """규제 DB와 실행형 대응방안 DB를 국가·규제명 기준으로 결합한다."""
    frame = pd.read_csv(DATA_DIR / "regulations.csv", encoding="utf-8-sig").fillna("")
    _validate_columns(frame, REGULATION_COLUMNS, "regulations.csv")
    actions = pd.read_csv(
        DATA_DIR / "regulation_actions.csv",
        encoding="utf-8-sig",
    ).fillna("")
    _validate_columns(actions, ACTION_COLUMNS, "regulation_actions.csv")
    return frame.merge(
        actions[ACTION_COLUMNS],
        on=["국가", "규제명"],
        how="left",
        validate="one_to_one",
    ).fillna("")


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
