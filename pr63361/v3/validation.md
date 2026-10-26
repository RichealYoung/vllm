# Image compatibility validation

The current source, `4327e413c`, derives from the current hash follow-up at `813ade25f`, whose parent is the text PR at `045e9051b`. Fresh validation passed 405 CPU tests and 72 real text requests. Image checks included 60 valid requests, 8 invalid requests and 12 lifecycle requests, plus 72 complete native-hash observations. These are different correctness checks, not independent performance samples.

Real image serving compared normal processing, tokenization reuse, hash reuse and both features together. Complete native hashes and expected reused-block counts matched in all four groups. CPU tests covered real processors, generated boundary cases, invalid input and discarded entries after failures. [Current source identities and acceptance records](../followups-current-text-20261026/README.md) include the commands, raw results and file hashes.

The CPU/GPU suites and applicable pre-commit checks were actually rerun on this source, using a matching rebuilt `token_lcp` helper. Both jobs exited successfully without remaining processes. [Earlier frozen-source checks](../identities/final-functional-acceptance.json), [earlier correctness acceptance](../identities/r5-correctness-acceptance.json) and [measured build information](../identities/measured-V3.json) remain separate historical records.

Real processor tests and lightweight library compatibility checks serve different purposes. A primary tested environment should exercise actual reuse; unsupported dependencies should check warnings and safe fallback. Additional processor/version combinations can be optional, while dependency upgrades must still expose whether reuse remains enabled.

The separate public replay-client check covers tokenization reuse on text requests only; this follow-up's fresh image correctness evidence is linked above. Performance figures remain from the frozen `be08fa535` experiment and were not rerun on the updated source. Publishing a standalone PR still needs human review and validation on its eventual head if it changes. No image-workload speedup or clean GPU-stack installation is claimed.
