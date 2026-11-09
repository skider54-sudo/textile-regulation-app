"""TexReg Insight 로고 자산을 모든 Streamlit 화면에서 공유한다."""

from __future__ import annotations

from base64 import b64encode
from functools import lru_cache
from pathlib import Path

from PIL import Image


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
BRAND_LOGO_PATH = ASSET_DIR / "texreg_logo.png"
BRAND_MARK_PATH = ASSET_DIR / "texreg_mark.png"


@lru_cache(maxsize=2)
def _png_data_uri(path: Path) -> str:
    """HTML 안에서 안전하게 사용할 수 있는 PNG data URI를 반환한다."""
    encoded = b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def brand_logo_data_uri() -> str:
    """가로형 TexReg Insight 로고의 data URI를 반환한다."""
    return _png_data_uri(BRAND_LOGO_PATH)


def brand_mark_data_uri() -> str:
    """정사각형 TexReg Insight 심볼의 data URI를 반환한다."""
    return _png_data_uri(BRAND_MARK_PATH)


@lru_cache(maxsize=1)
def brand_mark_image() -> Image.Image:
    """브라우저 탭 아이콘에 사용할 독립된 PIL 이미지를 반환한다."""
    with Image.open(BRAND_MARK_PATH) as image:
        return image.copy()
