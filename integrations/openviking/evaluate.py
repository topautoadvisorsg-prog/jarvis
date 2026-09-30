"""Compare local lexical source selection with scoped OpenViking retrieval."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .second_brain import plan_sources, semantic_find


WORDS = re.compile(r"[a-z0-9][a-z0-9_-]{2,}")
STOPWORDS = {
    "and", "are", "but", "can", "current", "does", "from", "give", "how",
    "into", "its", "me", "not", "the", "this", "through", "what", "when",
    "where", "which", "why", "with",
}


def _tokens(text: str) -> list[str]:
    return [word for word in WORDS.findall(text.casefold()) if word not in STOPWORDS]


def _lexical_rank(question: str, planned: list[Any]) -> list[str]:
    documents = [Counter(_tokens(item.source.read_text(encoding="utf-8"))) for item in planned]
    query = set(_tokens(question))
    ranked: list[tuple[float, str]] = []
    for index, (item, counts) in enumerate(zip(planned, documents, strict=True)):
        score = 0.0
        for token in query:
            frequency = counts[token]
            if not frequency:
                continue
            document_frequency = sum(token in document for document in documents)
            inverse = math.log((len(documents) + 1) / (document_frequency + 1)) + 1
            score += (1 + math.log(frequency)) * inverse
        ranked.append((score, item.target))
    return [target for _, target in sorted(ranked, key=lambda row: (-row[0], row[1]))]


def _openviking_uris(result: dict[str, Any]) -> list[str]:
    body = result.get("result") or {}
    return [str(item.get("uri") or "") for item in body.get("resources") or []]


def _rank(expected: str, paths: list[str]) -> int | None:
    for index, path in enumerate(paths, start=1):
        if expected in path:
            return index
    return None


def evaluate(manifest_path: Path, cases_path: Path) -> dict[str, Any]:
    manifest, planned = plan_sources(manifest_path)
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case in cases:
        baseline = _lexical_rank(case["question"], planned)
        started = time.perf_counter()
        result = semantic_find(manifest, case["question"], limit=8)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        latencies.append(latency_ms)
        openviking = _openviking_uris(result)
        expected = case["expectedTarget"]
        rows.append({
            **case,
            "baselineRank": _rank(expected, baseline),
            "baselineTop3": baseline[:3],
            "openVikingRank": _rank(expected, openviking),
            "openVikingTop3": openviking[:3],
            "latencyMs": latency_ms,
        })
    baseline_top1 = sum(row["baselineRank"] == 1 for row in rows)
    openviking_top1 = sum(row["openVikingRank"] == 1 for row in rows)
    baseline_top3 = sum((row["baselineRank"] or 99) <= 3 for row in rows)
    openviking_top3 = sum((row["openVikingRank"] or 99) <= 3 for row in rows)
    return {
        "schemaVersion": 1,
        "caseCount": len(rows),
        "baselineMethod": "deterministic IDF-weighted repository text search",
        "sessionSearchIncluded": False,
        "sessionSearchReason": "Session history does not provide authoritative paths for this fixed document-source test.",
        "scores": {
            "baselineTop1": baseline_top1,
            "openVikingTop1": openviking_top1,
            "baselineTop3": baseline_top3,
            "openVikingTop3": openviking_top3,
        },
        "latencyMs": {
            "minimum": min(latencies),
            "median": round(statistics.median(latencies), 2),
            "maximum": max(latencies),
        },
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.manifest, args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scores": report["scores"], "latencyMs": report["latencyMs"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
