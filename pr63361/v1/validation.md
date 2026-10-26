# Token reuse validation

The code under review passed 366 CPU tests, applicable pre-commit checks and 36 requests to running Qwen3/Llama servers with reuse enabled and disabled. Tests compare complete prompt token IDs, reported token counts and generated outputs, and confirm whole-prompt and prefix reuse. They cover compatibility checks, edited histories, memory limits, shared entries, cancellation, reset and normal processing of requests containing media.

The CPU and serving test commands are included in the PR description and in the source tree. Historical compatibility checks cover 182 lightweight cases across 14 library combinations. Those library checks were not rerun on the final tree; the relevant product modules have matching file hashes.

Separately, the public replay scripts passed CPU HTTP checks and four real-server runs: baseline/reuse × growing histories/independent requests, 320 requests plus 32 warmups. Their test scope, runtime versions and limitations are in [replay validation](../performance/replay-validation.md). They confirm that the public entry points work; they do not replace the four-repeat performance data or constitute upstream CI results.

<details>
<summary>Source and evidence mapping</summary>

[Final functional acceptance](../identities/final-functional-acceptance.json) identifies the reviewed source. [Earlier correctness evidence](../identities/r5-correctness-acceptance.json) includes the historical dependency checks. [Source/build files](../identities/) distinguish actual runs from evidence associated through unchanged file hashes. Git tree IDs in those records describe file content, not published commit IDs.

Earlier performance builds also carry the same independent shutdown patch on both sides. This patch is excluded from the code under review. Test/documentation cleanup did not change token reuse product code; the exact source snapshots and both patch forms remain available. Author validation does not mean upstream CI has passed.

</details>
