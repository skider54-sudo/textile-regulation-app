"""공식 공고와 등록 규제 원문을 주기적으로 확인하는 모니터링 엔진.

자동 수집 결과는 법률 판단이나 Risk Score를 직접 변경하지 않는다. 새 문서와
원문 변경을 검토 후보로 저장하고, 승인된 규제 DB는 별도 절차로 갱신한다.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

from texreg_core.source_monitor import (
    MAX_RESPONSE_BYTES,
    SourceMonitorError,
    normalize_source_content,
    validate_official_url,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MONITOR_SOURCES_PATH = DATA_DIR / "monitoring_sources.csv"
MONITOR_STATE_PATH = DATA_DIR / "regulatory_monitor_state.json"
MONITOR_EVENTS_PATH = DATA_DIR / "regulatory_monitor_events.json"
MONITOR_VERSION = "1.0"
DEFAULT_TIMEOUT_SECONDS = 12
MAX_DISCOVERY_ITEMS = 100


class _MonitorRedirectHandler(HTTPRedirectHandler):
    """리디렉션 이후에도 공식 HTTPS 도메인 제한을 유지한다."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        validate_official_url(newurl, resolve_dns=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _LinkParser(HTMLParser):
    """공식 공고 목록 페이지에서 링크 제목과 주소를 추출한다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href = ""
        self._parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = next((value or "" for name, value in attrs if name.lower() == "href"), "")
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            title = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
            if title:
                self.links.append((self._href, title))
            self._href = ""
            self._parts = []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def load_monitor_sources(path: str | Path | None = None) -> list[dict[str, str]]:
    """국가별 공식 공고·API·피드 설정을 읽는다."""
    source_path = Path(path) if path else MONITOR_SOURCES_PATH
    with source_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"source_id", "국가", "출처명", "source_type", "url", "keywords", "enabled"}
    if not rows or not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0] if rows else {}))
        raise ValueError(f"monitoring_sources.csv 필수 컬럼 누락: {', '.join(missing)}")
    return [row for row in rows if str(row.get("enabled", "")).strip().lower() in {"1", "true", "yes"}]


def load_registered_sources(path: str | Path | None = None) -> list[dict[str, str]]:
    """현재 승인 DB에 등록된 규제 원문을 모니터링 대상으로 변환한다."""
    actions_path = Path(path) if path else DATA_DIR / "regulation_actions.csv"
    with actions_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    sources: list[dict[str, str]] = []
    for row in rows:
        country = str(row.get("국가", "")).strip()
        name = str(row.get("규제명", "")).strip()
        url = str(row.get("공식출처", "")).strip()
        if not country or not name or not url:
            continue
        digest = sha256(f"{country}\0{name}".encode("utf-8")).hexdigest()[:16]
        sources.append(
            {
                "source_id": f"reg-{digest}",
                "국가": country,
                "출처명": name,
                "source_type": "registered_document",
                "url": url,
                "keywords": "",
                "enabled": "true",
                "규제명": name,
            }
        )
    return sources


def _with_korea_api_key(url: str) -> str:
    api_key = os.getenv("KOREA_LAW_OC", "").strip()
    if not api_key:
        raise SourceMonitorError(
            "configuration_required",
            "국가법령정보 Open API 인증키(KOREA_LAW_OC)가 필요합니다.",
        )
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["OC"] = api_key
    return urlunparse(parsed._replace(query=urlencode(query)))


def fetch_monitor_source(
    source: dict[str, str], *, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> dict[str, Any]:
    """공식 모니터링 출처를 제한된 크기로 안전하게 읽는다."""
    url = str(source.get("url", "")).strip()
    if source.get("source_type") == "korea_law_api":
        url = _with_korea_api_key(url)
    safe_url = validate_official_url(url, resolve_dns=True)
    request = Request(
        safe_url,
        headers={
            "User-Agent": "TexReg-Insight-Regulatory-Monitor/1.0",
            "Accept": "application/json,application/atom+xml,application/xml,text/html,text/plain;q=0.9,*/*;q=0.1",
            "Accept-Language": "ko,en;q=0.8",
        },
        method="GET",
    )
    try:
        with build_opener(_MonitorRedirectHandler()).open(request, timeout=timeout) as response:
            final_url = str(response.geturl())
            validate_official_url(final_url, resolve_dns=False)
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise SourceMonitorError("response_too_large", "공식 출처 응답이 5MB를 초과했습니다.")
            return {
                "body": body,
                "content_type": str(response.headers.get("Content-Type", "text/html")),
                "final_url": final_url,
                "http_status": int(getattr(response, "status", 200) or 200),
            }
    except HTTPError as error:
        raise SourceMonitorError("http_error", f"공식 출처가 HTTP {error.code}을 반환했습니다.") from error
    except URLError as error:
        raise SourceMonitorError("network_error", "공식 출처에 연결하지 못했습니다.") from error
    except TimeoutError as error:
        raise SourceMonitorError("timeout", "공식 출처 응답 시간을 초과했습니다.") from error


def _decode_body(body: bytes, content_type: str) -> str:
    charset_match = re.search(r"charset\s*=\s*([^;\s]+)", content_type, flags=re.I)
    charset = charset_match.group(1).strip("\"'") if charset_match else "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _keyword_match(item: dict[str, str], keywords: str) -> bool:
    terms = [term.strip().casefold() for term in str(keywords).split("|") if term.strip()]
    if not terms:
        return True
    haystack = " ".join(
        str(item.get(field, "")) for field in ("title", "summary", "url")
    ).casefold()
    return any(term in haystack for term in terms)


def _item_id(item: dict[str, str]) -> str:
    canonical = "\0".join(
        str(item.get(field, "")).strip() for field in ("url", "title", "published_at")
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_items(items: Iterable[dict[str, str]], keywords: str) -> list[dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for raw in items:
        item = {
            "title": re.sub(r"\s+", " ", str(raw.get("title", ""))).strip()[:500],
            "url": str(raw.get("url", "")).strip(),
            "published_at": str(raw.get("published_at", "")).strip()[:40],
            "summary": re.sub(r"\s+", " ", str(raw.get("summary", ""))).strip()[:1000],
        }
        if len(item["title"]) < 4 or not item["url"] or not _keyword_match(item, keywords):
            continue
        try:
            parsed_url = urlparse(item["url"])
            if parsed_url.scheme.lower() == "http":
                item["url"] = urlunparse(parsed_url._replace(scheme="https"))
            item["url"] = validate_official_url(item["url"], resolve_dns=False)
        except SourceMonitorError:
            continue
        item["item_id"] = _item_id(item)
        normalized[item["item_id"]] = item
        if len(normalized) >= MAX_DISCOVERY_ITEMS:
            break
    return list(normalized.values())


def _parse_json_items(text: str) -> list[dict[str, str]]:
    payload = json.loads(text)
    candidates = payload.get("results") if isinstance(payload, dict) else payload
    if isinstance(payload, dict) and not isinstance(candidates, list):
        law_search = payload.get("LawSearch", {})
        candidates = law_search.get("law", []) if isinstance(law_search, dict) else []
    if isinstance(candidates, dict):
        candidates = [candidates]
    items: list[dict[str, str]] = []
    for row in candidates or []:
        if not isinstance(row, dict):
            continue
        agencies = row.get("agencies", [])
        agency_text = " ".join(
            str(agency.get("name", "")) for agency in agencies if isinstance(agency, dict)
        )
        items.append(
            {
                "title": str(row.get("title") or row.get("법령명한글") or row.get("법령명") or ""),
                "url": str(row.get("html_url") or row.get("법령상세링크") or row.get("url") or ""),
                "published_at": str(row.get("publication_date") or row.get("공포일자") or ""),
                "summary": f"{row.get('abstract', '')} {agency_text}".strip(),
            }
        )
    return items


def _parse_atom_items(text: str) -> list[dict[str, str]]:
    root = ET.fromstring(text)
    items: list[dict[str, str]] = []
    for entry in root.findall(".//{*}entry"):
        link = next(
            (node.attrib.get("href", "") for node in entry.findall("{*}link") if node.attrib.get("href")),
            "",
        )
        items.append(
            {
                "title": entry.findtext("{*}title", default=""),
                "url": link,
                "published_at": entry.findtext("{*}updated", default="")
                or entry.findtext("{*}published", default=""),
                "summary": entry.findtext("{*}summary", default="")
                or entry.findtext("{*}content", default=""),
            }
        )
    return items


def _parse_html_items(text: str, base_url: str) -> list[dict[str, str]]:
    parser = _LinkParser()
    parser.feed(text)
    return [
        {"title": title, "url": urljoin(base_url, href), "published_at": "", "summary": ""}
        for href, title in parser.links
    ]


def extract_discovery_items(source: dict[str, str], payload: dict[str, Any]) -> list[dict[str, str]]:
    """공식 API·Atom·HTML 목록을 공통 검토 후보 형식으로 변환한다."""
    body = payload["body"]
    content_type = str(payload.get("content_type", ""))
    text = _decode_body(body, content_type)
    source_type = str(source.get("source_type", ""))
    try:
        if source_type in {"json_feed", "korea_law_api"}:
            raw_items = _parse_json_items(text)
        elif source_type == "atom_feed":
            raw_items = _parse_atom_items(text)
        else:
            raw_items = _parse_html_items(text, str(payload.get("final_url") or source.get("url", "")))
    except (json.JSONDecodeError, ET.ParseError) as error:
        raise SourceMonitorError("parse_error", "공식 공고 목록을 해석하지 못했습니다.") from error
    return _normalize_items(raw_items, str(source.get("keywords", "")))


def _source_fingerprint(source: dict[str, str], payload: dict[str, Any], items: list[dict[str, str]]) -> str:
    if source.get("source_type") != "registered_document" and items:
        joined = "\n".join(sorted(item["item_id"] for item in items))
        return sha256(joined.encode("ascii")).hexdigest()
    normalized, _ = normalize_source_content(payload["body"], str(payload.get("content_type", "")))
    visible = normalized.decode("utf-8", errors="replace").casefold()
    blocked_markers = ("incident id:", "access denied", "verify you are human", "captcha")
    if len(visible) < 600 and any(marker in visible for marker in blocked_markers):
        raise SourceMonitorError(
            "automated_access_blocked",
            "공식 사이트가 자동 확인 요청을 차단했습니다. 원문 링크에서 직접 확인해 주세요.",
        )
    return sha256(normalized).hexdigest()


def _event_id(event_type: str, source_id: str, identity: str) -> str:
    return sha256(f"{event_type}\0{source_id}\0{identity}".encode("utf-8")).hexdigest()


def _new_event(
    source: dict[str, str], *, event_type: str, identity: str, detected_at: str,
    item: dict[str, str] | None = None,
) -> dict[str, str]:
    item = item or {}
    title = item.get("title") or f"{source.get('출처명', '공식 출처')} 원문 변경"
    url = item.get("url") or source.get("url", "")
    return {
        "event_id": _event_id(event_type, str(source.get("source_id", "")), identity),
        "detected_at": detected_at,
        "국가": str(source.get("국가", "")),
        "event_type": event_type,
        "출처명": str(source.get("출처명", "")),
        "title": str(title),
        "url": str(url),
        "published_at": str(item.get("published_at", "")),
        "summary": str(item.get("summary", "")),
        "review_status": "pending",
    }


def run_regulatory_monitor(
    *,
    sources: list[dict[str, str]] | None = None,
    previous_state: dict[str, Any] | None = None,
    previous_events: list[dict[str, Any]] | None = None,
    fetcher: Callable[[dict[str, str]], dict[str, Any]] = fetch_monitor_source,
    checked_at: str | None = None,
    max_workers: int = 6,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """모든 공식 출처를 확인하고 변경·신규 후보를 누적한다."""
    checked_at = checked_at or _utc_now()
    sources = sources or [*load_registered_sources(), *load_monitor_sources()]
    previous_state = previous_state or {}
    previous_by_id = {
        str(row.get("source_id", "")): row for row in previous_state.get("sources", [])
    }
    events_by_id = {
        str(row.get("event_id", "")): dict(row) for row in (previous_events or [])
    }

    fetched: dict[str, dict[str, Any] | Exception] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(sources) or 1))) as executor:
        future_map = {executor.submit(fetcher, source): source for source in sources}
        for future in as_completed(future_map):
            source = future_map[future]
            try:
                fetched[str(source["source_id"])] = future.result()
            except Exception as error:  # 출처 하나의 실패가 전체 모니터링을 막지 않는다.
                fetched[str(source["source_id"])] = error

    current_rows: list[dict[str, Any]] = []
    for source in sources:
        source_id = str(source.get("source_id", ""))
        previous = previous_by_id.get(source_id, {})
        result = fetched.get(source_id)
        base = {
            "source_id": source_id,
            "국가": str(source.get("국가", "")),
            "출처명": str(source.get("출처명", "")),
            "source_type": str(source.get("source_type", "")),
            "url": str(source.get("url", "")),
            "checked_at": checked_at,
            "status": "error",
            "http_status": 0,
            "fingerprint": str(previous.get("fingerprint", "")),
            "items": list(previous.get("items", [])),
            "error_code": "",
            "error_message": "",
        }
        if isinstance(result, Exception) or result is None:
            error = result if isinstance(result, Exception) else RuntimeError("확인 결과 없음")
            base["error_code"] = getattr(error, "code", "unexpected_error")
            base["error_message"] = str(error)
            current_rows.append(base)
            continue

        try:
            items = (
                []
                if source.get("source_type") == "registered_document"
                else extract_discovery_items(source, result)
            )
            fingerprint = _source_fingerprint(source, result, items)
            previous_fingerprint = str(previous.get("fingerprint", ""))
            status = "baseline" if not previous_fingerprint else (
                "unchanged" if previous_fingerprint == fingerprint else "changed"
            )
            base.update(
                status=status,
                http_status=int(result.get("http_status", 0)),
                fingerprint=fingerprint,
                items=items,
                error_code="",
                error_message="",
            )
            if previous_fingerprint and status == "changed":
                if source.get("source_type") == "registered_document":
                    event = _new_event(
                        source,
                        event_type="registered_source_changed",
                        identity=fingerprint,
                        detected_at=checked_at,
                    )
                    events_by_id.setdefault(event["event_id"], event)
                else:
                    old_item_ids = {
                        str(item.get("item_id", "")) for item in previous.get("items", [])
                    }
                    for item in items:
                        if item["item_id"] in old_item_ids:
                            continue
                        event = _new_event(
                            source,
                            event_type="new_official_candidate",
                            identity=item["item_id"],
                            detected_at=checked_at,
                            item=item,
                        )
                        events_by_id.setdefault(event["event_id"], event)
        except Exception as error:
            base.update(
                status="error",
                error_code=getattr(error, "code", "parse_error"),
                error_message=str(error),
            )
        current_rows.append(base)

    state = {
        "schema_version": 1,
        "monitor_version": MONITOR_VERSION,
        "generated_at": checked_at,
        "source_count": len(current_rows),
        "sources": sorted(current_rows, key=lambda row: (row["국가"], row["출처명"])),
    }
    events = sorted(
        events_by_id.values(),
        key=lambda row: str(row.get("detected_at", "")),
        reverse=True,
    )[:500]
    return state, events


def load_monitor_snapshot(
    state_path: str | Path | None = None,
    events_path: str | Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """앱이 Git에 저장된 최신 모니터링 결과를 읽는다."""
    state = _read_json(Path(state_path) if state_path else MONITOR_STATE_PATH, {})
    events = _read_json(Path(events_path) if events_path else MONITOR_EVENTS_PATH, [])
    return state if isinstance(state, dict) else {}, events if isinstance(events, list) else []


def save_monitor_snapshot(
    state: dict[str, Any],
    events: list[dict[str, Any]],
    state_path: str | Path | None = None,
    events_path: str | Path | None = None,
) -> None:
    """스케줄러 결과를 앱이 읽는 JSON 파일에 원자적으로 가까운 형태로 저장한다."""
    _write_json(Path(state_path) if state_path else MONITOR_STATE_PATH, state)
    _write_json(Path(events_path) if events_path else MONITOR_EVENTS_PATH, events)
