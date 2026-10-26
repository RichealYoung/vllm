# Image compatibility validation

The earlier tested source passed 403 CPU tests and 72 real text requests. Image checks included 60 valid requests, 8 invalid requests and 12 lifecycle requests, plus 72 complete native-hash observations. These are different correctness checks, not independent performance samples.

Real image serving compared normal processing, tokenization reuse, hash reuse and both features together. CPU tests covered real processors, generated boundary cases, invalid input and discarded entries after failures. [Acceptance records](../identities/r5-correctness-acceptance.json) give the test selections and results.

The final source was reassembled and passed source-hash/pre-commit checks; its CPU/GPU tests were not rerun. [Final source checks](../identities/final-functional-acceptance.json) and [measured build information](../identities/measured-V3.json) distinguish these scopes.

Real processor tests and lightweight library compatibility checks serve different purposes. A primary tested environment should exercise actual reuse; unsupported dependencies should check warnings and safe fallback. Additional processor/version combinations can be optional, while dependency upgrades must still expose whether reuse remains enabled.

The new public replay validation covers tokenization reuse on text requests only. Publishing this follow-up separately requires validation on its chosen head and vision assets; no new image correctness or performance result is claimed by the replay-script check.
