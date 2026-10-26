# Follow-up correctness on the current text-reuse source

The optional follow-ups were derived again from the current text tokenization PR, preserving its update to main and reasoning-effort regression test. Both received fresh CPU, pre-commit and real GPU serving checks. This updates the source and correctness evidence; it does not update the earlier performance measurements.

| Scope | Source | Parent | Fresh validation |
|---|---|---|---|
| Text tokenization reuse | `045e9051b` | main `85e199e60` | [368 CPU tests and 36 serving requests](../v1/main-update-20261026/README.md) |
| Add block-hash reuse | `813ade25f` | `045e9051b` | 397 CPU tests, 72 text requests, 9 image fallback requests |
| Add image compatibility | `4327e413c` | `813ade25f` | 405 CPU tests, 72 text requests, 60 valid image requests, 8 invalid requests, 12 lifecycle requests |

The [hash increment](https://github.com/RichealYoung/vllm/compare/045e9051b2c8c93e90aed3e30516855edc57d99d...813ade25f0fdecb93a1ab0547f362c1b0404aa37) changes 18 files; the [image increment](https://github.com/RichealYoung/vllm/compare/813ade25f0fdecb93a1ab0547f362c1b0404aa37...4327e413c12ca9c3a066035f827d5f1c9bb5487a) changes 10. Git range comparisons confirm the two feature increments match their earlier versions, while their ancestry now includes the current text PR.

The `token_lcp` helper was rebuilt through the current source's CMake target, checked to expose only that API, and used by both follow-ups. Applicable hooks passed without changing either source. Existing GPU extensions and dependencies were reused after source and binary identity checks; this is not a clean installation or validation of every backend.

Text serving checks compare complete prompt IDs, token counts and generated output/logprobs with normal computation and require actual reuse. Image serving uses four combinations: neither feature, tokenization reuse, hash reuse, and both. All 72 independently observed image-request hash chains matched normal computation, with exact expected reused-block counts. The hash-only follow-up's 9 image requests used normal hashing with no reused blocks. Both jobs exited successfully with no remaining processes.

Models and runtime match the existing correctness setup: RTX 3090, PyTorch 2.14.0+cu130, Transformers 5.20.2, tokenizers 0.23.2; Qwen3-0.6B, Llama-3.2-1B and Qwen2.5-VL-3B-Instruct at the recorded fixed revisions. CPU/hooks took about 21 minutes and GPU correctness about 50 minutes. These durations are test-run costs, not serving performance results.

[Acceptance and exact source identities](acceptance.json), [raw logs, commands, responses and JUnit records](evidence-portable.tar.gz), and [207 file hashes](file-sha256.json) are available together. Archive SHA256: `1311a5792645c53ba3c6f8d55b8c77ca22d7db1ae794fb1dab45dbb21f97be24`. All 207 files were verified after download. File links used by test fixtures are stored as ordinary bytes for portability.

To rerun, use the CPU/serving commands in the source tree at the corresponding commit. The image stage replaces the image-fallback CPU suite with its real-processor tests in `tests/renderers/test_session_prefix.py`; the hash stage includes `tests/renderers/test_session_prefix_media_fallback.py`. The source's Buildkite commands select these paths. The independent image-hash observer and its assertions are included in the archive; they add diagnostic work and must not be used for performance timing.

The original `be08fa535` performance experiment, inputs, raw results and patches remain unchanged. No new-main latency benefit or image-workload speedup is claimed by these correctness checks. The original combined implementation and previous follow-up commits remain available in the fork.
