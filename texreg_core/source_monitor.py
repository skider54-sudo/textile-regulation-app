"""공식 규제 출처의 접속 상태와 본문 변경을 안전하게 감지한다.

페이지 변경은 법적 의무 변경이 아니므로, 본 모듈은 규제 DB나 Risk Score를
자동으로 수정하지 않고 '검토 필요' 신호만 저장한다.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import socket
import sqlite3
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from texreg_core.history import history_db_path


CHECKER_VERSION = "1.0"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_TTL_HOURS = 6
ALLOWED_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "application/xml",
    "application/rdf+xml",
    "text/xml",
    "application/json",
    "text/json",
    "text/plain",
    "application/pdf",
}
OFFICIAL_DOMAIN_SUFFIXES = {
    "echa.europa.eu",
    "eur-lex.europa.eu",
    "publications.europa.eu",
    "epa.gov",
    "p65warnings.ca.gov",
    "leginfo.legislature.ca.gov",
    "ftc.gov",
    "cpsc.gov",
    "hse.gov.uk",
    "gov.uk",
    "legislation.gov.uk",
    "meti.go.jp",
    "caa.go.jp",
    "laws.e-gov.go.jp",
    "openstd.samr.gov.cn",
    "std.samr.gov.cn",
    "samr.gov.cn",
    "moit.gov.vn",
    "chinhphu.vn",
    "consumeraffairs.gov.in",
    "dgft.gov.in",
    "bis.gov.in",
    "moea.gov.tw",
    "bsmi.gov.tw",
    "competition-bureau.canada.ca",
    "canada.ca",
    "laws-lois.justice.gc.ca",
    "productsafety.gov.au",
    "legislation.gov.au",
    "dcceew.gov.au",
    "legislation.govt.nz",
    "comcom.govt.nz",
    "law.go.kr",
    "open.law.go.kr",
}
SUCCESS_STATES = {"baseline", "unchanged", "changed"}
SOURCE_CHECK_COLUMNS = [
    "check_id",
    "checked_at",
    "country",
    "regulation_name",
    "source_url",
    "final_url",
    "state",
    "http_status",
    "etag",
    "last_modified",
    "content_type",
    "content_length",
    "raw_sha256",
    "normalized_sha256",
    "title",
    "previous_check_id",
    "error_code",
    "error_message",
    "checker_version",
]


class SourceMonitorError(RuntimeError):
    """출처 확인 실패 유형을 UI에 안전하게 전달한다."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class _VisibleTextParser(HTMLParser):
    """동적 스크립트·네비게이션을 제외한 실제 본문 텍스트를 추출한다."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in self.SKIP_TAGS:
            self._skip_depth += 1
        if lowered == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if lowered == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if not self._skip_depth:
            self.parts.append(data)


@contextmanager
def _connect(db_path: str | Path | None = None):
    path = Path(db_path) if db_path else history_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_source_monitor(db_path: str | Path | None = None) -> None:
    """기존 진단 스냅샷을 건드리지 않고 출처 확인 이력 테이블을 추가한다."""
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS regulation_source_checks (
                check_id TEXT PRIMARY KEY,
                checked_at TEXT NOT NULL,
                country TEXT NOT NULL,
                regulation_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                final_url TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL,
                http_status INTEGER NOT NULL DEFAULT 0,
                etag TEXT NOT NULL DEFAULT '',
                last_modified TEXT NOT NULL DEFAULT '',
                content_type TEXT NOT NULL DEFAULT '',
                content_length INTEGER NOT NULL DEFAULT 0,
                raw_sha256 TEXT NOT NULL DEFAULT '',
                normalized_sha256 TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                previous_check_id TEXT NOT NULL DEFAULT '',
                error_code TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                checker_version TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_source_checks_regulation
                ON regulation_source_checks(country, regulation_name, checked_at DESC);
            CREATE INDEX IF NOT EXISTS idx_source_checks_url
                ON regulation_source_checks(source_url, checked_at DESC);
            """
        )


def _host_is_allowed(hostname: str) -> bool:
    host = hostname.rstrip(".").lower()
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in OFFICIAL_DOMAIN_SUFFIXES)


