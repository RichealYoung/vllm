# Correctness after the accounting update

Commit [04d5f00e8bf6836c3a4ead37e9ec7dc04ec68ee8](https://github.com/RichealYoung/vllm/commit/04d5f00e8bf6836c3a4ead37e9ec7dc04ec68ee8), Git tree `538920299a37ccd572c2a5ca2d882958ff9fb9a2`, follows [045e9051b](../main-update-20261026/README.md) on the same main `85e199e60ca87a4b136aeaa0842541139b94c778`. It changes four files ([incremental patch](../../patches/current-main/text-accounting.patch)):

- Each stored prompt records a validated upper bound of its token IDs. Whole-prompt hits reuse it, and prefix hits check only the newly tokenized suffix. The memory charge therefore no longer rescans the whole prompt. Lists that cannot be validated keep the original full scan. The charge is never lower than before, and it is identical when all IDs are below 2^30.
- The tokenizer compatibility check ignores the truncation and padding state left by an earlier call, which Transformers resets on every call. Previously, a tokenizer used with truncation before the cache was created was rejected.

| Check | Result |
|---|---|
| CPU suite, including media fallback | 371 passed (368 earlier tests plus 3 new); no failures, errors or skips |
| Existing reasoning/render-parity and CLI tests | 19 passed |
| Mapping regression with the mapping deliberately removed | Failed as expected |
| Applicable pre-commit checks | 18 passed; no source changes made by hooks |
| Real text serving | 4 cases, 36 requests passed: Qwen3 and Llama, reuse off/on |

The commands, runtime, compiled libraries and models are those of the [previous correctness checks](../main-update-20261026/README.md). The candidate was that accepted source tree with the four changed files replaced and checked against their committed hashes. All tests ran on the server; these are correctness checks, not new performance measurements or upstream CI results.

New tests check that whole-prompt and prefix hits charge exactly the full-scan size and return the normal token IDs, that a validated bound matches a full scan, and that a tokenizer used with truncation and padding is still accepted. On the previous source, the two new renderer tests failed for the expected reasons.

A CPU component measurement on 80 fixed growing-history requests (Qwen3 tokenizer) compared the two sources in three interleaved rounds. It used the change before the formatting-only amendment described below. The median prefix-hit encoding time changed from 2.96–3.23 ms to 2.24–2.29 ms, a paired change of −0.73 to −0.89 ms per request. Full tokenization of the same prompts took about 50 ms. Requests with no reusable prefix showed no consistent change. This affects about 0.3% of the reported frontend CPU time per request, so the [performance results](../benchmark.md) were not rerun. They still describe their original frozen source.

[Acceptance record](acceptance.json), [raw logs, commands and JUnit results](evidence-portable.tar.gz) and [file hashes](file-sha256.json) are available together. The archive's SHA256 is `00ad393cb5f56c0008934b7686ced62cfb29ec6a835b3dfea87c722eda5a2ddd`.

<details>
<summary>Failed first attempt</summary>

The first run stopped at the pre-commit checks before any test ran. Formatting, line length and three type annotations in the new lines did not pass. The commit was amended without changing behavior, and every check above was then rerun on the amended source. The [first attempt's evidence](evidence-attempt1-hooks-failed.tar.gz) is retained.

</details>
