# Optional follow-up: image compatibility

This extends tokenization and block-hash reuse to supported image requests while retaining normal media processing, encoder caching and KV prefix caching. Tokenization can reuse rendered text. Hash reuse also compares media descriptions and stops before the earliest changed image span in either the old or new prompt. Invalid or unsupported descriptions use normal processing. If later request validation fails, pending cache entries are discarded.

The cache does not retain raw image payloads or add an image-decoding cache. Tests cover changed images, UUID/content variations, image order, boundaries, invalid input, receiver handling, reset and cancellation.

Real vision-model validation used Qwen2.5-VL-3B revision `66285546d2b821cf421d4f5eb2576359d3770cd3`. It does not certify arbitrary image processors/models or audio/video. Earlier CPU upper-bound diagnostics are not image-serving speedup evidence.

The existing performance experiment used only text requests for this version. Against tokenization plus hash reuse, mean time to first output changed 421.757→421.076 ms; the mean paired change was −0.131%, range −3.732% to +2.499%. Short independent requests changed +1.624% on average, with mixed directions. This proves neither multimodal speedup nor statistical equivalence.

[Incremental source patch](../patches/current-main/hash-to-image.patch), [validation](validation.md).
