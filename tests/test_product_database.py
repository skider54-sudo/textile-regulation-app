"""제품 데이터베이스의 이력 조회 화면을 검증한다."""

import os
import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from texreg_core.data_loader import load_regulations
from texreg_core.history import save_diagnosis_snapshot
from texreg_core.matching import diagnose_product
from texreg_core.source_monitor import check_regulation_sources


ROOT = Path(__file__).resolve().parents[1]


class ProductDatabaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        os.environ["TEXREG_HISTORY_DB"] = str(Path(self._temp_dir.name) / "history.db")
        os.environ["TEXREG_LIVE_CHECKS"] = "0"
        product = {
            "제품명": "Archive Jacket",
            "소재": "Nylon 100%",
            "가공방법": "염색, 발수, 코팅",
            "사용화학물질": "PFAS 계열 발수제",
            "제품용도": "아웃도어 의류",
            "수출국": "EU",
        }
        result = diagnose_product(product, load_regulations())
        save_diagnosis_snapshot(
            result,
            diagnosed_at="2027-10-07T11:00:00+09:00",
        )
        pfas_regulation = next(
            regulation for regulation in result["규제"] if regulation["규제명"] == "PFAS Restriction"
        )

        def source_result(content_hash):
            return {
                "not_modified": False,
                "http_status": 200,
                "final_url": pfas_regulation["공식출처"],
                "etag": "",
                "last_modified": "",
                "content_type": "text/html",
                "content_length": 100,
                "raw_sha256": f"raw-{content_hash}",
                "normalized_sha256": content_hash,
                "title": "Official PFAS source",
            }

        responses = iter([source_result("old"), source_result("new")])

        def fetcher(url, *, etag="", last_modified=""):
            return next(responses)

        check_regulation_sources([pfas_regulation], fetcher=fetcher, force=True)
        check_regulation_sources([pfas_regulation], fetcher=fetcher, force=True)

    def tearDown(self) -> None:
        os.environ.pop("TEXREG_HISTORY_DB", None)
        os.environ.pop("TEXREG_LIVE_CHECKS", None)
        self._temp_dir.cleanup()

    def test_saved_record_and_historical_regulations_are_visible(self) -> None:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.switch_page("pages/3_Risk_Dashboard.py").run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        markdown_values = [element.value for element in app.markdown]
        self.assertTrue(any("제품 데이터베이스" in element.value for element in app.title))
        self.assertTrue(any("진단 당시 문제 규제" in value for value in markdown_values))
        self.assertTrue(any("현재 규제 DB와 비교" in value for value in markdown_values))
        self.assertTrue(any("공식 출처 최신성 확인" in value for value in markdown_values))
        self.assertTrue(any("공식 페이지 본문 변경" in warning.value for warning in app.warning))
        self.assertTrue(
            any(button.label == "현재 규제 DB로 재진단하고 새 기록 만들기" for button in app.button)
        )


if __name__ == "__main__":
    unittest.main()
