# Tokenization reuse: performance results

Qwen3-0.6B on an RTX 3090, FP16, four concurrent clients, with prefix caching, chunked prefill and CUDA graphs enabled. Each configuration has four fresh-server runs of 80 requests for each workload. The CPU budget for cached text and token IDs is 512 MiB.

| Metric | Baseline | Token reuse | Result |
|---|---:|---:|---|
| Growing histories: frontend CPU time/request | 389.5 CPU-ms | 291.7 CPU-ms | −25.1% |
| Growing histories: mean time to first output | 641.1 ms | 515.3 ms | −19.7%; runs −27.0% to −2.2% |
| Growing histories: mean end-to-end latency | 8.391 s | 8.306 s | approximately −1.0% |
| Independent requests: mean time to first output | 99.7 ms | 98.0 ms | runs −9.5% to +10.9%; no consistent gain |
| Independent requests: P95 time to first output | 133.9 ms | 137.1 ms | tail latency increased |

Growing histories contain 16,402–34,832 input tokens and generate 448 tokens. Independent requests contain 512/1024/2048 input tokens and generate 64 tokens. These are fixed synthetic chat histories, not live coding-agent tasks.

Time to first output is measured from client request start to the first non-empty streamed output chunk. CPU time/request is the API server process CPU increment divided by 80. Percentages average changes between matched baseline and reuse runs; the displayed P95 values average four run P95s. Four complete pairs, not individual requests, are the repeats.

Clients send the next request when the previous response finishes. Gains vary substantially between runs and are not guaranteed for other arrival patterns. Reported prefix-cache hit token counts matched request by request. No significance, production capacity or multimodal performance claim is made.

<details>
<summary>Run variation and additional analysis</summary>

The four changes in mean time to first output were −27.036%, −24.467%, −25.000% and −2.166%. The last run still reduced API server CPU time by 28.0%. A later inspection found different client-start synchronization patterns across runs. This is correlation, not a direct measurement of server arrival or queue waiting and not proof of the latency mechanism. All runs, including adverse results, were retained.

[Analysis data](../performance/results/posthoc-alignment-review-001.json) and [per-request records](../performance/results/runs-001/) preserve the observations. CPU time is not an isolated tokenizer-function measurement.

</details>

The two benchmark builds use base `be08fa5355a049b838803540211fed5647490b39` plus the same [shutdown patch](../prerequisites/benchmark-shutdown.patch). The tokenization implementation matches the code under review. [Source and build information](../identities/versions.json) distinguishes the measured source from later test/documentation changes.

## Reproduce or inspect the results

- [Run the replay](../performance/REPRODUCTION.md).
- [Regenerate the table from the supplied data](../performance/REPRODUCTION.md#regenerate-the-published-table).
- [Download the fixed inputs](../performance/workload-v1.json) and browse [raw results](../performance/results/).
- [See the replay script validation](../performance/replay-validation.md). That check validates the public entry points; it is separate from the four-repeat performance experiment above.
