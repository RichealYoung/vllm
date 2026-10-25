# Session prefix reuse

Session prefix reuse uses the existing `session_id` Agent Hint to select one
recent candidate for input tokenization and prompt block hash reuse. Enable
the two stages independently:

```console
vllm serve Qwen/Qwen3-0.6B \
    --tokenizer-revision c1899de289a04d12100db370d81485cdf75e47ca \
    --session-token-cache-mb 32 \
    --session-hash-cache-mb 32
```

Both options default to zero (disabled). Budgets are in MiB per renderer or
EngineCore instance, respectively; multiple processes do not share a budget.
The histories occupy CPU memory and do not retain physical KV blocks. Original
KV prefix lookup and existing scheduler optimizations remain active.

Send the existing `session_id` request field or `X-Session-ID` header. The
existing precedence is request field, header, then `vllm_xargs.session_id`.
Session identity selects a candidate; it does not prove equal content or a
parent/child relationship. Each process keeps the most recently successfully
published candidate per session and cache salt. Same-session requests may run
concurrently. Forks or worker routing can reduce reuse, without relaxing exact
content validation. No new request protocol fields are required.

## Initial support

Token reuse supports text Chat Completions with the following exact library
versions and audited tokenizer configurations. Each Transformers version in
the table can be paired with either listed tokenizers version:

| Transformers | tokenizers |
| --- | --- |
| 5.16.1 | 0.23.2, 0.23.3 |
| 5.17.0 | 0.23.2, 0.23.3 |
| 5.18.0 | 0.23.2, 0.23.3 |
| 5.19.0 | 0.23.2, 0.23.3 |
| 5.20.0 | 0.23.2, 0.23.3 |
| 5.20.1 | 0.23.2, 0.23.3 |
| 5.20.2 | 0.23.2, 0.23.3 |

These are explicit supported pairs, not a continuous version range. Install
mutually compatible dependencies: tokenizers 0.23.2 requires
`huggingface-hub<2.0`; compatibility validation used Hub 1.31.0.

| Tokenizer asset repository | Audited revision |
| --- | --- |
| Qwen/Qwen3-0.6B | `c1899de289a04d12100db370d81485cdf75e47ca` |
| Qwen/Qwen3-Coder-30B-A3B-Instruct | `b2cff646eb4bb1d68355c01b18ae02e7cf42d120` |
| Qwen/Qwen2.5-7B-Instruct | `a09a35458c702b33eeacc393d103063234e8bc28` |
| unsloth/Llama-3.2-1B-Instruct | `5a8abab4a5d6f164389b1079fb721cfab8d7126c` |
| zai-org/GLM-4.5 | `cbb2c7cfb52fa128a9660cb1a7a78e017899e115` |
| deepseek-ai/DeepSeek-V3.1 | `c0781d039fb7a1ba2abc4add0bdc293e92d2b8db` |

These repositories identify tokenizer assets, not a guarantee for every model
in a family. Qwen3 and Qwen3-Coder load the same audited backend. Compatibility
validation checks complete input token IDs, real chat templates, history edits,
length errors and fallback behavior; it does not certify GPU model execution
or performance for every listed model.

