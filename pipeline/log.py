"""Structured run logger.

All pipeline stages write to the same RunLogger instance so the full
execution can be reconstructed from one JSON + one text file.

Usage:
    logger = RunLogger(run_id)
    logger.event("ingest", "loaded", table_id="1.1", row_count=500)
    logger.event("harmonise", "dropped_column", table="h_foo", column="bar_1", reason="duplicate of bar")
    logger.close()   # flushes logs/<run_id>_run.jsonl and logs/<run_id>_summary.txt
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class RunLogger:
    LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.started_at = datetime.now()
        self.events: list[dict] = []
        self.LOGS_DIR.mkdir(exist_ok=True)
        self._jsonl_path = self.LOGS_DIR / f"{run_id}_run.jsonl"
        self._txt_path = self.LOGS_DIR / f"{run_id}_summary.txt"
        self._jsonl_fh = open(self._jsonl_path, "w", encoding="utf-8")
        self._t0 = time.time()

    # ── public API ─────────────────────────────────────────────────────────────

    def event(self, stage: str, action: str, **kwargs: Any) -> None:
        """Record a structured event. Printed + buffered for final report."""
        entry: dict = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "stage": stage,
            "action": action,
            **kwargs,
        }
        self.events.append(entry)
        self._jsonl_fh.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")
        self._jsonl_fh.flush()

        # Human-readable console line
        parts = [f"[{stage}]", action]
        for k, v in kwargs.items():
            parts.append(f"{k}={v}")
        print("  " + "  ".join(parts))

    def section(self, title: str) -> None:
        """Print a visible section header."""
        print(f"\n{'─' * 60}")
        print(f"  {title}")
        print(f"{'─' * 60}")

    def close(self) -> None:
        """Flush logs and write the human-readable summary."""
        self._jsonl_fh.close()
        self._write_summary()
        print(f"\nLog JSONL : {self._jsonl_path}")
        print(f"Summary   : {self._txt_path}")

    # ── internals ──────────────────────────────────────────────────────────────

    def _write_summary(self) -> None:
        elapsed = time.time() - self._t0

        by_stage: dict[str, list[dict]] = {}
        for e in self.events:
            by_stage.setdefault(e["stage"], []).append(e)

        lines: list[str] = [
            "=" * 60,
            f"MHS Pipeline Run: {self.run_id}",
            f"Started : {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Elapsed : {elapsed:.1f}s",
            "=" * 60,
            "",
        ]

        for stage, evts in by_stage.items():
            lines.append(f"── {stage} ({len(evts)} events) " + "─" * max(0, 54 - len(stage)))
            by_action: dict[str, int] = {}
            for e in evts:
                by_action[e["action"]] = by_action.get(e["action"], 0) + 1
            for action, count in sorted(by_action.items()):
                lines.append(f"   {action:<40} {count:>4}×")
            lines.append("")

        # Ingest detail
        loaded = [e for e in self.events if e["stage"] == "ingest" and e["action"] == "loaded"]
        errors = [e for e in self.events if e["stage"] == "ingest" and e["action"] in ("parse_error", "load_error")]
        if loaded:
            lines += [
                "── Ingest: loaded tables ────────────────────────────────",
                *[
                    f"  {e.get('table_id','?'):<14} {e.get('row_count',0):>6} rows  "
                    f"{e.get('col_count',0):>3} cols  "
                    f"{e.get('date_min','?')}..{e.get('date_max','?')}"
                    for e in loaded
                ],
                "",
            ]
        if errors:
            lines += [
                "── Ingest: errors ───────────────────────────────────────",
                *[f"  {e.get('table_id','?'):<14} {e.get('error','')}" for e in errors],
                "",
            ]

        # Harmonise dedup detail (only dedup events, not column_map noise)
        dedup_actions = {"column_dropped_empty", "column_dropped_duplicate",
                         "column_merged", "column_kept_conflict"}
        dedup_evts = [e for e in self.events if e["stage"] == "harmonise"
                      and e["action"] in dedup_actions]
        if dedup_evts:
            lines += [
                "── Harmonise: column dedup decisions ────────────────────",
                *[
                    f"  {e.get('table','?'):<35} {e.get('col_name','?'):<35} {e.get('action','')}"
                    for e in dedup_evts
                ],
                "",
            ]

        lines.append("=" * 60)

        with open(self._txt_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
