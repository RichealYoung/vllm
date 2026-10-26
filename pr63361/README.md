# Tokenization reuse for chat sessions

> Review snapshot: these materials describe a proposed tokenization-only scope and optional follow-ups for PR #63361. The existing PR is unchanged; use the source revisions recorded here to identify each tested version.

Successive chat turns often resend most of the previous conversation. This feature uses an agent hint, the existing `session_id`, to select the previous rendered prompt, reuse token IDs for its unchanged prefix, and tokenize only the remaining suffix. Text comparison and tokenizer compatibility checks determine whether reuse is safe.

- [Run the baseline and token reuse comparison](performance/REPRODUCTION.md).
- [Performance results and limitations](v1/benchmark.md).
- [How reuse works](v1/design.md) and [correctness tests](v1/validation.md).
- [Benchmark inputs](performance/workload-v1.json), [raw results](performance/results/), and [measurement protocol](performance/protocol.md).

The replay scripts have been checked in a fresh client environment and against running Qwen3 servers, with reuse disabled and enabled. See [what was validated](performance/replay-validation.md). Existing server dependencies, compiled libraries and model files were reused; this does not certify a from-scratch installation of the GPU software stack.

The default instructions cover tokenization reuse. Optional follow-ups describe [block-hash reuse](v2/design.md) and [image compatibility](v3/design.md). Their combined results are not attributed to tokenization reuse.

Source revisions, build information and file hashes are in [versions.json](identities/versions.json). The original implementation at `580cf373d7af587f845e518650aef74744dfa359` and its evidence are preserved.
