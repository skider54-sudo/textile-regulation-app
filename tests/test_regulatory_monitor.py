"""정기 규제 모니터링의 기준선·변경·신규 후보 동작을 검증한다."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

from texreg_core.regulatory_monitor import (
    load_monitor_sources,
    load_registered_sources,
    run_regulatory_monitor,
)
from texreg_core.source_monitor import SourceMonitorError, validate_official_url


REGISTERED = {
    "source_id": "reg-test",
    "국가": "EU",
    "출처명": "Test REACH",
    "source_type": "registered_document",
    "url": "https://echa.europa.eu/regulations/reach/understanding-reach",
    "keywords": "",
}
DISCOVERY = {
    "source_id": "us-test",
    "국가": "미국",
    "출처명": "Federal Register API",
    "source_type": "json_feed",
    "url": "https://www.federalregister.gov/api/v1/documents.json",
    "keywords": "textile|PFAS",
}


def _payload(body: str, url: str, content_type: str) -> dict:
    return {
        "body": body.encode("utf-8"),
        "content_type": content_type,
        "final_url": url,
        "http_status": 200,
    }


def _feed(*titles: str) -> str:
    results = [
        {
            "title": title,
            "html_url": f"https://www.federalregister.gov/documents/2026/10/{index:02d}/test",
            "publication_date": f"2026-10-{index:02d}",
            "abstract": "Textile PFAS regulatory notice",
        }
        for index, title in enumerate(titles, start=1)
    ]
    return json.dumps({"results": results})


class RegulatoryMonitorTest(unittest.TestCase):
    def test_config_covers_twelve_markets_and_official_urls(self) -> None:
        sources = load_monitor_sources()
        self.assertEqual(len({source["국가"] for source in sources}), 12)
        self.assertGreaterEqual(len(load_registered_sources()), 38)
        for source in sources:
            url = source["url"]
            if source["source_type"] == "korea_law_api":
                url = f"{url}&OC=test"
            self.assertTrue(validate_official_url(url).startswith("https://"))

    def test_second_run_detects_registered_change_and_new_candidate(self) -> None:
        sources = [REGISTERED, DISCOVERY]

        def baseline_fetcher(source):
            if source["source_type"] == "registered_document":
                return _payload("<main>Limit 25 ppb</main>", source["url"], "text/html")
            return _payload(_feed("Textile PFAS notice A"), source["url"], "application/json")

        baseline, events = run_regulatory_monitor(
            sources=sources,
            fetcher=baseline_fetcher,
            checked_at="2026-10-12T00:00:00+00:00",
        )
        self.assertEqual(events, [])
        self.assertTrue(all(row["status"] == "baseline" for row in baseline["sources"]))

        def changed_fetcher(source):
            if source["source_type"] == "registered_document":
                return _payload("<main>Limit 10 ppb</main>", source["url"], "text/html")
            return _payload(
                _feed("Textile PFAS notice A", "New textile chemical rule"),
                source["url"],
                "application/json",
            )

        changed, events = run_regulatory_monitor(
            sources=sources,
            previous_state=baseline,
            previous_events=events,
            fetcher=changed_fetcher,
            checked_at="2026-10-12T06:00:00+00:00",
        )
        self.assertTrue(all(row["status"] == "changed" for row in changed["sources"]))
        self.assertEqual(
            {event["event_type"] for event in events},
            {"registered_source_changed", "new_official_candidate"},
        )
        self.assertTrue(all(event["review_status"] == "pending" for event in events))

    def test_source_failure_is_visible_and_preserves_last_good_state(self) -> None:
        baseline, _ = run_regulatory_monitor(
            sources=[REGISTERED],
            fetcher=lambda source: _payload("<main>original</main>", source["url"], "text/html"),
            checked_at="2026-10-12T00:00:00+00:00",
        )

        def fail(_source):
            raise SourceMonitorError("timeout", "공식 출처 응답 시간을 초과했습니다.")

        failed, events = run_regulatory_monitor(
            sources=[REGISTERED],
            previous_state=baseline,
            fetcher=fail,
            checked_at="2026-10-12T06:00:00+00:00",
        )
        row = failed["sources"][0]
        self.assertEqual(row["status"], "error")
        self.assertEqual(row["fingerprint"], baseline["sources"][0]["fingerprint"])
        self.assertEqual(events, [])

    def test_monitor_page_loads_before_first_scheduled_run(self) -> None:
        app = AppTest.from_file(
            Path(__file__).resolve().parents[1] / "app.py"
        )
        app.run(timeout=30)
        app.switch_page("pages/4_Regulation_Monitor.py").run(timeout=30)
        self.assertEqual(list(app.exception), [])
        visible = "\n".join(str(node.value) for node in app.markdown)
        self.assertIn("OFFICIAL SOURCE WATCH", visible)
        self.assertIn("자동 감지는 법률 판단이 아닙니다", visible)


if __name__ == "__main__":
    unittest.main()
