# Historical matching alternatives (2026-10-21)

This is earlier CPU component evidence, not the current PR's end-to-end test.
Input: two Python integer lists and old block hashes. Output: complete native-
compatible block hashes. Fixed SHA-256, block size 16, pure tokens/salt namespace.
All methods include matching/conversion, native Request construction, old-hash
continuation and suffix hashing. Neither snapshot publication nor model/GPU/
scheduler/network work is measured.

4096/16384/65536 tokens × same/append256/head/middle/tail/shorten256; 8 independently
JSON-reconstructed input pairs, 12 warmups, 120 samples, three interleaved method
orders, seed 42. Arrays convert both lists inside the timer. Machine nonexclusive,
Intel Xeon Platinum 8255C CPU48, CPython 3.12.3, gcc11.2, vLLM
`0.32.0.dev0+sim0ba5646e.cu129`; this is not be08's environment.

1,197 boundary checks and 58,320 measured calls matched native full-hash outputs.
Raw [samples](samples.jsonl), [results](results.json), [analysis](analysis.json),
[environment](environment.json), [native fingerprints](expected-native.json),
[method source](run.py), [C source](matcher.c), [build](build.py),
and [analysis method](analyze.py) are supplied. Author paths are substituted;
original/distributed hashes are in artifact provenance. The historical vLLM API
and exact source must be restored to rerun this component experiment; adapting
it to current vLLM is new work, not something this package has executed.

Representative 16K same-input median time (median of three run medians): native
full hashing 6.160 ms, C list unboxing 0.418 ms. Middle edit: 6.150→3.175 ms;
tail edit: 6.118→0.435 ms; head edit: 6.025→6.157 ms, adverse direction. See full
data for Python loop/galloping list/array and packed-word/AVX2 alternatives.
Array conversion plus SIMD did not beat native list unboxing in this experiment;
this does not show the SIMD kernel itself is slow or rule out pre-stored arrays
under a different memory/input contract. Reused inputs are relatively warm.

No claim of significance, universal C necessity, or current-head E2E benefit
follows from these historical three-repeat component results.
