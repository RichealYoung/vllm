# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Replay one fixed workload against an already running, fresh server."""
import argparse
import asyncio
import importlib.metadata
import os
from pathlib import Path
import platform
import sys

import httpx

from session_prefix_bench import adapter, telemetry
from session_prefix_bench.common import file_sha, unseal, validate_workload, write
from session_prefix_bench.measure import batch, request

WORKLOAD_SHA = "935e387020d27548aba5da24c997c9381a03bd4fc8735e3d1ef5e3c2dd44f833"


async def run(args):
    if any(k.startswith("SP_ACCOUNTING") or k in
           ("SP_PREFLIGHT_CLIENT", "SP_BENCH_DIAGNOSTIC_DIR") for k in os.environ):
        raise ValueError("Remove diagnostic/accounting instrumentation")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    status = {"status": "failed", "workload": args.case}
    try:
        write(output / "invocation.json", {
        "argv": sys.argv, "python": platform.python_version(),
        "workload_sha256": WORKLOAD_SHA,
        "fresh_server_operator_confirmation": True,
        "packages": {n: importlib.metadata.version(n)
                     for n in ("httpx", "httpcore", "anyio", "psutil")},
        "inputs": {str(p.relative_to(Path(__file__).parent)): file_sha(p)
                   for p in Path(__file__).parent.rglob("*.py")},
        })
        if file_sha(args.workload) != WORKLOAD_SHA:
            raise ValueError("Workload differs from the fixed benchmark input")
        data = validate_workload(unseal(args.workload))
        # Set affinity externally before launch; this also binds HTTP threads.
        limits = httpx.Limits(max_connections=4)
        async with httpx.AsyncClient(base_url=args.url.rstrip("/"), timeout=180,
                                     trust_env=False, limits=limits) as client:
            (await client.get("/health")).raise_for_status()
            warm = [dict(lane[-1], id=f"warm-long-{i}",
                         session_id=f"warm-long-{i}")
                    for i, lane in enumerate(data["workloads"]["coding"])]
            short = [r for lane in data["workloads"]["independent"] for r in lane]
            for i, size in enumerate(("512", "1024", "2048", "1024")):
                row = next(r for r in short if r["group"] == size)
                warm.append(dict(row, id=f"warm-short-{i}",
                                 session_id=f"warm-short-{i}"))
            rows = []
            for start in (0, 4):
                rows.extend(await asyncio.gather(*[
                    request(client, row, args.model, "warmup")
                    for row in warm[start:start + 4]]))
            write(output / "warmup.json", rows)
            if any(r["status"] != "ok" for r in rows):
                raise ValueError("Warmup failed; retain evidence and stop")
            case = output / args.case
            case.mkdir()
            await adapter.reset(client)
            before = await telemetry.idle(client, case, "before", empty_kv=True)
            result = await batch(client, data["workloads"][args.case],
                                 args.model, "matrix-session", args.server_pid,
                                 case, cpu_enabled=args.server_pid is not None)
            after = await telemetry.idle(client, case, "after")
            if before["preemptions"] != after["preemptions"]:
                raise ValueError("Preemption during measurement")
            if not result["measurement_valid"]:
                raise ValueError(f"Invalid measurement: {result['error']}")
            status.update(status="passed", requests=80, warmup_requests=8,
                          cpu_collected=args.server_pid is not None)
    except BaseException as exc:
        status["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        write(output / "terminal.json", status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Origin URL, without /v1")
    parser.add_argument("--model", default="session-prefix-bench")
    parser.add_argument("--workload", type=Path,
                        default=Path(__file__).resolve().parents[1] / "workload-v1.json")
    parser.add_argument("--case", choices=("coding", "independent"), required=True)
    parser.add_argument("--output", required=True, help="New output directory")
    parser.add_argument("--server-pid", type=int,
                        help="Local API PID, optional process-tree CPU accounting")
    parser.add_argument("--fresh-server-confirmed", action="store_true", required=True,
                        help="Confirm a new exclusive service, not a reused process")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
