"""Closed-loop four-lane HTTP measurement, no vLLM imports or per-token tracing."""
import asyncio
import json
import time
import os

from . import adapter, cpu
from .common import CONTRACT, write


async def request(client, row, model, namespace):
    start = time.perf_counter_ns()
    first = None
    state = {}
    done = False
    try:
        async with asyncio.timeout(CONTRACT["request_deadline_s"]):
            async with client.stream("POST", "/v1/chat/completions",
                                     json=adapter.payload(row, model, namespace,
                                                          diagnostic=bool(os.environ.get("SP_PREFLIGHT_CLIENT")))) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    value = line[5:].strip()
                    if value == "[DONE]":
                        done = True
                        continue
                    if value:
                        visible = adapter.handle_event(json.loads(value), state)
                        if visible and first is None:
                            first = time.perf_counter_ns()
        end = time.perf_counter_ns()
        if not done or first is None or state.get("finish_reason") != "length":
            raise ValueError("Missing output, terminal event, or fixed-length finish")
        usage = state.get("usage", {})
        if usage.get("completion_tokens") != row["output_tokens"]:
            raise ValueError("Actual output length differs from frozen target")
        if usage.get("prompt_tokens") != row["input_tokens"]:
            raise ValueError("Server prompt length differs from frozen tokenizer")
        if os.environ.get("SP_PREFLIGHT_CLIENT"):
            ids = state.get("prompt_token_ids")
            if not isinstance(ids, list) or len(ids) != row["input_tokens"]:
                raise ValueError("Full prompt IDs absent or wrong length")
        details = usage.get("prompt_tokens_details")
        if not isinstance(details, dict) or type(details.get("cached_tokens")) is not int:
            raise ValueError("Actual cached-token details missing")
        return {"id": row["id"], "lane": row["lane"], "index": row["index"],
                "group": row["group"], "start_ns": start, "end_ns": end,
                "first_output_chunk_s": (first - start) / 1e9,
                "http_e2e_s": (end - start) / 1e9, "usage": usage,
                "finish_reason": state["finish_reason"], "status": "ok",
                "prompt_token_ids": state.get("prompt_token_ids")}
    except Exception as exc:
        return {"id": row["id"], "lane": row["lane"], "index": row["index"],
                "start_ns": start, "end_ns": time.perf_counter_ns(),
                "status": "failed", "error": f"{type(exc).__name__}: {exc}"}


async def batch(client, lanes, model, namespace, root_pid, output, cpu_enabled=True):
    rows = []
    expected_requests = sum(len(queue) for queue in lanes)
    before = cpu.snapshot(root_pid) if cpu_enabled else None
    released = time.perf_counter_ns()
    valid = True
    error = None

    async def lane(queue):
        for item in queue:
            row = await request(client, item, model, namespace)
            rows.append(row)
            if row["status"] != "ok":
                raise RuntimeError(row["error"])

    tasks = [asyncio.create_task(lane(queue)) for queue in lanes]
    try:
        async with asyncio.timeout(CONTRACT["batch_deadline_s"]):
            await asyncio.gather(*tasks)
    except (Exception, asyncio.CancelledError) as exc:
        valid, error = False, f"{type(exc).__name__}: {exc}"
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    completed = time.perf_counter_ns()
    after = None
    accounted = None
    try:
        if cpu_enabled:
            after = cpu.snapshot(root_pid)
            accounted = cpu.delta(before, after, expected_requests)
    except Exception as exc:
        valid, error = False, f"CPU accounting: {exc}"
    valid &= len(rows) == expected_requests and all(r["status"] == "ok" for r in rows)
    attempted = {r["id"] for r in rows}
    missing = [r["id"] for queue in lanes for r in queue if r["id"] not in attempted]
    with (output / "requests.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    result = {"measurement_valid": bool(valid), "error": error,
              "batch_s": (completed - released) / 1e9,
              "release_ns": released, "completed_ns": completed,
              "cpu_before": before, "cpu_after": after, "cpu": accounted,
              "recorded_requests": len(rows), "not_completed_or_unrecorded": missing}
    write(output / "measurement.json", result)
    return result
