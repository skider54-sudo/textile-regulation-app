"""GitHub Actions와 로컬에서 실행하는 규제 모니터링 진입점."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from texreg_core.regulatory_monitor import (  # noqa: E402
    load_monitor_snapshot,
    run_regulatory_monitor,
    save_monitor_snapshot,
)


def main() -> int:
    previous_state, previous_events = load_monitor_snapshot()
    state, events = run_regulatory_monitor(
        previous_state=previous_state,
        previous_events=previous_events,
    )
    save_monitor_snapshot(state, events)
    success = sum(row.get("status") != "error" for row in state.get("sources", []))
    errors = int(state.get("source_count", 0)) - success
    pending = sum(event.get("review_status") == "pending" for event in events)
    print(
        f"Regulatory monitor complete: {success} successful, {errors} errors, "
        f"{pending} pending review events."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
