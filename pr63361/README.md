# Tokenization reuse for chat sessions

> Source snapshots for tokenization reuse and optional follow-ups are linked below. Each source commit's Git tree matches the corresponding validated tree recorded with the test evidence.

Successive chat turns often resend most of the previous conversation. This feature uses an agent hint, the existing `session_id`, to select the previous rendered prompt, reuse token IDs for its unchanged prefix, and tokenize only the remaining suffix. Text comparison and tokenizer compatibility checks determine whether reuse is safe.

- [Run the baseline and token reuse comparison](performance/REPRODUCTION.md).
- [Performance results and limitations](v1/benchmark.md).
- [How reuse works](v1/design.md) and [correctness tests](v1/validation.md).
- [Benchmark inputs](performance/workload-v1.json), [raw results](performance/results/), and [measurement protocol](performance/protocol.md).

The replay scripts have been checked in a fresh client environment and against running Qwen3 servers, with reuse disabled and enabled. See [what was validated](performance/replay-validation.md). Existing server dependencies, compiled libraries and model files were reused; this does not certify a from-scratch installation of the GPU software stack.

The default instructions cover tokenization reuse. Optional follow-ups describe [block-hash reuse](v2/README.md) and [image compatibility](v3/README.md). Their combined results are not attributed to tokenization reuse.

| Scope | Source snapshot | Incremental review |
|---|---|---|
| Text tokenization reuse | [Source](https://github.com/RichealYoung/vllm/tree/97e901c7f00b6d14f538400e0be57c7e67bcefd8) | [Upstream → token reuse](https://github.com/RichealYoung/vllm/compare/be08fa5355a049b838803540211fed5647490b39...97e901c7f00b6d14f538400e0be57c7e67bcefd8) |
| Add block-hash reuse | [Source](https://github.com/RichealYoung/vllm/tree/6360b1aa9473faf377fa0c383c14ad6a53fac587) | [Token reuse → hash reuse](https://github.com/RichealYoung/vllm/compare/97e901c7f00b6d14f538400e0be57c7e67bcefd8...6360b1aa9473faf377fa0c383c14ad6a53fac587) |
| Add image compatibility | [Source](https://github.com/RichealYoung/vllm/tree/f9732fa728c5f7507373f0790ce8a1f6babc64fa) | [Hash reuse → image compatibility](https://github.com/RichealYoung/vllm/compare/6360b1aa9473faf377fa0c383c14ad6a53fac587...f9732fa728c5f7507373f0790ce8a1f6babc64fa) |

Source revisions, build information and file hashes are in [versions.json](identities/versions.json). The original implementation at `580cf373d7af587f845e518650aef74744dfa359` and its evidence are preserved.
