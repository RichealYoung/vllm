# Correctness after updating to main

The text tokenization reuse change was updated to main `85e199e60ca87a4b136aeaa0842541139b94c778`. The overlapping edits in request preprocessing retain both the session context and upstream reasoning-effort mapping. A new regression test checks mapped prompt token IDs on cache misses, whole-prompt hits and prefix hits.

Validated source: [045e9051b2c8c93e90aed3e30516855edc57d99d](https://github.com/RichealYoung/vllm/tree/045e9051b2c8c93e90aed3e30516855edc57d99d), Git tree `af1302ed4f8a269418c146b1fd6184af02590c37`.

| Check | Result |
|---|---|
| CPU suite, including media fallback | 368 passed; no failures, errors or skips |
| Existing reasoning/render-parity and CLI tests | 19 passed on main; 19 passed with token reuse |
| New mapping regression with the mapping deliberately removed | Failed as expected; the correct implementation passed |
| Applicable pre-commit checks | 18 passed; no source changes made by hooks |
| Real text serving | 4 cases, 36 requests passed: Qwen3 and Llama, reuse off/on |

Serving checks compare complete prompt token IDs, token counts and generated output/logprobs with the normal computation path, and require actual whole-prompt and prefix reuse. The server fixtures and job manager reported no remaining processes. All tests ran on the server; these are correctness checks, not new performance measurements or upstream CI results.

The runtime used an RTX 3090, PyTorch 2.14.0+cu130, Transformers 5.20.2, tokenizers 0.23.2 and huggingface-hub 1.31.0. Model revisions remain Qwen3-0.6B `c1899de289a04d12100db370d81485cdf75e47ca` and Llama-3.2-1B `5a8abab4a5d6f164389b1079fb721cfab8d7126c`. Serving uses FP16, maximum length 1024, two sequences and GPU memory utilization 0.3. No session-prefix native extension is present.

Run the CPU and serving commands in the PR description at the source commit above. The additional upstream checks use:

```bash
.venv/bin/python -m pytest -v \
  tests/entrypoints/openai/test_render_parity.py \
  tests/entrypoints/common/test_cli_args.py -k 'reasoning or effort'
```

[Acceptance record](acceptance.json), [raw logs, commands and JUnit results](evidence-portable.tar.gz), and [file hashes](file-sha256.json) are available together. The archive's SHA256 is `ba10205d8064d72279f12d73c7304e4014f090c337dbf417b11919f875f46512`. Its 93 files were verified after download; 22 test-fixture links are stored as ordinary file bytes for portability.

<details>
<summary>Build scope and failed preparation attempts</summary>

The current main's `_C_stable_libtorch` and `fs_io_C` extensions were built in a private directory. Other existing libraries and dependencies were reused; dense Qwen/Llama serving does not validate MoE or every backend. This is not a clean GPU-stack installation.

An initial hook run failed because Windows-style line endings reached an upstream shell script. The archives were regenerated locally with `core.autocrlf=false` and `core.eol=lf`. Native binaries were reused only after checking every native/build source against the corrected archive after line-ending normalization. No product code, assertion or hook was weakened. A controller then read an asynchronously created status file too early; monitoring resumed against the same GPU job without rerunning tests. The original [build/hook failure evidence](evidence-initial.tar.gz) and failed-controller record inside the final archive are retained.

</details>

The [performance results](../benchmark.md) still describe their original frozen source and common benchmark patch. They were not rerun on this updated main, and their recorded inputs and raw results remain unchanged.
