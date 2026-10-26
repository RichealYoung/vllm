# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""HTTP subset of the adapter used in M2; no installation/launcher dependency."""
from .common import CONTRACT


def payload(row, model, namespace, diagnostic=False):
    if diagnostic:
        raise ValueError("Diagnostics are excluded from this replay entry point")
    result = dict(CONTRACT["sampling"])
    result.update(model=model, messages=row["messages"],
                  max_tokens=row["output_tokens"], stream=True,
                  stream_options={"include_usage": True})
    if namespace != "warmup":
        result["session_id"] = f"{namespace}:{row['session_id']}"
    return result


def handle_event(event, state):
    if "error" in event:
        raise ValueError(f"Server SSE error: {event['error']}")
    if event.get("usage"):
        state["usage"] = event["usage"]
    if event.get("prompt_token_ids") is not None:
        if "prompt_token_ids" in state:
            raise ValueError("Repeated prompt IDs")
        state["prompt_token_ids"] = event["prompt_token_ids"]
    visible = False
    for choice in event.get("choices", []):
        delta = choice.get("delta", {})
        tool_text = any(call.get("function", {}).get("arguments")
                        or call.get("function", {}).get("name")
                        for call in delta.get("tool_calls", []))
        visible |= bool(delta.get("content") or delta.get("reasoning_content")
                        or delta.get("reasoning") or tool_text)
        if choice.get("finish_reason") is not None:
            state["finish_reason"] = choice["finish_reason"]
    return visible


async def reset(client):
    response = await client.post("/reset_prefix_cache")
    response.raise_for_status()
    if response.json().get("success") is not True:
        raise RuntimeError("Prefix reset refused; no measurement started")
