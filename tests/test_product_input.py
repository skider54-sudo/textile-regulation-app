"""제품 입력 화면의 복수·기타 소재 입력 동작을 검증한다."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class ProductInputTest(unittest.TestCase):
    def test_mixed_and_custom_materials_are_saved_together(self) -> None:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.switch_page("pages/1_Product_Input.py").run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertFalse(app.text_input[1].disabled)
        self.assertIn("대한민국", app.multiselect[1].options)

        app.text_input[0].input("Test Leggings")
        app.multiselect[0].set_value(["Nylon", "Spandex"])
        app.text_input[1].input("Modal")
        app.multiselect[1].set_value(["미국", "일본"])
        app.button[0].click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            app.session_state["current_result"]["제품"]["소재"],
            "Nylon, Spandex, Modal",
        )

        app.switch_page("pages/2_Diagnosis_Result.py").run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        markdown_values = [element.value for element in app.markdown]
        self.assertTrue(
            any("실행형 상세 대응방안" in value for value in markdown_values)
        )
        self.assertTrue(any("즉시 실행 순서" in value for value in markdown_values))
        self.assertTrue(any("완료 기준" in value for value in markdown_values))


if __name__ == "__main__":
    unittest.main()