def validate_official_url(url: str, *, resolve_dns: bool = False) -> str:
    """HTTPS 공식 도메인만 허용하고 로컬·사설 주소 접속을 차단한다."""
    parsed = urlparse(str(url).strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise SourceMonitorError("untrusted_url", "HTTPS 공식 출처 URL이 아닙니다.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise SourceMonitorError("untrusted_url", "인증정보 또는 비표준 포트가 포함된 URL은 확인하지 않습니다.")
    if not _host_is_allowed(parsed.hostname):
        raise SourceMonitorError("untrusted_domain", "등록된 공식 도메인이 아닙니다.")
    if resolve_dns:
        try:
            addresses = {
                info[4][0]
                for info in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
            }
        except OSError as error:
            raise SourceMonitorError("dns_error", f"공식 출처 주소를 찾지 못했습니다: {error}") from error
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise SourceMonitorError("unsafe_address", "공식 출처가 공개 인터넷 주소로 확인되지 않습니다.")
    return parsed.geturl()


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        parsed = urlparse(newurl)
        if parsed.scheme == "http" and parsed.hostname == "publications.europa.eu":
            newurl = urlunparse(parsed._replace(scheme="https"))
        validate_official_url(newurl, resolve_dns=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _charset_from_content_type(content_type: str) -> str:
    match = re.search(r"charset\s*=\s*['\"]?([^;'\"\s]+)", content_type, flags=re.I)
    return match.group(1) if match else "utf-8"


def _eurlex_celex_id(url: str) -> str:
    """EUR-Lex ELI·CELEX URL에서 CELLAR 조회용 CELEX 식별자를 추출한다."""
    parsed = urlparse(url)
    query_values = parse_qs(parsed.query)
    for value in query_values.get("uri", []):
        if value.upper().startswith("CELEX:"):
            return value.split(":", 1)[1].strip().upper()
    match = re.search(r"/eli/reg/(\d{4})/(\d+)", parsed.path, flags=re.I)
    if match:
        year, number = match.groups()
        return f"3{year}R{int(number):04d}"
    return ""


def _official_fetch_target(url: str) -> tuple[str, str]:
    """HTML 차단 출처는 같은 기관의 공식 구조화 API로 전환한다."""
    if urlparse(url).hostname == "eur-lex.europa.eu":
        celex_id = _eurlex_celex_id(url)
        if celex_id:
            return (
                f"https://publications.europa.eu/resource/celex/{celex_id}",
                "application/rdf+xml",
            )
    return (
        url,
        "text/html,application/xhtml+xml,application/xml,application/json,application/pdf,text/plain;q=0.9,*/*;q=0.1",
    )


def normalize_source_content(body: bytes, content_type: str) -> tuple[bytes, str]:
    """형식·공백·스크립트 차이로 인한 오탐을 줄인 지문용 본문을 만든다."""
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type == "application/pdf":
        return body, ""

    try:
        text = body.decode(_charset_from_content_type(content_type), errors="replace")
    except LookupError:
        text = body.decode("utf-8", errors="replace")

    if media_type in {"application/json", "text/json"}:
        try:
            canonical = json.dumps(
                json.loads(text), ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            return canonical.encode("utf-8"), ""
        except json.JSONDecodeError:
            pass

    parser = _VisibleTextParser()
    try:
        parser.feed(text)
        visible = " ".join(parser.parts)
        title = " ".join(parser.title_parts)
    except Exception:
        visible, title = text, ""
    normalized = re.sub(r"\s+", " ", visible).strip()
    normalized_title = re.sub(r"\s+", " ", title).strip()[:300]
    return normalized.encode("utf-8"), normalized_title


def fetch_official_source(
    url: str,
    *,
    etag: str = "",
    last_modified: str = "",
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """조건부 GET으로 공식 출처를 읽고 원문·정규화 지문을 반환한다."""
    safe_url = validate_official_url(url, resolve_dns=opener is None)
    fetch_url, accept_header = _official_fetch_target(safe_url)
    validate_official_url(fetch_url, resolve_dns=opener is None)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36 "
            "TexReg-Insight/2.5"
        ),
        "Accept": accept_header,
        "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    request = Request(fetch_url, headers=headers, method="GET")
    open_call = opener or build_opener(_SafeRedirectHandler()).open

    try:
        response_context = open_call(request, timeout=timeout)
        with response_context as response:
            status = int(getattr(response, "status", None) or response.getcode() or 200)
            final_url = str(response.geturl())
            validate_official_url(final_url, resolve_dns=False)
            content_type_header = str(response.headers.get("Content-Type", "")).strip()
            media_type = content_type_header.split(";", 1)[0].strip().lower()
            if media_type not in ALLOWED_CONTENT_TYPES:
                raise SourceMonitorError(
                    "unsupported_content_type",
                    f"확인하지 않는 응답 형식입니다: {media_type or '미확인'}",
                )
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise SourceMonitorError("response_too_large", "공식 출처 응답이 5MB를 초과했습니다.")
            normalized, title = normalize_source_content(body, content_type_header)
            return {
                "not_modified": False,
                "http_status": status,
                "final_url": final_url,
                "etag": str(response.headers.get("ETag", "")),
                "last_modified": str(response.headers.get("Last-Modified", "")),
                "content_type": content_type_header,
                "content_length": len(body),
                "raw_sha256": hashlib.sha256(body).hexdigest(),
                "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
                "title": title,
            }
    except HTTPError as error:
        if error.code == 304:
            return {
                "not_modified": True,
                "http_status": 304,
                "final_url": str(error.geturl() or safe_url),
                "etag": str(error.headers.get("ETag", etag)) if error.headers else etag,
                "last_modified": (
                    str(error.headers.get("Last-Modified", last_modified))
                    if error.headers
                    else last_modified
                ),
                "content_type": "",
                "content_length": 0,
                "raw_sha256": "",
                "normalized_sha256": "",
                "title": "",
            }
        raise SourceMonitorError("http_error", f"공식 출처가 HTTP {error.code}을 반환했습니다.") from error
    except (TimeoutError, socket.timeout) as error:
        raise SourceMonitorError("timeout", "공식 출처 응답 시간을 초과했습니다.") from error
    except URLError as error:
        raise SourceMonitorError("network_error", f"공식 출처에 연결하지 못했습니다: {error.reason}") from error
    except OSError as error:
        raise SourceMonitorError("network_error", f"공식 출처 확인 중 오류가 발생했습니다: {error}") from error


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def get_latest_source_check(
    country: str,
    regulation_name: str,
    db_path: str | Path | None = None,
    *,
    successful_only: bool = False,
) -> dict[str, Any] | None:
    initialize_source_monitor(db_path)
    success_filter = "AND state IN ('baseline', 'unchanged', 'changed')" if successful_only else ""
    with _connect(db_path) as connection:
        row = connection.execute(
            f"""
            SELECT {', '.join(SOURCE_CHECK_COLUMNS)}
            FROM regulation_source_checks
            WHERE country = ? AND regulation_name = ? {success_filter}
            ORDER BY checked_at DESC, rowid DESC
            LIMIT 1
            """,
            (country, regulation_name),
        ).fetchone()
    return _row_to_dict(row)


def _record_source_check(check: dict[str, Any], db_path: str | Path | None = None) -> None:
    initialize_source_monitor(db_path)
    with _connect(db_path) as connection:
        connection.execute(
            f"""
            INSERT INTO regulation_source_checks ({', '.join(SOURCE_CHECK_COLUMNS)})
            VALUES ({', '.join('?' for _ in SOURCE_CHECK_COLUMNS)})
            """,
            tuple(check.get(column, "") for column in SOURCE_CHECK_COLUMNS),
        )


def list_source_check_history(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """감사·테스트용으로 모든 공식 출처 확인 이력을 반환한다."""
    initialize_source_monitor(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT {', '.join(SOURCE_CHECK_COLUMNS)} FROM regulation_source_checks ORDER BY checked_at, rowid"
        ).fetchall()
    return [dict(row) for row in rows]


def _is_recent(check: dict[str, Any] | None, ttl_hours: float) -> bool:
    if not check:
        return False
    try:
        checked_at = datetime.fromisoformat(str(check["checked_at"]))
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - checked_at.astimezone(timezone.utc) < timedelta(hours=ttl_hours)
    except (KeyError, TypeError, ValueError):
        return False


def _cached_status(
    latest: dict[str, Any], previous_success: dict[str, Any] | None
) -> dict[str, Any]:
    status = dict(latest)
    status["cached"] = True
    status["last_successful_at"] = (
        previous_success.get("checked_at", "") if previous_success else ""
    )
    return status


def _perform_check(
    regulation: dict[str, Any],
    previous_success: dict[str, Any] | None,
    fetcher: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    country = str(regulation.get("국가", ""))
    regulation_name = str(regulation.get("규제명", ""))
    source_url = str(regulation.get("공식출처", "")).strip()
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    base = {
        "check_id": str(uuid4()),
        "checked_at": checked_at,
        "country": country,
        "regulation_name": regulation_name,
        "source_url": source_url,
        "final_url": "",
        "state": "error",
        "http_status": 0,
        "etag": "",
        "last_modified": "",
        "content_type": "",
        "content_length": 0,
        "raw_sha256": "",
        "normalized_sha256": "",
        "title": "",
        "previous_check_id": previous_success.get("check_id", "") if previous_success else "",
        "error_code": "",
        "error_message": "",
        "checker_version": CHECKER_VERSION,
    }
    if not source_url:
        base.update(error_code="missing_source", error_message="공식 출처 URL이 등록되지 않았습니다.")
        return base

    try:
        fetched = fetcher(
            source_url,
            etag=str(previous_success.get("etag", "")) if previous_success else "",
            last_modified=str(previous_success.get("last_modified", "")) if previous_success else "",
        )
        if fetched.get("not_modified") and previous_success:
            fetched["raw_sha256"] = previous_success.get("raw_sha256", "")
            fetched["normalized_sha256"] = previous_success.get("normalized_sha256", "")
            fetched["content_type"] = fetched.get("content_type") or previous_success.get("content_type", "")
            fetched["title"] = fetched.get("title") or previous_success.get("title", "")
            fetched["content_length"] = previous_success.get("content_length", 0)
        current_hash = str(fetched.get("normalized_sha256", ""))
        previous_hash = str(previous_success.get("normalized_sha256", "")) if previous_success else ""
        if previous_hash:
            state = "unchanged" if current_hash == previous_hash else "changed"
        else:
            state = "baseline"
        base.update(fetched)
        base.update(state=state, error_code="", error_message="")
    except SourceMonitorError as error:
        base.update(error_code=error.code, error_message=str(error))
    except Exception as error:  # 한 출처 실패가 전체 확인을 막지 않게 격리한다.
        base.update(error_code="unexpected_error", error_message=str(error))
    base["cached"] = False
    base["last_successful_at"] = previous_success.get("checked_at", "") if previous_success else ""
    return base


def check_regulation_sources(
    regulations: Iterable[dict[str, Any]],
    *,
    db_path: str | Path | None = None,
    force: bool = False,
    ttl_hours: float = DEFAULT_TTL_HOURS,
    fetcher: Callable[..., dict[str, Any]] = fetch_official_source,
) -> list[dict[str, Any]]:
    """규제별 공식 출처를 병렬 확인하고 결과를 append-only 이력으로 저장한다."""
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for regulation in regulations:
        key = (str(regulation.get("국가", "")), str(regulation.get("규제명", "")))
        if key != ("", ""):
            unique[key] = regulation

    results: dict[tuple[str, str], dict[str, Any]] = {}
    pending: list[tuple[tuple[str, str], dict[str, Any], dict[str, Any] | None]] = []
    for key, regulation in unique.items():
        latest = get_latest_source_check(*key, db_path=db_path)
        previous_success = get_latest_source_check(*key, db_path=db_path, successful_only=True)
        if (
            not force
            and latest is not None
            and latest.get("state") != "error"
            and _is_recent(latest, ttl_hours)
        ):
            results[key] = _cached_status(latest, previous_success)
        else:
            pending.append((key, regulation, previous_success))

    if pending:
        with ThreadPoolExecutor(max_workers=min(4, len(pending))) as executor:
            futures = {
                executor.submit(_perform_check, regulation, previous_success, fetcher): key
                for key, regulation, previous_success in pending
            }
            for future in as_completed(futures):
                key = futures[future]
                check = future.result()
                persisted = {column: check.get(column, "") for column in SOURCE_CHECK_COLUMNS}
                _record_source_check(persisted, db_path)
                results[key] = check

    return [results[key] for key in unique]


def latest_source_statuses(
    regulations: Iterable[dict[str, Any]], db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """네트워크 호출 없이 규제별 마지막 확인 상태를 읽는다."""
    results = []
    seen: set[tuple[str, str]] = set()
    for regulation in regulations:
        key = (str(regulation.get("국가", "")), str(regulation.get("규제명", "")))
        if key in seen:
            continue
        seen.add(key)
        latest = get_latest_source_check(*key, db_path=db_path)
        if not latest:
            continue
        success = get_latest_source_check(*key, db_path=db_path, successful_only=True)
        latest["cached"] = True
        latest["last_successful_at"] = success.get("checked_at", "") if success else ""
        results.append(latest)
    return results
