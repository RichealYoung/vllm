# Tokenization reuse for chat sessions

> Source snapshots for tokenization reuse and optional follow-ups are linked below. Each source commit's Git tree matches the corresponding validated tree recorded with the test evidence.

Successive chat turns often resend most of the previous conversation. This feature uses an agent hint, the existing `session_id`, to select the previous rendered prompt, reuse token IDs for its unchanged prefix, and tokenize only the remaining suffix. Text comparison and tokenizer compatibility checks determine whether reuse is safe.

The current PR has been updated to main: [text-reuse correctness checks](v1/main-update-20261026/README.md). Both optional follow-ups now derive from that same source and passed [fresh CPU/GPU validation](followups-current-text-20261026/README.md). The performance experiment retains its original frozen source and data.

- [Run the baseline and token reuse comparison](performance/REPRODUCTION.md).
- [Performance results and limitations](v1/benchmark.md).
- [How reuse works](v1/design.md) and [correctness tests](v1/validation.md).
- [Benchmark inputs](performance/workload-v1.json), [raw results](performance/results/), and [measurement protocol](performance/protocol.md).

The replay scripts have been checked in a fresh client environment and against running Qwen3 servers, with reuse disabled and enabled. See [what was validated](performance/replay-validation.md). Existing server dependencies, compiled libraries and model files were reused; this does not certify a from-scratch installation of the GPU software stack.

The default instructions cover tokenization reuse. Optional follow-ups describe [block-hash reuse](v2/README.md) and [image compatibility](v3/README.md). Their combined results are not attributed to tokenization reuse.

| Scope | Source snapshot | Incremental review |
|---|---|---|
| Text tokenization reuse | [Source](https://github.com/RichealYoung/vllm/tree/045e9051b2c8c93e90aed3e30516855edc57d99d) | [Upstream → token reuse](https://github.com/RichealYoung/vllm/compare/85e199e60ca87a4b136aeaa0842541139b94c778...045e9051b2c8c93e90aed3e30516855edc57d99d) |
| Add block-hash reuse | [Source](https://github.com/RichealYoung/vllm/tree/813ade25f0fdecb93a1ab0547f362c1b0404aa37) | [Token reuse → hash reuse](https://github.com/RichealYoung/vllm/compare/045e9051b2c8c93e90aed3e30516855edc57d99d...813ade25f0fdecb93a1ab0547f362c1b0404aa37) |
| Add image compatibility | [Source](https://github.com/RichealYoung/vllm/tree/4327e413c12ca9c3a066035f827d5f1c9bb5487a) | [Hash reuse → image compatibility](https://github.com/RichealYoung/vllm/compare/813ade25f0fdecb93a1ab0547f362c1b0404aa37...4327e413c12ca9c3a066035f827d5f1c9bb5487a) |

Source revisions, build information and file hashes are in [versions.json](identities/versions.json). The original implementation at `580cf373d7af587f845e518650aef74744dfa359` and its evidence are preserved.
