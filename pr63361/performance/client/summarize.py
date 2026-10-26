# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Recompute the token reuse table from the supplied per-request records."""
import argparse
import json
from pathlib import Path
import statistics


def read(path):
    return json.loads(path.read_text())


def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low = int(position)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)


def load(run, case):
    rows = [json.loads(line) for line in (run / case / "requests.jsonl").read_text().splitlines()]
    if len(rows) != 80 or any(row["status"] != "ok" for row in rows):
        raise ValueError(f"Incomplete or failed run: {run}")
    if len({row["id"] for row in rows}) != 80:
        raise ValueError("Duplicate request ID")
    measurement = read(run / case / "measurement.json")
    if not measurement["measurement_valid"]:
        raise ValueError("Invalid measurement")
    return {
        "first_output_ms": statistics.mean(r["first_output_chunk_s"] for r in rows) * 1000,
        "first_output_p95_ms": percentile([r["first_output_chunk_s"] for r in rows], .95) * 1000,
        "e2e_s": statistics.mean(r["http_e2e_s"] for r in rows),
        "frontend_cpu_ms_per_request": measurement["cpu"]["seconds"]["frontend"] / 80 * 1000,
        "cached_tokens": {r["id"]: r["usage"]["prompt_tokens_details"]["cached_tokens"] for r in rows},
    }


def summarize(root):
    result = {}
    for case in ("coding", "independent"):
        blocks = []
        for number in range(1, 5):
            folder = root / "runs-001" / case / f"block-{number}"
            baseline = load(next(folder.glob("pos-*-N")), case)
            reuse = load(next(folder.glob("pos-*-V1")), case)
            if baseline.pop("cached_tokens") != reuse.pop("cached_tokens"):
                raise ValueError("Native cached-token counts differ within a pair")
            changes = {key: (reuse[key] / baseline[key] - 1) * 100 for key in baseline}
            blocks.append({"block": number, "baseline": baseline,
                           "token_reuse": reuse, "percent_change": changes})
        result[case] = {"blocks": blocks}
        for label in ("baseline", "token_reuse", "percent_change"):
            result[case][label] = {key: statistics.mean(b[label][key] for b in blocks)
                                  for key in blocks[0][label]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path(__file__).resolve().parents[1] / "results")
    parser.add_argument("--output", type=Path, required=True, help="New directory")
    args = parser.parse_args()
    result = summarize(args.results)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    table = ["| Workload / metric | Baseline | Token reuse | Mean paired change |",
             "|---|---:|---:|---:|"]
    for case, key, label, unit in (
        ("coding", "frontend_cpu_ms_per_request", "Growing histories: API CPU/request", "CPU-ms"),
        ("coding", "first_output_ms", "Growing histories: first output", "ms"),
        ("coding", "e2e_s", "Growing histories: end-to-end", "s"),
        ("independent", "first_output_ms", "Independent: first output", "ms"),
        ("independent", "first_output_p95_ms", "Independent: P95 first output", "ms"),
    ):
        row = result[case]
        table.append(f"| {label} | {row['baseline'][key]:.3f} {unit} | "
                     f"{row['token_reuse'][key]:.3f} {unit} | {row['percent_change'][key]:+.3f}% |")
    table.extend(["", "Changes are averaged across four matched pairs of runs.",
                  "P95 values are averages of the four run P95s; no significance claim."])
    (args.output / "table.md").write_text("\n".join(table) + "\n")
    print("\n".join(table))


if __name__ == "__main__":
    main()
