"""Collection run report (markdown) — the Phase 2 deliverable artifact."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def render_report(db_path: Path, per_source: dict[str, dict[str, Any]], mode: str, only_ids: set[str] | None = None) -> str:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if only_ids is None:
        where, params = "WHERE 1=1", ()
    else:
        ids = list(only_ids)
        if not ids:
            ids = [""]
        where = f"WHERE id IN ({','.join('?' * len(ids))})"
        params = tuple(ids)
    rows = {r["source"]: r for r in conn.execute(
        f"SELECT source, COUNT(*) AS n, COUNT(DISTINCT author) AS users, "
        f"MIN(timestamp) AS min_ts, MAX(timestamp) AS max_ts, "
        f"SUM(CASE WHEN is_duplicate_of IS NULL THEN 0 ELSE 1 END) AS dupes, "
        f"SUM(CASE WHEN url <> '' THEN 1 ELSE 0 END) AS with_url "
        f"FROM conversations {where} GROUP BY source", params)}
    total = conn.execute(f"SELECT COUNT(*) AS n FROM conversations {where}", params).fetchone()["n"]
    conn.close()

    lines = [
        "# Collection Run Report",
        "",
        f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}",
        f"- **Mode:** {mode}",
        f"- **Total kept conversations:** {total}",
        "",
        "## Per-source",
        "",
        "| Source | Kept | Users | With URL | Duplicates (in run) | Invalid | Date-filtered | Date range | Errors |",
        "|--------|------|-------|----------|---------------------|---------|---------------|------------|--------|",
    ]
    for source, row in sorted(rows.items()):
        stats = per_source.get(source, {})
        date_range = _range(row["min_ts"], row["max_ts"])
        lines.append(
            f"| {source} | {row['n']} | {row['users'] or 0} | {row['with_url']} | "
            f"{stats.get('duplicates', 0)} | {stats.get('invalid', 0)} | {stats.get('filtered', 0)} | "
            f"{date_range} | "
            f"{'; '.join(stats.get('errors', [])) or '-'} |"
        )
    lines += ["", "## Source URL / traceability", ""]
    for source, row in sorted(rows.items()):
        coverage = (row["with_url"] / row["n"] * 100) if row["n"] else 0
        lines.append(f"- **{source}:** {coverage:.0f}% of kept conversations carry a source URL.")
    lines.append("")
    lines.append("## Adapter log")
    return "\n".join(lines)


def render_adapter_log(log: list[str]) -> str:
    return "\n".join(f"- {entry}" for entry in log)


def _range(min_ts: str | None, max_ts: str | None) -> str:
    if not min_ts or not max_ts:
        return "n/a"
    return f"{_short(min_ts)} .. {_short(max_ts)}"


def _short(iso: str) -> str:
    try:
        return iso[:10]
    except Exception:
        return iso