"""Artifact integrity and measurement contract; no vLLM imports."""
import hashlib
import json
from pathlib import Path

from . import VERSION


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def seal(payload):
    return {"payload": payload, "sha256": digest(payload)}


def unseal(path):
    obj = read(path)
    if digest(obj["payload"]) != obj["sha256"]:
        raise ValueError(f"Artifact hash mismatch: {path}")
    return obj["payload"]


CONTRACT = {
    "version": VERSION, "seed": 42, "lanes": 4, "requests": 80,
    "request_deadline_s": 180, "batch_deadline_s": 3600,
    "coding": {"sessions": 4, "turns": 20, "system": 2048,
               "private": 13824, "delta": 512, "output": 448},
    "independent": {"system": 256, "inputs": [512, 1024, 2048],
                    "counts": [20, 40, 20], "output": 64},
    "sampling": {"temperature": 0, "top_p": 1, "seed": 42,
                 "ignore_eos": True, "stop": [],
                 "chat_template_kwargs": {"enable_thinking": False}},
    "metrics": ["first_output_chunk_s", "http_e2e_s", "batch_s",
                "server_cpu_seconds_per_request"],
    "warmup": {"long": 4, "short": 4},
}


def validate_workload(data):
    if data["contract"] != CONTRACT or data["contract_sha256"] != digest(CONTRACT):
        raise ValueError("Workload contract differs from this framework")
    for name in ("coding", "independent"):
        lanes = data["workloads"][name]
        if len(lanes) != 4 or any(len(lane) != 20 for lane in lanes):
            raise ValueError("Expected 4 frozen queues of 20 requests")
        requests = [r for lane in lanes for r in lane]
        ids = [r["id"] for r in requests]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate request identity")
        expected_output = CONTRACT[name]["output"]
        for lane_id, lane in enumerate(lanes):
            for index, row in enumerate(lane):
                if (row["lane"] != lane_id or row["index"] != index
                        or row["output_tokens"] != expected_output
                        or row["input_tokens"] < 1 or not row["messages"]):
                    raise ValueError("Invalid request contract")
            sessions = [r["session_id"] for r in lane]
            if name == "coding" and len(set(sessions)) != 1:
                raise ValueError("Coding session changed mid-conversation")
        sessions = [r["session_id"] for r in requests]
        if name == "independent" and len(set(sessions)) != 80:
            raise ValueError("Independent tasks share a session")
        if name == "coding" and len(set(sessions)) != 4:
            raise ValueError("Coding needs four distinct sessions")
    return data
