# Measurement protocol

This describes the existing performance experiment, not the later replay-script usability check. Inputs are fixed synthetic conversations assembled once using AIPerf's `SyntheticDatasetComposer` at commit `f7257c900f3d38a3ca1f7ba7f40aca05ffe0123e`. Assistant history is fixed rather than replaced by newly sampled outputs. This is a serving replay, not live execution of an agent task.

## Inputs and execution

Growing histories: four sessions, 20 turns each, 16,402–34,832 input tokens and 448 output tokens. Independent requests: 80 distinct sessions, 512/1024/2048 input tokens in counts 20/40/20, with 64 output tokens. Each of four clients sends its next complete request when the previous response finishes, with no think time.

Qwen3-0.6B on RTX 3090, FP16; maximum model length 40960, four sequences, 4096 batched tokens, 18 GiB KV cache. Native prefix caching, chunked prefill, async scheduling and CUDA graphs remain enabled. Cached text/token IDs have a 512 MiB budget. OMP/MKL threads=1; server logical CPUs 0–11, client 12–13. Sampling: seed 42, temperature 0, top_p 1, ignore_eos enabled, no stop strings, thinking disabled.

Every run starts a new server, warms four long and four short requests without session IDs, resets native KV, verifies idle/empty KV and then processes all 80 requests. No full-ID return, diagnostic hooks, per-token tracing or periodic metric sampling during the measured window. CPU and scheduling metrics are sampled at its boundaries.

## Repeats and recorded order

Four matched pairs are available for each workload. The full experiment also interleaved two optional follow-ups, preserving the order below; they are separate conditions, not parts of the token-only result.

| Repeat | Condition order |
|---|---|
| 1 | Baseline → token reuse → token + hash reuse + image compatibility → token + hash reuse |
| 2 | Token reuse → token + hash reuse → baseline → token + hash reuse + image compatibility |
| 3 | Token + hash reuse → token + hash reuse + image compatibility → token reuse → baseline |
| 4 | Token + hash reuse + image compatibility → baseline → token + hash reuse → token reuse |

Growing-history runs precede independent-request runs. Do not compare absolute latency across workloads. Original records use compact condition identifiers: `N`=baseline, `V1`=token reuse, `V2`=token + hash reuse, `V3`=image-compatible follow-up. These identifiers are retained in filenames so existing hashes and records remain traceable. Reproducing only the default two conditions checks their usability; it does not duplicate the original interleaved schedule.

## Metrics and acceptance

Time to first output: client request start to first non-empty streamed content/reasoning/tool text. HTTP end-to-end: start through stream completion. CPU/request: process CPU increment divided by 80; API server CPU is not isolated tokenizer CPU or request wall time.

Mean/P50/P95 are calculated per run. Percentiles use linear interpolation at position `(n−1)q`; displayed P95 averages four run P95s. Paired percent change is `(reuse−baseline)/baseline`, averaged across four pairs. Four runs, not 320 requests, are the repeat unit. No significance, equivalence, throughput or production SLO claim.

Request deadline: 180 seconds; batch deadline: 3600 seconds. Require successful HTTP/SSE, DONE, non-empty output, finish_reason=length, exact input/output lengths and integer cached_tokens. Missing fields are not zero. Source/model/build drift, preemption, incomplete CPU snapshots or failed requests invalidate the run and preserve its evidence. Ordinary variability and adverse results are retained without retries chosen by effect size.

All published runs passed their checks. Native cached-token counts matched request by request between paired conditions. The two benchmark builds use the same independent shutdown patch; exact source/build hashes and that patch are supplied. [Results](../v1/benchmark.md), [replay instructions](REPRODUCTION.md), [input file](workload-v1.json).
