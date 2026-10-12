"""Streamlit Cloud의 배포 직후 혼합 모듈 상태에 대한 회귀 테스트."""

from pathlib import Path
import sys
from types import ModuleType
import unittest

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


class CloudHotReloadCompatibilityTests(unittest.TestCase):
    def test_new_pages_work_with_legacy_ui_module_cached(self) -> None:
        """새 전용 UI가 예전 공용 UI와 함께 로드되어도 ImportError가 없어야 한다."""
        import texreg_core.ui as current_ui

        stable_names = {
            "page_heading",
            "regulation_status_badge",
            "render_footer",
            "render_layer_stack",
            "risk_badge",
            "stat_card",
        }
        legacy_ui = ModuleType("texreg_core.ui")
        for name in stable_names:
            setattr(legacy_ui, name, getattr(current_ui, name))

        # 이전 배포의 setup_page는 sidebar_state 키워드를 받지 않았다.
        def legacy_setup_page(title: str) -> None:
            current_ui.setup_page(title)

        legacy_ui.setup_page = legacy_setup_page
        original_ui = sys.modules["texreg_core.ui"]
        sys.modules["texreg_core.ui"] = legacy_ui
        try:
            app = AppTest.from_file(str(ROOT / "app.py"))
            app.run(timeout=30)
            self.assertEqual(
                len(app.exception),
                0,
                f"app.py: {[item.value for item in app.exception]}",
            )
            app.switch_page("pages/1_Product_Input.py").run(timeout=30)
            self.assertEqual(
                len(app.exception),
                0,
                f"Product Input: {[item.value for item in app.exception]}",
            )
            app.switch_page("pages/2_Diagnosis_Result.py").run(timeout=30)
            self.assertEqual(
                len(app.exception),
                0,
                f"Diagnosis Result: {[item.value for item in app.exception]}",
            )
        finally:
            sys.modules["texreg_core.ui"] = original_ui


if __name__ == "__main__":
    unittest.main()
