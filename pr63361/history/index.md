# Evidence history

The original complete implementation at `580cf373d7af587f845e518650aef74744dfa359` is preserved. Later preparation separated text tokenization reuse from optional hash reuse and image support. Source revisions and file hashes distinguish these snapshots.

The current review chain is `045e9051b → 813ade25f → 4327e413c`, with [fresh correctness evidence for the follow-ups](../followups-current-text-20261026/README.md). The earlier published chain `97e901c7 → 6360b1aa → f9732fa7` remains available as historical snapshots; it is no longer the current comparison chain. The performance results still use the original `be08fa535` setup and were not rerun after the main update. The bullets below describe the earlier stages.

- Earlier correctness tests covered tokenization, hashing, image compatibility and library combinations. The final tokenization-only source then passed a fresh 366-CPU-test/36-serving-request check. Optional follow-ups received source-hash and pre-commit checks, without new GPU runs.
- The full performance experiment contains 32 instances, 2,560 measured requests and 256 warmups, with four matched pairs per workload. All runs were retained, including adverse short-request tails and the small latency improvement in the last tokenization-only pair.
- A separate native/Python token-storage-size comparison had mixed short-request results and did not establish a reason to add a native helper to tokenization reuse.
- Later CPU/client-start analysis used existing records only. It did not profile queue waiting or prove a causal latency mechanism.
- Public replay entry points were checked in a fresh client environment and against four real servers: 320 requests plus 32 warmups. This validates usability; it does not replace the original performance results.

Each benchmark condition used the same independent shutdown patch. The code under review excludes that unrelated patch. Final test/documentation cleanup did not change token reuse product code; measured and reviewed source hashes remain available.

Failed preparation and installation attempts are retained in the author's complete records. Original data is not overwritten by corrected summaries or replay validation. Similar combined speedup percentages from different experiments are not interchangeable and are not tokenization-only claims. Image CPU diagnostics do not establish multimodal serving speedup.
