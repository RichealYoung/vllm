# Follow-up: session reuse for image requests

This optional follow-up builds on [block-hash reuse](../v2/README.md). It is not part of [PR #63361](https://github.com/vllm-project/vllm/pull/63361).

## Overview

With tokenization and hash reuse alone, requests that contain images use normal processing. This follow-up lets them use both features. Tokenization reuse runs on the rendered text before image placeholders are expanded. Hash reuse also compares each image's identity, position and length, and stops before the earliest changed image in either the previous or the new prompt. Media loading, processor caching, encoder caching and prefix caching are unchanged, and image payloads are not stored in session histories.

## Claims

- Uses the same opt-in budgets as the previous stages; no new options.
- This is a correctness extension, not a speedup claim. Replacing an image while keeping identical token IDs changes the normal hash chain, and reuse stops before the affected block.
- No image-workload performance is claimed. On text-only requests this version performed like the previous stage: mean time to first output 421.8 → 421.1 ms (individual runs −3.7% to +2.5%); short independent requests changed +1.6% on average with mixed directions. This shows neither a speedup nor statistical equivalence.

## Validation

Qwen2.5-VL-3B-Instruct (revision `66285546d2b821cf421d4f5eb2576359d3770cd3`), comparing no reuse, tokenization reuse, hash reuse and both, against requests without a session hint.

- **CPU:** an earlier tested source passed 403 CPU tests, including the real image processor, image replacement, resizing, insertion and removal, reordering, block boundaries, invalid image spans, and discarding pending entries after failures. It also passed 72 requests to running text-model servers.
- **Image serving:** 60 valid image requests, 8 invalid image requests and 12 streaming-close/reset/recovery requests. Complete prompt token IDs and usage matched requests without a session hint, and 72 complete normal hash chains were checked independently.
- The synthetic test images produce the same first output tokens, so comparing outputs alone does not prove that images are distinguished; the hash checks do.
- The published source was reassembled and passed source-hash and pre-commit checks; its CPU/GPU tests were not rerun. See [validation details](validation.md).

## Limitations

- One image model and fixed 56×56 synthetic images. Audio, video, embedding-mask spans and other image models need their own real-path validation.
- Image identity follows vLLM's existing media hashing, including its current trust in client-provided UUIDs.

## Code

- [Incremental changes: hash reuse → image compatibility](https://github.com/RichealYoung/vllm/compare/6360b1aa9473faf377fa0c383c14ad6a53fac587...f9732fa728c5f7507373f0790ce8a1f6babc64fa)
- [Full source snapshot](https://github.com/RichealYoung/vllm/tree/f9732fa728c5f7507373f0790ce8a1f6babc64fa) · [patch](../patches/V2-to-V3.patch) · [design notes](design.md)
- Previous: [block-hash reuse](../v2/README.md)
