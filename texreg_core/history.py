"""진단 당시 결과를 변경 불가능한 SQLite 스냅샷으로 보관한다."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY_DB = BASE_DIR / "data" / "diagnosis_history.db"
SNAPSHOT_SCHEMA_VERSION = 1
APP_RULESET_VERSION = "2.5"
HISTORY_LIST_COLUMNS = [
    "record_id",
    "diagnosed_at",
    "product_name",
    "destinations",
    "risk_score",
    "risk_level",
    "regulation_count",
    "regulation_reviewed_at",
    "ruleset_version",
    "ruleset_fingerprint",
    "source",
    "parent_record_id",
]


def history_db_path() -> Path:
    """테스트·배포 환경에서는 환경변수로 저장 위치를 바꿀 수 있다."""
    configured = os.getenv("TEXREG_HISTORY_DB", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_HISTORY_DB


@contextmanager
def _connect(db_path: str | Path | None = None):
    """트랜잭션을 처리하고 Windows에서도 DB 파일 핸들을 즉시 반환한다."""
    path = Path(db_path) if db_path else history_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_history_db(db_path: str | Path | None = None) -> None:
    """진단 이력 테이블과 조회 인덱스를 준비한다."""
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS diagnosis_history (
                record_id TEXT PRIMARY KEY,
                diagnosed_at TEXT NOT NULL,
                product_name TEXT NOT NULL,
                destinations TEXT NOT NULL DEFAULT '',
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                regulation_count INTEGER NOT NULL,
                regulation_reviewed_at TEXT NOT NULL DEFAULT '',
                ruleset_version TEXT NOT NULL,
                ruleset_fingerprint TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                parent_record_id TEXT NOT NULL DEFAULT '',
                snapshot_schema INTEGER NOT NULL,
                result_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_history_diagnosed_at
                ON diagnosis_history(diagnosed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_history_product_name
                ON diagnosis_history(product_name, diagnosed_at DESC);
            """
        )


def ruleset_fingerprint() -> str:
    """규제·대응·일정 DB와 매칭 코드의 조합을 짧은 버전 해시로 만든다."""
    digest = hashlib.sha256()
    paths = [
        BASE_DIR / "data" / "regulations.csv",
        BASE_DIR / "data" / "regulation_actions.csv",
        BASE_DIR / "data" / "regulation_timeline.csv",
        BASE_DIR / "texreg_core" / "matching.py",
    ]
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def _latest_reviewed_at(result: dict[str, Any]) -> str:
    reviewed_dates = [
        str(item.get("최근확인일", "")).strip()
        for item in result.get("규제", [])
        if str(item.get("최근확인일", "")).strip()
    ]
    return max(reviewed_dates, default="미확인")


def save_diagnosis_snapshot(
    result: dict[str, Any],
    *,
    source: str = "manual",
    parent_record_id: str = "",
    diagnosed_at: str | None = None,
    record_id: str | None = None,
    ignore_existing: bool = False,
    db_path: str | Path | None = None,
) -> str:
    """진단 결과 전체를 새 이력으로 저장하고 고유 기록 ID를 반환한다."""
    initialize_history_db(db_path)
    snapshot_id = record_id or str(uuid4())
    timestamp = diagnosed_at or datetime.now().astimezone().isoformat(timespec="seconds")
    product = result.get("제품", {})
    matches = result.get("규제", [])
    payload = json.dumps(result, ensure_ascii=False, default=str, separators=(",", ":"))
    insert_keyword = "INSERT OR IGNORE" if ignore_existing else "INSERT"

    with _connect(db_path) as connection:
        connection.execute(
            f"""
            {insert_keyword} INTO diagnosis_history (
                record_id, diagnosed_at, product_name, destinations,
                risk_score, risk_level, regulation_count, regulation_reviewed_at,
                ruleset_version, ruleset_fingerprint, source, parent_record_id,
                snapshot_schema, result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                timestamp,
                str(product.get("제품명", "미입력")),
                str(product.get("수출국", "")),
                int(result.get("score", 0)),
                str(result.get("위험도", "낮음")),
                len(matches),
                _latest_reviewed_at(result),
                APP_RULESET_VERSION,
                ruleset_fingerprint(),
                source,
                parent_record_id,
                SNAPSHOT_SCHEMA_VERSION,
                payload,
            ),
        )
    return snapshot_id


def list_diagnosis_history(db_path: str | Path | None = None) -> pd.DataFrame:
    """사용자에게 표시할 진단 이력 목록을 최신 순으로 반환한다."""
    initialize_history_db(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT record_id, diagnosed_at, product_name, destinations,
                   risk_score, risk_level, regulation_count,
                   regulation_reviewed_at, ruleset_version,
                   ruleset_fingerprint, source, parent_record_id
            FROM diagnosis_history
            ORDER BY diagnosed_at DESC, rowid DESC
            """
        ).fetchall()
    return pd.DataFrame([dict(row) for row in rows], columns=HISTORY_LIST_COLUMNS)


def get_diagnosis_snapshot(
    record_id: str, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    """고유 기록 ID로 당시 결과와 저장 메타데이터를 읽는다."""
    initialize_history_db(db_path)
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM diagnosis_history WHERE record_id = ?",
            (record_id,),
        ).fetchone()
    if row is None:
        return None
    metadata = dict(row)
    result = json.loads(metadata.pop("result_json"))
    return {"메타데이터": metadata, "결과": result}


def export_history_json(db_path: str | Path | None = None) -> str:
    """장기 백업용으로 모든 스냅샷을 한 JSON 파일에 직렬화한다."""
    initialize_history_db(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM diagnosis_history ORDER BY diagnosed_at ASC, rowid ASC"
        ).fetchall()
        source_table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'regulation_source_checks'"
        ).fetchone()
        source_rows = (
            connection.execute(
                "SELECT * FROM regulation_source_checks ORDER BY checked_at ASC, rowid ASC"
            ).fetchall()
            if source_table_exists
            else []
        )
    records = []
    for row in rows:
        item = dict(row)
        item["result"] = json.loads(item.pop("result_json"))
        records.append(item)
    return json.dumps(
        {
            "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "snapshot_schema": SNAPSHOT_SCHEMA_VERSION,
            "records": records,
            "source_checks": [dict(row) for row in source_rows],
        },
        ensure_ascii=False,
        indent=2,
    )
