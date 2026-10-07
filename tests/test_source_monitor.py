"""공식 규제 출처 확인의 보안·지문·이력 동작을 검증한다."""

import tempfile
import unittest
from pathlib import Path

from utils.source_monitor import (
    SourceMonitorError,
    check_regulation_sources,
    fetch_official_source,
    latest_source_statuses,
    list_source_check_history,
    normalize_source_content,
    validate_official_url,
)


REGULATION = {
    "국가": "EU",
    "규제명": "PFAS Restriction",
    "공식출처": "https://eur-lex.europa.eu/eli/reg/2024/2462/oj/eng",
}


def _fetch_result(content_hash: str) -> dict:
    return {
        "not_modified": False,
        "http_status": 200,
        "final_url": REGULATION["공식출처"],
        "etag": f'"{content_hash}"',
        "last_modified": "Wed, 07 Oct 2026 00:00:00 GMT",
        "content_type": "text/html; charset=utf-8",
        "content_length": 120,
        "raw_sha256": f"raw-{content_hash}",
        "normalized_sha256": content_hash,
        "title": "Official regulation",
    }


class _FakeResponse:
    status = 200

    def __init__(self, body: bytes):
        self.body = body
        self.headers = {
            "Content-Type": "text/html; charset=utf-8",
            "ETag": '"test-etag"',
            "Last-Modified": "Wed, 07 Oct 2026 00:00:00 GMT",
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def getcode(self):
        return 200

    def geturl(self):
        return REGULATION["공식출처"]

    def read(self, size: int):
        return self.body[:size]


class SourceMonitorTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._temp_dir.name) / "monitor.db"

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_only_https_allowlisted_official_urls_are_accepted(self) -> None:
        self.assertEqual(
            validate_official_url(REGULATION["공식출처"]),
            REGULATION["공식출처"],
        )
        for url in [
            "http://eur-lex.europa.eu/eli/reg/2024/2462",
            "https://127.0.0.1/internal",
            "https://example.com/not-official",
        ]:
            with self.subTest(url=url), self.assertRaises(SourceMonitorError):
                validate_official_url(url)

    def test_html_normalization_ignores_scripts_and_whitespace(self) -> None:
        first, title = normalize_source_content(
            b"<html><title>Rule</title><script>token=1</script><main>Limit 25 ppb</main></html>",
            "text/html; charset=utf-8",
        )
        second, _ = normalize_source_content(
            b"<html><title>Rule</title><script>token=999</script><main> Limit   25 ppb </main></html>",
            "text/html; charset=utf-8",
        )
        changed, _ = normalize_source_content(
            b"<html><title>Rule</title><main>Limit 10 ppb</main></html>",
            "text/html; charset=utf-8",
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(title, "Rule")

    def test_fetch_builds_content_fingerprints_without_real_network(self) -> None:
        body = b"<html><title>Official</title><main>Legal text</main></html>"

        def opener(request, timeout):
            self.assertEqual(
                request.full_url,
                "https://publications.europa.eu/resource/celex/32024R2462",
            )
            self.assertEqual(request.headers["Accept"], "application/rdf+xml")
            self.assertGreater(timeout, 0)
            return _FakeResponse(body)

        result = fetch_official_source(REGULATION["공식출처"], opener=opener)
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["title"], "Official")
        self.assertEqual(len(result["normalized_sha256"]), 64)

    def test_baseline_cache_change_and_error_are_append_only(self) -> None:
        responses = iter([_fetch_result("hash-a"), _fetch_result("hash-a"), _fetch_result("hash-b")])
        calls = []

        def fetcher(url, *, etag="", last_modified=""):
            calls.append((url, etag, last_modified))
            return next(responses)

        first = check_regulation_sources(
            [REGULATION], db_path=self.db_path, fetcher=fetcher
        )[0]
        self.assertEqual(first["state"], "baseline")

        cached = check_regulation_sources(
            [REGULATION], db_path=self.db_path, fetcher=fetcher
        )[0]
        self.assertTrue(cached["cached"])
        self.assertEqual(len(calls), 1)

        unchanged = check_regulation_sources(
            [REGULATION], db_path=self.db_path, fetcher=fetcher, force=True
        )[0]
        changed = check_regulation_sources(
            [REGULATION], db_path=self.db_path, fetcher=fetcher, force=True
        )[0]
        self.assertEqual(unchanged["state"], "unchanged")
        self.assertEqual(changed["state"], "changed")
        self.assertEqual(len(list_source_check_history(self.db_path)), 3)

        def failing_fetcher(url, *, etag="", last_modified=""):
            raise SourceMonitorError("timeout", "timeout")

        failed = check_regulation_sources(
            [REGULATION], db_path=self.db_path, fetcher=failing_fetcher, force=True
        )[0]
        self.assertEqual(failed["state"], "error")
        self.assertTrue(failed["last_successful_at"])
        self.assertEqual(len(list_source_check_history(self.db_path)), 4)

        latest = latest_source_statuses([REGULATION], self.db_path)[0]
        self.assertEqual(latest["state"], "error")
        self.assertTrue(latest["last_successful_at"])


if __name__ == "__main__":
    unittest.main()
