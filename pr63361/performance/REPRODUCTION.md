# Run the token reuse comparison

The scripts replay the same complete chat requests against a baseline server and a server with tokenization reuse. They accept your model directory and installed server Python paths; no author SSH setup, activation script or experiment framework is required.

## Prerequisites

- Linux with Python 3.12 and `uv`, `taskset` and a working GPU-enabled vLLM installation. The measured setup used an RTX 3090, PyTorch 2.14.0/CUDA 13.0, Transformers 5.20.2, tokenizers 0.23.2 and huggingface-hub 1.31.0.
- Local Qwen3-0.6B model and tokenizer files at revision `c1899de289a04d12100db370d81485cdf75e47ca`.
- Working CUDA compilation tools, including `nvcc` and `ninja`. First-use kernel compilation can make startup take several minutes. The vLLM installation must include its package metadata, not only a directory of Python source files.
- An otherwise idle GPU and enough memory for 18 GiB of KV cache plus model/runtime allocations. Server and client use different logical CPUs; defaults are 0–11 and 12–13. Adapt both consistently if your allowed CPU set differs, and record the change.

[Replay validation](replay-validation.md) records the tested setup. It reused existing dependencies and compiled libraries; a clean GPU-stack installation was not tested.

## Prepare the two source versions

Use two clean checkouts of upstream `be08fa5355a049b838803540211fed5647490b39`. Apply `prerequisites/benchmark-shutdown.patch` to both, and additionally apply `patches/token-reuse.patch` to the token reuse checkout. Install each checkout with vLLM's normal build/install workflow. Keep the materials directory outside both source checkouts.

The shared patch reconstructs the original measurement conditions; it is separate from tokenization reuse. Exact source/build hashes are supplied in [versions.json](../identities/versions.json). The measured feature patch and the final review patch have identical token reuse product code; their tests/documentation differ. The latter is also preserved under `patches/BASE-to-V1.patch`.

## Create the client environment

Set paths for your own machine:

```bash
export REPLAY_MATERIALS=/absolute/path/to/pr63361
export REPLAY_MODEL=/absolute/path/to/Qwen3-0.6B
export BASELINE_PYTHON=/absolute/path/to/baseline/.venv/bin/python
export TOKEN_REUSE_PYTHON=/absolute/path/to/token-reuse/.venv/bin/python

uv venv --python 3.12 .venv-client
uv pip install --python .venv-client/bin/python \
  -r "$REPLAY_MATERIALS/performance/client/requirements.txt"
```

Use `tmux` or an equivalent persistent session for the commands below. Run one service at a time, starting a fresh process for every condition and workload. A KV-cache reset alone does not clear all cached text history.

## Start a server and replay requests

Example: baseline with growing histories. The server stays in the foreground internally; `nohup` keeps it alive across SSH disconnects.

```bash
nohup .venv-client/bin/python "$REPLAY_MATERIALS/performance/client/serve.py" \
  --condition baseline --server-python "$BASELINE_PYTHON" \
  --model-dir "$REPLAY_MODEL" --port 18261 --server-cpus 0-11 \
  > baseline-coding.server.log 2>&1 < /dev/null &
replay_server_pid=$!
printf '%s\n' "$replay_server_pid" > baseline-coding.server.pid
```

Wait until `curl -fsS http://127.0.0.1:18261/health` succeeds, then run:

```bash
taskset -c 12,13 .venv-client/bin/python \
  "$REPLAY_MATERIALS/performance/client/replay_client.py" \
  --url http://127.0.0.1:18261 --case coding \
  --server-pid "$replay_server_pid" --fresh-server-confirmed \
  --output baseline-coding
```

After the client finishes, send SIGTERM to this server PID, wait for it to exit, and preserve both logs and output files. Repeat with a new server using `--condition token-reuse --server-python "$TOKEN_REUSE_PYTHON"`. Repeat both conditions with `--case independent` and new output directories. `serve.py` uses the full argument lists in [server-arguments.json](server-arguments.json), including the 512 MiB token history budget when enabled.

The server is bound to localhost. `VLLM_SERVER_DEV_MODE=1` is set for the test-only prefix-cache reset endpoint. The client checks reset success and idle/empty KV before sending measured requests. Eight warmup requests have no session ID; measured requests carry the fixed agent hints and complete messages. Do not change the inputs or weaken the output-length/cache-field checks to make a run pass.

For a functional check, add `--log-level DEBUG` to the server command and inspect `Session token reuse: route=partial reused_tokens=...` in its log. Use the default INFO level for timing runs. Response `cached_tokens` describes the KV prefix cache, not how much tokenization work was reused.

## Read the output

- `terminal.json`: success/failure and request counts. Failed runs are retained without automatic retries.
- `coding/requests.jsonl` or `independent/requests.jsonl`: per-request time to first output, end-to-end latency, usage and status.
- `CASE/measurement.json`: batch duration and process CPU snapshots. `cpu.seconds.frontend / 80` is API server CPU time per request.
- `CASE/metrics.jsonl`: scheduling/KV-cache checks before and after the request batch.

`--server-pid` must identify the local API server process. Omitting it supports latency-only use and does not reproduce the published CPU metric. Output directories must be new. The client checks HTTP/SSE completion, fixed input/output lengths, first non-empty output, native cached-token fields and preemptions; a passed client record alone does not certify the installed source or server cleanup.

One pair of runs checks usability, not the published effect size. The [measurement protocol](protocol.md) specifies four matched pairs, fresh services and the original condition order. No benefit is guaranteed for a different hardware/model/arrival pattern.

## Regenerate the published table

This reads the supplied existing results and does not start a server or send requests:

```bash
.venv-client/bin/python "$REPLAY_MATERIALS/performance/client/summarize.py" \
  --output recomputed-table
```

It writes `table.md` and `summary.json`, including each paired run's changes. The default report compares only the baseline and token reuse records. [Raw data](results/) also preserves separately labelled follow-up experiments; their combined benefit is not assigned to tokenization reuse.

The input file SHA256 is `935e387020d27548aba5da24c997c9381a03bd4fc8735e3d1ef5e3c2dd44f833`. Original/distributed hashes are recorded in [artifact-provenance.json](../identities/artifact-provenance.json); author-specific paths in JSON copies were replaced without changing measurement values. Models and compiled installations are not bundled.
