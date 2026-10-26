# How tokenization reuse works

After applying the chat template, compare the prompt with the previous prompt in the same session. Reuse cached token IDs up to a safe tokenizer boundary within their common prefix, and tokenize only the remaining suffix. To locate it, scan backward for an added token, such as a chat delimiter, whose matching rules allow independent tokenization on either side, then verify its position against the cached token IDs. If no safe boundary exists, use normal tokenization.

Enable `--session-token-cache-mb <MiB>` and send the same `session_id` with complete chat histories. The default budget is zero, disabling reuse. Each renderer stores one previous prompt per session and `cache_salt` value. Histories use CPU memory. The limit covers cached entries, reserved space and entries still in use, not total process memory. Cancellation, failures and resets prevent incomplete or outdated entries from being cached.

## Tokenizer compatibility

Tested combinations are Transformers 5.16.1, 5.17.0, 5.18.0, 5.19.0, 5.20.0, 5.20.1 or 5.20.2 with tokenizers 0.23.2 or 0.23.3. Compatibility checks also examine the tokenizer backend, added tokens and encoding implementation. Unsupported configurations warn and use normal tokenization. A model name or version number alone does not enable reuse.

The benchmark uses Qwen3-0.6B tokenizer revision `c1899de289a04d12100db370d81485cdf75e47ca`. The feature documentation in the source tree lists other tested tokenizer configurations and revisions; these are not performance claims for those models. Keep the implementation and test version lists in sync when checking a new dependency combination.

Requests containing media use normal tokenization. Short prompts, edits, branching conversations and requests routed between processes can reduce reuse or make its overhead outweigh the savings.
