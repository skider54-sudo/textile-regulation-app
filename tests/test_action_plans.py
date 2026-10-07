"""규제별 실행형 대응방안 DB의 완전성과 형식을 검증한다."""

import unittest
from pathlib import Path

import pandas as pd

from texreg_core.source_monitor import validate_official_url


ROOT = Path(__file__).resolve().parents[1]


class ActionPlanDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.regulations = pd.read_csv(ROOT / "data" / "regulations.csv").fillna("")
        cls.actions = pd.read_csv(ROOT / "data" / "regulation_actions.csv").fillna("")
        cls.timeline = pd.read_csv(ROOT / "data" / "regulation_timeline.csv").fillna("")

    def test_every_regulation_has_one_action_plan(self) -> None:
        regulation_keys = set(
            self.regulations[["국가", "규제명"]].itertuples(index=False, name=None)
        )
        action_keys = set(
            self.actions[["국가", "규제명"]].itertuples(index=False, name=None)
        )
        self.assertEqual(len(action_keys), len(self.actions))
        self.assertEqual(regulation_keys, action_keys)

    def test_every_plan_has_three_steps_and_official_source(self) -> None:
        required = [
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
        for _, row in self.actions.iterrows():
            with self.subTest(regulation=row["규제명"]):
                self.assertTrue(all(str(row[column]).strip() for column in required))
                self.assertGreaterEqual(len(str(row["즉시조치"]).split("|")), 3)
            self.assertTrue(str(row["공식출처"]).startswith("https://"))

    def test_every_official_source_uses_an_allowlisted_domain(self) -> None:
        for url in self.actions["공식출처"]:
            self.assertEqual(validate_official_url(str(url)), str(url))

    def test_every_regulation_has_status_and_review_date(self) -> None:
        regulation_keys = set(
            self.regulations[["국가", "규제명"]].itertuples(index=False, name=None)
        )
        timeline_keys = set(
            self.timeline[["국가", "규제명"]].itertuples(index=False, name=None)
        )
        self.assertEqual(len(timeline_keys), len(self.timeline))
        self.assertEqual(regulation_keys, timeline_keys)
        self.assertTrue(
            self.timeline["규제상태"].isin(["시행 중", "시행 예정", "제안·검토"]).all()
        )
        self.assertTrue(self.timeline["최근확인일"].str.match(r"^\d{4}-\d{2}-\d{2}$").all())


if __name__ == "__main__":
    unittest.main()
