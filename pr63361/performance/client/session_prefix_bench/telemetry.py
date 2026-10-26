"""Diagnostic Prometheus samples; missing observations fail closed."""
import asyncio
import json
import time

KEYS = {"running": "vllm:num_requests_running",
        "waiting": "vllm:num_requests_waiting",
        "kv_fraction": "vllm:kv_cache_usage_perc",
        "preemptions": "vllm:num_preemptions_total"}


async def sample(client, output, label):
    response = await client.get("/metrics")
    response.raise_for_status()
    raw = response.text
    values = {key: [] for key in KEYS}
    for line in raw.splitlines():
        if not line or line.startswith("#"):
            continue
        name = line.split("{", 1)[0].split(" ", 1)[0]
        for key, expected in KEYS.items():
            if name == expected:
                values[key].append(float(line.split()[-1]))
    if any(not items for items in values.values()):
        (output / f"missing-metrics-{label}.txt").write_text(raw)
        raise RuntimeError(f"Required metric absent: {values}")
    result = {key: sum(items) for key, items in values.items()}
    result.update(time_ns=time.time_ns(), label=label)
    if not 0 <= result["kv_fraction"] <= 1:
        raise RuntimeError("Invalid KV utilization")
    with (output / "metrics.jsonl").open("a") as stream:
        stream.write(json.dumps(result) + "\n")
    if label in ("before", "after"):
        (output / f"metrics-{label}.txt").write_text(raw)
    return result


async def monitor(client, output):
    while True:
        await sample(client, output, "during")
        await asyncio.sleep(0.5)


async def idle(client, output, label, empty_kv=False):
    for _ in range(30):
        result = await sample(client, output, label)
        if (result["running"] == result["waiting"] == 0
                and (not empty_kv or result["kv_fraction"] == 0)):
            return result
        await asyncio.sleep(0.5)
    raise RuntimeError("Requests remain in flight or reset KV is not empty")
