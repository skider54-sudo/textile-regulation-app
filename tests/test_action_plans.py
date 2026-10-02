"""규제별 실행형 대응방안 DB의 완전성과 형식을 검증한다."""

import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class ActionPlanDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.regulations = pd.read_csv(ROOT / "data" / "regulations.csv").fillna("")
        cls.actions = pd.read_csv(ROOT / "data" / "regulation_actions.csv").fillna("")

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


if __name__ == "__main__":
    unittest.main()
