# Follow-up: reuse prompt block hashes across session turns

This optional follow-up builds on [tokenization reuse (PR #63361)](https://github.com/vllm-project/vllm/pull/63361). It is not part of that PR.

## Overview

After tokenization, EngineCore still computes the prefix-cache hash of every complete prompt block, even when most of the prompt repeats the previous turn. This follow-up keeps the previous prompt's token IDs and block hashes for each session. For a new request with the same `session_id`, EngineCore compares the token IDs exactly, reuses the hashes of matching complete blocks, and continues the normal hash chain for the remaining blocks. KV-cache lookup, cache policy and physical KV blocks are unchanged.

## Claims

- Opt-in, with a separate CPU memory budget (`--session-hash-cache-mb`, default 0). It can be enabled with or without tokenization reuse.
- EngineCore checks the token IDs itself and does not trust the frontend's match. Cache salt, resets and model-weight updates keep histories separate. Unsupported requests, such as LoRA, prompt embeddings or multimodal inputs, use normal hashing.
- On growing chat histories, adding hash reuse to tokenization reuse reduced mean time to first output by **17.0%** on average across four pairs of runs. End-to-end latency changed by about **−0.1%**.
- The [final text evaluation](final-text-evaluation-20261030/README.md) measured both mechanisms together on the current source against the baseline. Mean time to first output fell **31.5%** on synthetic growing histories and **30.3%** on replayed real coding-agent trajectories. Hash reuse cut EngineCore request preprocessing from 13.9 to 4.3 ms. With no usable history, the combination was 4.6% slower.

## Validation

The performance measurements below use the earlier frozen `be08fa535` source; they were not rerun after updating to main. Current-source results for tokenization and hash reuse together are in the [final text evaluation](final-text-evaluation-20261030/README.md); the incremental effect of hash reuse alone was not remeasured. Setup: Qwen3-0.6B on an RTX 3090, four concurrent clients, four fresh-server runs of 80 requests per configuration.

| Metric | Token reuse | Token + hash reuse | Result |
|---|---:|---:|---|
| Growing histories: mean time to first output | 515.3 ms | 421.8 ms | −17.0%; individual runs −32.6% to −11.0% |
| Growing histories: P95 time to first output¹ | 654.9 ms | 539.5 ms | lower |
| Growing histories: mean end-to-end latency | 8.306 s | 8.296 s | about −0.1% |
| Independent requests: mean time to first output | 98.0 ms | 97.7 ms | individual runs −11.7% to +8.0% |

¹ Mean of the four run P95s. Percentages average the relative changes between matched runs.

The largest change (−32.6%) comes from the run pair in which the tokenization-only server's four clients stayed synchronized and showed almost no gain over the baseline; the other three pairs ranged from −13.0% to −11.0%. Clients send their next request when the previous response finishes, so latency depends on how requests line up and should not be assumed for other arrival patterns. EngineCore process CPU time did not show a clear decrease in these runs.

Against the baseline without any reuse, tokenization plus hash reuse reduced mean time to first output by 34.2% (runs −35.2% to −32.8%) and end-to-end latency by about 1.1%. This combined result must not be attributed to tokenization reuse alone.

Correctness on the updated source: 397 CPU tests, 72 requests to running Qwen3 and Llama servers, and 9 image requests checking normal-processing fallback passed. Complete token IDs and complete block hashes from normal computation are the references; tests also confirm actual reuse and cover hash-state resets and memory limits. The native helper was rebuilt and applicable pre-commit checks passed. See [validation details](validation.md).

## Details

- A native helper, `token_lcp`, compares long token-ID lists. If it is unavailable, hash reuse warns and stays disabled while tokenization reuse keeps working. See [why a native helper is proposed](design.md#why-a-native-helper-is-proposed) and the [historical comparison](historical-match/README.md).
- Each EngineCore keeps at most one previous prompt per session and cache salt. Histories store token IDs and hashes only; they never hold KV blocks.
- Results come from one model and one GPU. A standalone PR would need human review, a matching helper build and validation on its own head.

## Code

- [Incremental changes: token reuse → hash reuse](https://github.com/RichealYoung/vllm/compare/045e9051b2c8c93e90aed3e30516855edc57d99d...813ade25f0fdecb93a1ab0547f362c1b0404aa37)
- Evaluated final text version: [source `797e19367`](https://github.com/RichealYoung/vllm/tree/797e19367fa3ce44c48f9579f474753e861247d0), the same hash reuse patch on the current PR head plus [suffix-only hash accounting](../patches/current-main/hash-accounting.patch) · [changes from the PR head](https://github.com/RichealYoung/vllm/compare/04d5f00e8bf6836c3a4ead37e9ec7dc04ec68ee8...797e19367fa3ce44c48f9579f474753e861247d0)
- [Full source snapshot](https://github.com/RichealYoung/vllm/tree/813ade25f0fdecb93a1ab0547f362c1b0404aa37) · [patch](../patches/current-main/text-to-hash.patch) · [raw performance results](../performance/results/summary-001.json)
- Next: [image compatibility](../v3/README.md)
