"""Streamlit Cloud의 배포 직후 혼합 모듈 상태에 대한 회귀 테스트."""

from pathlib import Path
import sys
from types import ModuleType
import unittest

import streamlit as st
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

        # 이전 배포의 setup_page는 sidebar_state 키워드를 받지 않았으며,
        # 이제 삭제된 모니터링 페이지를 사이드바에서 계속 참조했다.
        def stale_render_sidebar() -> None:
            st.page_link(
                "pages/4_Regulation_Monitor.py",
                label="최신 규제 모니터링",
            )

        legacy_ui.render_sidebar = stale_render_sidebar

        def legacy_setup_page(title: str) -> None:
            st.set_page_config(page_title=title)
            legacy_ui.render_sidebar()

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