For DeepSeek-V3.1 tool calling, use vLLM's documented configuration:
`--tool-call-parser deepseek_v31` together with
`--chat-template examples/tool_chat_template_deepseekv31.jinja`.
See [DeepSeek-V3.1 tool calling](tool_calling.md#deepseek-v31-models-deepseek_v31).
The repository template serializes dictionary arguments and includes tool
definitions. The model-bundled template is not equivalent: it expects string
arguments and can reject tool-call histories after vLLM parses the arguments.
Token reuse neither substitutes templates automatically nor repairs such errors.
Mistral-7B-Instruct-v0.3's Metaspace backend is not admitted: encoding a suffix
independently can change its IDs. Other tokenizer configurations, including
ones that passed a preliminary raw-JSON survey, are not automatically admitted.

Other model revisions using an identical audited configuration can pass the same
checks. Activation checks the complete backend configuration
and public encoding implementation; a model name alone is insufficient.
The tokenizer must remain immutable. Unsupported configurations or library
versions disable token reuse with a warning and use native tokenization, even
when those library versions satisfy vLLM's installation requirements.

This initial native helper path requires a GIL-enabled CPython build.
If the helper extension is unavailable, the corresponding reuse stage is
disabled with a warning and requests use the existing computation path.

### Image requests

Image-path validation uses Qwen/Qwen2.5-VL-3B-Instruct revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`. CPU processor tests cover the 14
library-version pairs above, including changes in image dimensions. Real-model
serving tests use Transformers 5.20.2, tokenizers 0.23.3 and 56-by-56 synthetic
images. These checks do not establish support for other image models or sizes,
audio, video or resumable inputs, or a multimodal performance improvement.

### Boundary contract

The audited configurations extract non-normalized added tokens before any
normalizer runs. Certified boundaries do not require word context or overlap
another added-token occurrence. Subsequent normalization, regex, ByteLevel and
deterministic BPE processing is local to the separated text in these backends.
Consequently an unchanged prefix ending at a complete certified marker has
the same IDs when a suffix changes. Snapshots store only the prompt text and
token IDs. On a partial match, the frontend finds the last complete marker in
the common prefix and locates its token by walking from the nearer end of the
snapshot, where text and token IDs are aligned. Every added-token ID on that
walk must match the markers in the text, otherwise the full prompt is encoded.
Only an added token that cannot overlap another added token and needs no word
context ends a reused prefix; a right-stripping one does so only when the new
suffix does not start with whitespace. Other added tokens are still matched
during the walk.
This relies on added-token IDs being disjoint from ordinary BPE IDs. The pinned
backend fingerprint covers these properties; this argument does not apply
automatically to arbitrary special tokens or other tokenizers.

The frontend reruns the chat template and compares the resulting prompt. It
reuses only exact token prefixes ending at certified added-token boundaries.
Plain character matches and offsets alone are not treated as stability proofs.
Changed tools, thinking settings or template tails are handled through actual
rendered content comparison. Explicit input truncation, padding, offsets,
lowercasing, embedding inputs, LoRA configurations and connector
configurations do not use the initial frontend fast path.

Hash reuse requires an existing native block hasher, token inputs and
compatible salt/context. It independently compares full token IDs against its
own candidate, reuses complete blocks at the native hash granularity, and
continues the native hash chain. Frontend and EngineCore histories need not
refer to the same request. Resumable inputs, embedding inputs, LoRA and KV
connectors are outside initial hash support.

Requests without a session hint or with an incompatible configuration use the
existing computation path for the corresponding stage. Without a reusable
token boundary, the frontend encodes the full prompt; independent hash reuse
may still succeed. Insufficient history capacity prevents saving a new
snapshot without discarding results already computed or reused. A non-reusable
request can still incur bounded history publication work. Disabling token reuse
does not disable independent hash reuse, or vice versa.

### Multimodal reuse

Token reuse applies to the rendered text before media placeholder expansion,
using the same tokenizer and encoding-option checks as text requests. An
unchanged text prompt can therefore reuse token IDs even when an image changes.
The native processor still handles the current media and expands its
placeholders; the cached IDs do not preserve an old image or its layout.

Hash reuse compares the final token IDs and each media item's modality, native
identifier, offset and length. Unchanged media can be part of a reused prefix.
At the first changed, inserted or removed media span, reuse stops at complete
blocks before the earlier of the old and new span starts. Later hashes are
computed by the native hasher, even if the text after that span is unchanged.

Eligible media spans must be ordered, non-overlapping, positive-length and
within the prompt, with nonempty identifiers and no embedding mask. Unsupported
spans use native hashing without replacing or clearing older history. Later
requests still validate their prefixes against that history. Session snapshots
retain media descriptions, not media payloads. Native media identity and the
existing client UUID trust contract are unchanged; reuse does not verify that
a supplied UUID matches the media bytes.

Media loading, processing, input validation, encoder caching and KV-cache lookup
follow the native path. Neither reuse stage adds a media or vision-encoder cache.

## Memory and lifecycle

Simple LRU eviction bounds charged history state, including reservations and
snapshots still held by readers after replacement. Oversized items or requests
that cannot obtain a reservation are not cached. Cache-only token copies require
a reservation of the snapshot size before allocation. Accounting conservatively
charges shared Python objects; it is not an exact process RSS limit. Native
request inputs, outputs, Python allocators and other serving state are separate.
Temporary text-matching workspace is outside the retained-history budget.

Cancelled or failed rendering does not publish a staged token snapshot. Token
history is published after rendering and request adjustment, before EngineCore
input validation. A later validation error may leave that valid text-to-token
snapshot cached; it does not admit the rejected request or cache media expansion.
Initial hash prefixes are internal: callers must validate tokens and media spans
before passing them to Request.
Cache clearing and shutdown invalidate in-flight publication. EngineCore
prefix-cache reset also clears its CPU history. Restart creates empty histories;
there is no cross-worker sharing or persistence.

Use session IDs within the deployment's existing cache isolation domain and
respect `cache_salt`. Session IDs are not authentication credentials. Histories
do not bypass authorization or existing cache isolation policy.

This is an opt-in CPU optimization. Helper and component microbenchmarks do not
establish HTTP/IPC or GPU serving improvements; measure representative text
and image workloads with the enabled stages and normal renderer concurrency.
Image compatibility does not imply that media decoding or vision encoding is
skipped, or that every workload benefits from reuse.
