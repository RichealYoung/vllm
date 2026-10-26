# Replay script validation

Validated on 2026-10-26, using a fresh Python 3.12.3 client environment and separate server installation layouts. The public `serve.py`, `replay_client.py` and `summarize.py` entry points were used without the original experiment framework's Python path or activation scripts.

| Workload | Baseline | Token reuse |
|---|---|---|
| Growing histories | 80 requests + 8 warmups passed | 80 requests + 8 warmups passed; actual prefix reuse confirmed |
| Independent requests | 80 requests + 8 warmups passed | 80 requests + 8 warmups passed; no reused tokenization history |

All 320 requests and 32 warmups passed HTTP/SSE completion, fixed input/output lengths, native cached-token fields and scheduling checks. Each client's 20 requests remained in order. API server CPU snapshots were collected, both workloads' native cached-token counts matched by request between conditions, and all four services exited without remaining owned processes.

Six groups of CPU checks covered complete request payloads, both workloads, warmup/reset order, four queues, first non-empty output, HTTP/SSE errors, missing fields, wrong lengths, reset rejection, timeout, bad input and preservation of existing output directories. These include ten HTTP/SSE/reset failure scenarios. All passed. The summary command also regenerated the published table from the supplied original data.

The client environment used httpx 0.28.1 and psutil 7.2.2; all resolved dependencies are pinned in `client/requirements.txt` and listed in the [machine-readable report](replay-validation.json). The servers used PyTorch 2.14.0/CUDA 13.0, Transformers 5.20.2, tokenizers 0.23.2 and Hub 1.31.0, with Qwen3-0.6B at revision `c1899de289a04d12100db370d81485cdf75e47ca` on an RTX 3090.

Existing server dependency files, native builds, compiler tools and model assets were reused after hash checks. This is not a from-scratch GPU-stack installation test. The checks exposed two missing prerequisites in the isolated layout—vLLM package metadata and the ninja executable—which were corrected without changing the token reuse implementation. The public launcher now adds the selected server Python's `bin` directory to PATH.

DEBUG logs were enabled to confirm actual tokenization reuse. These four runs validate the public entry points and their output; their timings are not a replacement for the published performance experiment. [Validation records](validation/) are kept separately from the original [performance results](results/). Author-specific paths are replaced in distributed JSON copies, and original/distributed hashes are recorded in the report. Hash reuse and image handling were not part of this new check.
