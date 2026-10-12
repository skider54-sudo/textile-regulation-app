"""포털 홈, 진행 단계와 결과 상단 경고 UI를 검증한다."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class PortalWorkflowTest(unittest.TestCase):
    def _open_result(self, score: int, level: str, product_name: str = "Boundary Jacket") -> AppTest:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
        app.session_state["current_result"] = {
            "제품": {
                "제품명": product_name,
                "제품형태": "의류 완제품",
                "제품용도": "일상 의류",
                "피부접촉": "직접·장시간 접촉",
                "수출국": "EU",
            },
            "score": score,
            "위험도": level,
            "규제": [],
        }
        return app.switch_page("pages/2_Diagnosis_Result.py").run(timeout=30)

    def test_home_has_portal_header_and_clickable_process_cards(self) -> None:
        app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        markdown = "\n".join(element.value for element in app.markdown)
        self.assertIn('class="portal-header"', markdown)
        self.assertIn('class="portal-hero"', markdown)

        labels = [button.label for button in app.button]
        self.assertTrue(any("01  제품 정보 입력" in label for label in labels))
        self.assertTrue(any("02  규제 진단" in label for label in labels))
        self.assertTrue(any("03  대응 가이드" in label for label in labels))

        next(button for button in app.button if button.key == "home_step_input").click()
        app.run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any(element.label == "제품명 *" for element in app.text_input))

    def test_result_title_uses_product_name_and_shows_active_step(self) -> None:
        app = self._open_result(39, "낮음", "AQUA-S")

        self.assertEqual(len(app.exception), 0)
        self.assertIn("AQUA-S 진단 결과", [title.value for title in app.title])
        markdown = "\n".join(element.value for element in app.markdown)
        self.assertIn('class="workflow-step workflow-step--active"', markdown)
        self.assertNotIn('class="risk-alert ', markdown)

    def test_risk_alert_starts_at_medium_and_distinguishes_high(self) -> None:
        medium = self._open_result(40, "보통")
        medium_markdown = "\n".join(element.value for element in medium.markdown)
        self.assertEqual(len(medium.exception), 0)
        self.assertIn('class="risk-alert risk-alert--medium"', medium_markdown)
        self.assertIn("40 / 100", medium_markdown)

        high = self._open_result(70, "높음")
        high_markdown = "\n".join(element.value for element in high.markdown)
        self.assertEqual(len(high.exception), 0)
        self.assertIn('class="risk-alert risk-alert--high"', high_markdown)
        self.assertIn("70 / 100", high_markdown)

    def test_product_name_is_escaped_inside_risk_alert(self) -> None:
        app = self._open_result(40, "보통", '<script>alert("x")</script> & Jacket')
        alert = next(
            element.value
            for element in app.markdown
            if 'class="risk-alert risk-alert--medium"' in element.value
        )

        self.assertNotIn("<script>", alert)
        self.assertIn("&lt;script&gt;", alert)
        self.assertIn("&amp; Jacket", alert)


if __name__ == "__main__":
    unittest.main()
