# Optional follow-up: block-hash reuse

This follow-up reuses previously computed prompt block hashes as well as tokenized text. It compares exact token IDs with the previous prompt selected by the agent hint, then resumes normal hashing at complete validated blocks. It does not retain physical KV blocks or change their cache policy. Hash state, model-weight version, cache salt and reset boundaries keep histories separate; unsupported requests use normal hashing.

`--session-hash-cache-mb` sets a separate CPU memory budget, default zero. The implementation uses the native `token_lcp` helper to compare long Python integer lists. If the helper is unavailable, it warns and disables hash reuse; tokenization reuse remains available independently.

## Why a native helper is proposed

The [historical Python/list/array/C comparison](historical-match/README.md) includes method sources and raw results. It measured matching plus block hashing on an earlier CPU/source version, not current end-to-end serving or history storage. It supports the design rationale, not a claim that C is the only acceptable implementation. In particular, converting both lists to arrays has a cost, and `array('q')` does not enforce the same strict integer-type/range checks.

A separate [native/Python token-memory-size comparison](accounting-paired-summary.json) tested the tokenization implementation on short independent requests: four pairs of runs, 640 measured requests. Python minus native mean time-to-first-output changes were −4.157,+4.575,+1.943,+2.396 ms. These mixed results did not justify adding a native memory-size helper to tokenization reuse. That experiment does not establish whether `token_lcp` is needed for hash reuse.

## Existing serving results

For growing histories, adding hash reuse changed mean time to first output from 515.324 to 421.757 ms. The mean paired change was −16.977%, ranging from −32.612% to −11.021%; end-to-end latency changed only −0.116%. Combined tokenization and hash reuse improved time to first output by 34.219% against the baseline. This combined benefit must not be attributed to tokenization reuse alone. Short-request changes varied in direction.

[Validation](validation.md), [incremental source patch](../patches/current-main/text-to-hash.patch), [complete performance result data](../performance/results/summary-001.json).
