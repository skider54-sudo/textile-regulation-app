"""SQLite 진단 스냅샷의 저장·조회·불변성을 검증한다."""

import json
import tempfile
import unittest
from pathlib import Path

from utils.history import (
    export_history_json,
    get_diagnosis_snapshot,
    initialize_history_db,
    list_diagnosis_history,
    save_diagnosis_snapshot,
)


def _sample_result(product_name: str = "발수 자켓", score: int = 74) -> dict:
    return {
        "제품": {
            "제품명": product_name,
            "소재": "Nylon 90%, Spandex 10%",
            "가공방법": "염색, 발수",
            "사용화학물질": "PFAS 미확인",
            "제품용도": "아웃도어 의류",
            "수출국": "EU",
        },
        "score": score,
        "위험도": "높음",
        "규제": [
            {
                "국가": "EU",
                "규제명": "PFHxA Restriction",
                "위험도": "높음",
                "규제상태": "시행 예정",
                "기준": "일반 소비자용 의류 기준",
                "시행일": "2026-10-10",
                "최근확인일": "2026-10-01",
                "매칭근거": ["EU 수출", "발수 가공"],
                "대응요약": "불소계 발수제 성분 확인",
            }
        ],
    }


class DiagnosisHistoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "diagnosis_history.db"

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_initialize_is_idempotent_and_empty(self) -> None:
        initialize_history_db(self.db_path)
        initialize_history_db(self.db_path)
        self.assertTrue(list_diagnosis_history(self.db_path).empty)

    def test_korean_nested_snapshot_round_trip_is_immutable(self) -> None:
        original = _sample_result()
        record_id = save_diagnosis_snapshot(
            original,
            diagnosed_at="2026-10-07T10:30:00+09:00",
            db_path=self.db_path,
        )

        # 저장 후 메모리 객체가 바뀌어도 DB의 과거 스냅샷은 그대로여야 한다.
        original["score"] = 1
        original["규제"][0]["기준"] = "변경된 값"
        stored = get_diagnosis_snapshot(record_id, self.db_path)

        self.assertIsNotNone(stored)
        self.assertEqual(stored["결과"]["score"], 74)
        self.assertEqual(stored["결과"]["규제"][0]["기준"], "일반 소비자용 의류 기준")
        self.assertEqual(stored["메타데이터"]["regulation_reviewed_at"], "2026-10-01")

    def test_same_product_creates_separate_audit_records(self) -> None:
        first_id = save_diagnosis_snapshot(
            _sample_result(score=60),
            diagnosed_at="2026-01-01T09:00:00+09:00",
            db_path=self.db_path,
        )
        second_id = save_diagnosis_snapshot(
            _sample_result(score=82),
            source="reassessment",
            parent_record_id=first_id,
            diagnosed_at="2027-01-01T09:00:00+09:00",
            db_path=self.db_path,
        )

        history = list_diagnosis_history(self.db_path)
        self.assertEqual(len(history), 2)
        self.assertEqual(history.iloc[0]["record_id"], second_id)
        self.assertEqual(history.iloc[0]["parent_record_id"], first_id)
        self.assertEqual(history["product_name"].nunique(), 1)

    def test_example_record_id_can_be_seeded_idempotently(self) -> None:
        for _ in range(2):
            save_diagnosis_snapshot(
                _sample_result(),
                record_id="fixed-example-record",
                source="example",
                ignore_existing=True,
                db_path=self.db_path,
            )

        history = list_diagnosis_history(self.db_path)
        self.assertEqual(len(history), 1)
        self.assertEqual(history.iloc[0]["source"], "example")

    def test_json_export_contains_full_results(self) -> None:
        record_id = save_diagnosis_snapshot(_sample_result(), db_path=self.db_path)
        exported = json.loads(export_history_json(self.db_path))

        self.assertEqual(len(exported["records"]), 1)
        self.assertEqual(exported["source_checks"], [])
        self.assertEqual(exported["records"][0]["record_id"], record_id)
        self.assertEqual(exported["records"][0]["result"]["규제"][0]["규제명"], "PFHxA Restriction")


if __name__ == "__main__":
    unittest.main()
