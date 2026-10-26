# Block-hash reuse validation

The current source, `813ade25f`, derives from the current text PR at `045e9051b`. Fresh validation passed 397 CPU tests, 72 real text requests and 9 real image requests checking normal-processing fallback. Full token IDs and complete hashes from normal computation are the correctness references. Tests check actual reuse, hash/reset isolation and memory limits. The rebuilt native helper exposes `token_lcp` only; applicable hooks passed without modifying source.

These CPU/GPU suites were actually rerun, including normal hashing for all 9 image requests and exact complete-hash checks. Both managed jobs exited successfully without remaining processes. [Source identities, commands, logs and complete results](../followups-current-text-20261026/README.md) distinguish this run from the earlier source's 395-test acceptance.

[Earlier acceptance records](../identities/r5-correctness-acceptance.json) remain available. [Earlier frozen-source checks](../identities/final-functional-acceptance.json) and [measured build information](../identities/measured-V2.json) retain the original source/native hashes. The generated package version label is not the source revision. Performance data remains from the frozen `be08fa535` experiment and was not rerun on this updated source.

A future standalone PR still needs human review and validation on its eventual head if it changes. This run rebuilt the helper and reused identified GPU libraries and dependencies; it is not a clean GPU-stack installation. The separate public replay-client check covers tokenization reuse only.
