#!/usr/bin/env python3
"""Probe Torn stock-log structure without persisting user log values.

The probe uses the official read-only Torn API. It persists only public log-type
identifiers/names plus observed top-level field names and Python type classes.
No log values, timestamps, titles, prices, fees, holdings, or account totals are
written to the report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from torn_research import ResearchToolError, TornApiClient

MAX_LOG_FILTERS = 10
ALLOWED_TOP_LEVEL = {
    "research_status",
    "source",
    "stock_log_type_count",
    "observed_stock_log_type_count",
    "user_log_access",
    "log_types",
    "interpretation",
}
ALLOWED_TYPE_KEYS = {
    "log_type_id",
    "public_name",
    "observed_count",
    "data_field_types",
    "params_field_types",
}


def extract_logtypes(payload: Any) -> dict[int, str]:
    if not isinstance(payload, Mapping):
        raise ResearchToolError("Expected mapping response from /torn/logtypes.")
    candidate = payload.get("logtypes", payload.get("data"))
    if not isinstance(candidate, Mapping):
        raise ResearchToolError("No logtypes mapping found in /torn/logtypes response.")
    result: dict[int, str] = {}
    for key, value in candidate.items():
        try:
            log_id = int(key)
        except (TypeError, ValueError):
            continue
        if isinstance(value, str) and value.strip():
            result[log_id] = value.strip()
    if not result:
        raise ResearchToolError("No usable log types returned by /torn/logtypes.")
    return result


def stock_logtypes(logtypes: Mapping[int, str]) -> dict[int, str]:
    return {log_id: name for log_id, name in logtypes.items() if "stock" in name.lower()}


def chunks(values: Sequence[int], size: int = MAX_LOG_FILTERS) -> Iterable[list[int]]:
    if size < 1 or size > MAX_LOG_FILTERS:
        raise ValueError(f"chunk size must be between 1 and {MAX_LOG_FILTERS}")
    for index in range(0, len(values), size):
        yield list(values[index:index + size])


def iter_log_entries(payload: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return
    candidate = payload.get("log", payload.get("logs"))
    if isinstance(candidate, Mapping):
        for entry in candidate.values():
            if isinstance(entry, Mapping):
                yield entry
    elif isinstance(candidate, list):
        for entry in candidate:
            if isinstance(entry, Mapping):
                yield entry


def type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def accumulate_field_types(target: dict[str, set[str]], value: Any) -> None:
    if not isinstance(value, Mapping):
        return
    for key, field_value in value.items():
        if not isinstance(key, str) or not key:
            continue
        target.setdefault(key, set()).add(type_name(field_value))


def summarize_entries(
    declared_types: Mapping[int, str],
    payloads: Sequence[Any],
) -> list[dict[str, Any]]:
    state: dict[int, dict[str, Any]] = {
        log_id: {
            "log_type_id": log_id,
            "public_name": name,
            "observed_count": 0,
            "data_field_types": {},
            "params_field_types": {},
        }
        for log_id, name in declared_types.items()
    }
    for payload in payloads:
        for entry in iter_log_entries(payload):
            raw_id = entry.get("log")
            try:
                log_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if log_id not in state:
                continue
            row = state[log_id]
            row["observed_count"] += 1
            accumulate_field_types(row["data_field_types"], entry.get("data"))
            accumulate_field_types(row["params_field_types"], entry.get("params"))

    rows: list[dict[str, Any]] = []
    for log_id in sorted(state):
        row = state[log_id]
        rows.append({
            "log_type_id": row["log_type_id"],
            "public_name": row["public_name"],
            "observed_count": row["observed_count"],
            "data_field_types": {key: sorted(types) for key, types in sorted(row["data_field_types"].items())},
            "params_field_types": {key: sorted(types) for key, types in sorted(row["params_field_types"].items())},
        })
    return rows


def assert_safe_report(report: Mapping[str, Any]) -> None:
    if set(report) != ALLOWED_TOP_LEVEL:
        raise ResearchToolError("Schema-probe output contains an unexpected top-level field.")
    rows = report.get("log_types")
    if not isinstance(rows, list):
        raise ResearchToolError("Schema-probe log_types must be a list.")
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != ALLOWED_TYPE_KEYS:
            raise ResearchToolError("Schema-probe output contains an unexpected per-type field.")
        if not isinstance(row.get("log_type_id"), int) or not isinstance(row.get("observed_count"), int):
            raise ResearchToolError("Schema-probe IDs/counts must be integers.")
        if not isinstance(row.get("public_name"), str):
            raise ResearchToolError("Schema-probe public_name must be a string.")
        for field in ("data_field_types", "params_field_types"):
            mapping = row.get(field)
            if not isinstance(mapping, Mapping):
                raise ResearchToolError(f"{field} must be a mapping.")
            for key, classes in mapping.items():
                if not isinstance(key, str) or not isinstance(classes, list) or not all(isinstance(x, str) for x in classes):
                    raise ResearchToolError(f"Unsafe {field} structure.")


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    assert_safe_report(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    client = TornApiClient(args.api_key)
    logtypes_observation = client.get("/torn/logtypes")
    declared = stock_logtypes(extract_logtypes(logtypes_observation.payload))
    if not declared:
        raise ResearchToolError("Official log-type catalog contained no stock-related entries.")

    payloads: list[Any] = []
    access = "available"
    try:
        ids = sorted(declared)
        for batch in chunks(ids):
            observation = client.get("/user/log", {"log": ",".join(str(value) for value in batch)})
            payloads.append(observation.payload)
    except ResearchToolError:
        # Deliberately do not persist the API error body; access availability alone is sufficient.
        access = "unavailable_or_insufficient"

    rows = summarize_entries(declared, payloads)
    report = {
        "research_status": "SCHEMA_OBSERVATION_ONLY",
        "source": "official_torn_api_v2",
        "stock_log_type_count": len(rows),
        "observed_stock_log_type_count": sum(row["observed_count"] > 0 for row in rows),
        "user_log_access": access,
        "log_types": rows,
        "interpretation": "Field names/types only. No user log values are persisted; no execution mechanic is inferred by this probe alone.",
    }
    write_report(Path(args.output), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if access == "available" else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe stock-log field schema without persisting user values.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--output", default="research/output/stock_log_schema/summary.json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except (ResearchToolError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
