# Block-hash reuse validation

The earlier tested source passed 395 CPU tests, 72 real text requests and 9 real image requests checking normal-processing fallback. Full token IDs and complete hashes from normal computation are the correctness references. Tests check actual reuse, hash/reset isolation and memory limits. The native helper exposes `token_lcp` only.

The final source was reassembled from the tokenization-only version and passed file-hash and pre-commit checks. Its CPU/GPU suites were not rerun; product code matches the previously tested source. This is not a new execution of 395 tests or 81 requests.

[Earlier acceptance records](../identities/r5-correctness-acceptance.json) contain test selections/results. [Final source checks](../identities/final-functional-acceptance.json) describe the later scope; [measured build information](../identities/measured-V2.json) records source/native hashes. The generated package version label is not the source revision.

A future standalone PR needs human review, a matching helper build and affected validation on its selected head. The public replay validation covers tokenization reuse only; it does not newly validate this follow-up or a clean native build.
