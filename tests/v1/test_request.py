# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project

import pytest

from vllm import SamplingParams
from vllm.multimodal.inputs import MultiModalFeatureSpec, PlaceholderRange
from vllm.v1.engine import EngineCoreRequest
from vllm.v1.kv_hints import KvHintAction, KvHintsEnvelope
from vllm.v1.request import Request, RequestStatus


def _multimodal_session_request(ids, media, salt="salt"):
    return EngineCoreRequest(
        request_id="multimodal",
        prompt_token_ids=ids,
        mm_features=[
            MultiModalFeatureSpec(
                data=None,
                modality="image",
                identifier=identifier,
                mm_position=PlaceholderRange(offset=offset, length=length),
            )
            for identifier, offset, length in media
        ],
        sampling_params=SamplingParams(max_tokens=3),
        pooling_params=None,
        arrival_time=0.0,
        lora_request=None,
        cache_salt=salt,
        data_parallel_rank=None,
        session_id="multimodal-session",
    )


@pytest.mark.parametrize("block_size", [4, 8, 16])
def test_multimodal_session_hash_reuse_matches_native_at_media_boundaries(block_size):
    """Media edits invalidate the hash chain even when every token is unchanged."""
    from vllm.utils.hashing import sha256
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash
    from vllm.v1.core.session_prefix import SessionHashCache

    init_none_hash(sha256)
    hasher = get_request_block_hasher(block_size, sha256)
    ids = list(range(12 * block_size + 1))
    for offset in (0, block_size - 1, block_size, block_size + 1):
        for length in (
            1,
            block_size - 1,
            block_size,
            block_size + 1,
            2 * block_size + 1,
        ):
            original = [("first", offset, length)]
            variants = [
                (original, len(ids) // block_size),
                ([("changed", offset, length)], offset // block_size),
                ([], offset // block_size),
                ([("first", offset + 1, length)], offset // block_size),
                ([("first", offset, length + 1)], offset // block_size),
                (
                    original + [("first", 8 * block_size, 1)],
                    8,
                ),
            ]
            for media, expected_blocks in variants:
                cache = SessionHashCache(1 << 20, block_size)
                previous = _multimodal_session_request(ids.copy(), original)
                native = Request.from_engine_core_request(previous, hasher)
                cache.publish(previous, native, cache.store.epoch)
                incoming = _multimodal_session_request(ids.copy(), media)
                prefix = cache.prefix(incoming)
                assert (len(prefix[1]) if prefix else 0) == expected_blocks
                actual = Request.from_engine_core_request(incoming, hasher, prefix)
                expected = Request.from_engine_core_request(incoming, hasher)
                assert actual.block_hashes == expected.block_hashes
                for token in range(500, 500 + block_size + 1):
                    actual.append_output_token_ids(token)
                    expected.append_output_token_ids(token)
                    assert actual.block_hashes == expected.block_hashes
                if (not media or media[0][0] == "changed") and offset >= block_size:
                    assert native.block_hashes != expected.block_hashes
                incoming.cache_salt = "other"
                assert cache.prefix(incoming) is None


@pytest.mark.parametrize("block_size", [4, 8, 16])
def test_multimodal_session_hash_reuse_stops_before_either_changed_media(block_size):
    """Left moves and leading insertions/deletions require both span starts."""
    from vllm.utils.hashing import sha256
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash
    from vllm.v1.core.session_prefix import SessionHashCache

    init_none_hash(sha256)
    hasher = get_request_block_hasher(block_size, sha256)
    ids = list(range(10 * block_size + 1))
    cases = (
        ([("first", block_size, 1)], [("first", block_size - 1, 1)], 0),
        (
            [("A", 6 * block_size, 1)],
            [("X", block_size, 1), ("A", 6 * block_size, 1)],
            1,
        ),
        (
            [("A", block_size, 1), ("C", 6 * block_size, 1)],
            [("C", 6 * block_size, 1)],
            1,
        ),
    )
    for previous_media, current_media, expected_blocks in cases:
        cache = SessionHashCache(1 << 20, block_size)
        previous = _multimodal_session_request(ids.copy(), previous_media)
        old = Request.from_engine_core_request(previous, hasher)
        cache.publish(previous, old, cache.store.epoch)
        incoming = _multimodal_session_request(ids.copy(), current_media)
        prefix = cache.prefix(incoming)
        assert (len(prefix[1]) if prefix else 0) == expected_blocks
        expected = Request.from_engine_core_request(incoming, hasher)
        actual = Request.from_engine_core_request(incoming, hasher, prefix)
        assert actual.block_hashes == expected.block_hashes
        assert old.block_hashes != expected.block_hashes


def test_multimodal_session_hash_generated_edits_preserve_native_chain():
    """Seeded token/media edits cover append, reorder and text/media transitions."""
    import random

    from vllm.utils.hashing import sha256
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash
    from vllm.v1.core.session_prefix import SessionHashCache

    init_none_hash(sha256)
    randomizer = random.Random(20261025)
    for iteration in range(200):
        block_size = randomizer.choice((4, 8, 16))
        hasher = get_request_block_hasher(block_size, sha256)
        cache = SessionHashCache(1 << 20, block_size)
        ids = list(range(10 * block_size + 1))
        media = [("first", block_size, block_size + 1), ("second", 6 * block_size, 1)]
        previous = _multimodal_session_request(ids, media if iteration % 8 else [])
        cache.publish(
            previous,
            Request.from_engine_core_request(previous, hasher),
            cache.store.epoch,
        )
        changed = ids.copy()
        if iteration % 4 == 0:
            changed.extend([1000] * block_size)
        elif iteration % 4 == 1:
            changed[randomizer.randrange(len(ids))] = 999
        if iteration % 8 == 2:
            media = [
                ("second", block_size, block_size + 1),
                ("first", 6 * block_size, 1),
            ]
        elif iteration % 8 == 3:
            media = []
        elif iteration % 8 == 5:
            media[0] = ("replacement", block_size, block_size + 1)
        incoming = _multimodal_session_request(changed, media)
        prefix = cache.prefix(incoming)
        expected_end = next(
            (
                index
                for index, (old_token, new_token) in enumerate(zip(ids, changed))
                if old_token != new_token
            ),
            len(ids),
        )
        previous_media = [
            (feature.identifier, feature.mm_position.offset, feature.mm_position.length)
            for feature in previous.mm_features or []
        ]
        for old_item, new_item in zip(previous_media, media):
            if old_item != new_item:
                expected_end = min(expected_end, old_item[1], new_item[1])
                break
        else:
            unmatched = previous_media[len(media) :] or media[len(previous_media) :]
            if unmatched:
                expected_end = min(expected_end, unmatched[0][1])
        assert (len(prefix[1]) if prefix else 0) == expected_end // block_size, (
            iteration
        )
        actual = Request.from_engine_core_request(incoming, hasher, prefix)
        expected = Request.from_engine_core_request(incoming, hasher)
        assert actual.block_hashes == expected.block_hashes, iteration
        if iteration % 8 in (0, 3, 4, 6, 7) and iteration % 4 != 1:
            assert prefix is not None


def test_multimodal_session_hash_snapshot_isolated_and_invalid_spans_decline():
    """New spans are validated and retained metadata is immutable and budgeted."""
    import copy

    import torch

    from vllm.utils.hashing import sha256
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash
    from vllm.v1.core.session_prefix import SessionHashCache

    init_none_hash(sha256)
    hasher = get_request_block_hasher(4, sha256)
    original = _multimodal_session_request(list(range(40)), [("first", 8, 5)])
    native = Request.from_engine_core_request(original, hasher)
    cache = SessionHashCache(1 << 20, 4)
    cache.publish(original, native, cache.store.epoch)
    assert cache.prefix(original) is not None
    assert original.mm_features is not None
    original.mm_features[0].identifier = "changed"
    prefix = cache.prefix(original)
    assert prefix is not None and len(prefix[1]) == 2
    used = cache.store.bytes_used
    for offset, length, identifier, mask in (
        (-1, 5, "first", None),
        (True, 5, "first", None),
        (8, 0, "first", None),
        (8, 50, "first", None),
        (8, 5, "", None),
        (8, 5, "first", torch.ones(5, dtype=torch.bool)),
    ):
        incoming = copy.deepcopy(original)
        assert incoming.mm_features is not None
        feature = incoming.mm_features[0]
        feature.identifier = identifier
        feature.mm_position = PlaceholderRange(
            offset=offset, length=length, is_embed=mask
        )
        assert cache.prefix(incoming) is None
        cache.publish(incoming, native, cache.store.epoch)
        assert cache.store.bytes_used == used
    for media in (
        [("first", 8, 5), ("second", 10, 3)],
        [("first", 20, 2), ("second", 8, 3)],
    ):
        incoming = _multimodal_session_request(list(range(40)), media)
        assert cache.prefix(incoming) is None
        cache.publish(incoming, native, cache.store.epoch)
        assert cache.store.bytes_used == used
    tiny = SessionHashCache(used - 1, 4)
    tiny.publish(original, native, tiny.store.epoch)
    assert tiny.store.bytes_used == 0
    assert tiny.prefix(original) is None
    cache.store.clear()
    assert cache.store.bytes_used == 0 and cache.prefix(original) is None


def test_hash_publication_reserved_before_reset_cannot_publish_after_reset():
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from vllm.utils.hashing import sha256
    from vllm.utils.session_prefix import Reservation
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash
    from vllm.v1.core.session_prefix import SessionHashCache

    init_none_hash(sha256)
    hasher = get_request_block_hasher(4, sha256)
    incoming = EngineCoreRequest(
        request_id="inflight",
        prompt_token_ids=list(range(33)),
        mm_features=None,
        sampling_params=SamplingParams(max_tokens=1),
        pooling_params=None,
        arrival_time=0.0,
        lora_request=None,
        cache_salt=None,
        data_parallel_rank=None,
        session_id="session",
    )
    native = Request.from_engine_core_request(incoming, hasher)
    for close in (False, True):
        cache = SessionHashCache(1 << 20, 4)
        entered, release = threading.Event(), threading.Event()
        previous = threading.getprofile()

        def observe(frame, event, arg, cache=cache, entered=entered, release=release):
            if (
                frame.f_code is Reservation.commit.__code__
                and event == "call"
                and frame.f_locals["self"].store is cache.store
            ):
                entered.set()
                assert release.wait(10)

        threading.setprofile(observe)
        try:
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(cache.publish, incoming, native, cache.store.epoch)
                try:
                    assert entered.wait(10), "real commit was not reached"
                    assert cache.store.bytes_used > 0
                    cache.store.clear(close=close)
                finally:
                    release.set()
                future.result(timeout=10)
        finally:
            release.set()
            threading.setprofile(previous)
        assert cache.store.bytes_used == 0
        assert cache.prefix(incoming) is None


def test_session_hash_reuse_preserves_native_chain_and_decode():
    from vllm.utils.hashing import sha256
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash
    from vllm.v1.core.session_prefix import SessionHashCache

    init_none_hash(sha256)
    for block_size in (2, 4, 16):
        hasher = get_request_block_hasher(block_size, sha256)
        cache = SessionHashCache(1 << 20, block_size)
        for turn, ids in enumerate(
            (list(range(33)), list(range(35)), [99] + list(range(34)))
        ):
            incoming = EngineCoreRequest(
                request_id=str(turn),
                prompt_token_ids=ids,
                mm_features=None,
                sampling_params=SamplingParams(max_tokens=3),
                pooling_params=None,
                arrival_time=0.0,
                lora_request=None,
                cache_salt="salt",
                data_parallel_rank=None,
                session_id="session",
            )
            expected = Request.from_engine_core_request(incoming, hasher)
            initial = cache.prefix(incoming)
            actual = Request.from_engine_core_request(incoming, hasher, initial)
            assert actual.block_hashes == expected.block_hashes
            if turn == 1:
                assert initial is not None and initial[1]
            cache.publish(incoming, actual, cache.store.epoch)
            for token in range(100, 118):
                actual.append_output_token_ids(token)
                expected.append_output_token_ids(token)
                assert actual.block_hashes == expected.block_hashes
        incoming.cache_salt = "different"
        assert cache.prefix(incoming) is None
        assert cache.stats["reused_blocks"] > 0
        cache.store.clear()
        assert cache.store.bytes_used == 0


def test_initial_hashes_reject_invalid_block_count():
    import pytest

    from vllm.utils.hashing import sha256
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash

    init_none_hash(sha256)
    with pytest.raises(ValueError, match="initial prompt block hashes"):
        Request(
            "invalid",
            [1],
            SamplingParams(max_tokens=1),
            None,
            block_hasher=get_request_block_hasher(16, sha256),
            initial_block_hashes=(16, [b"invalid"]),
        )


def test_session_hash_reset_close_and_eviction_preserve_native_results():
    from vllm.utils.hashing import sha256
    from vllm.v1.core.kv_cache_utils import get_request_block_hasher, init_none_hash
    from vllm.v1.core.session_prefix import SessionHashCache

    init_none_hash(sha256)
    hasher = get_request_block_hasher(4, sha256)
    incoming = EngineCoreRequest(
        request_id="lifecycle",
        prompt_token_ids=list(range(33)),
        mm_features=None,
        sampling_params=SamplingParams(max_tokens=1),
        pooling_params=None,
        arrival_time=0.0,
        lora_request=None,
        cache_salt="salt",
        data_parallel_rank=None,
        session_id="session",
    )
    native = Request.from_engine_core_request(incoming, hasher)
    for close in (False, True):
        cache = SessionHashCache(1 << 20, 4)
        cache.publish(incoming, native, cache.store.epoch)
        initial = cache.prefix(incoming)
        assert initial is not None
        epoch = cache.store.epoch
        cache.store.clear(close=close)
        cache.publish(incoming, native, epoch)
        assert cache.store.bytes_used == 0  # Stale work cannot repopulate.
        actual = Request.from_engine_core_request(incoming, hasher, initial)
        assert actual.block_hashes == native.block_hashes  # Existing reader is valid.
        assert cache.prefix(incoming) is None
        if not close:
            cache.publish(incoming, actual, cache.store.epoch)
            assert cache.prefix(incoming) is not None

    probe = SessionHashCache(1 << 20, 4)
    probe.publish(incoming, native, probe.store.epoch)
    capacity = probe.store.bytes_used + 1
    cache = SessionHashCache(capacity, 4)
    cache.publish(incoming, native, cache.store.epoch)
    with cache.store.borrow(("salt", "session")) as snapshot:
        assert snapshot is not None
        incoming.session_id = "another"
        cache.publish(incoming, native, cache.store.epoch)
        assert cache.prefix(incoming) is None  # Pinned retired reader consumes budget.
        assert 0 < cache.store.bytes_used <= capacity
        assert snapshot.hashes == native.block_hashes
    assert cache.store.bytes_used == 0
    incoming.session_id = "session"
    cache.publish(incoming, native, cache.store.epoch)
    initial = cache.prefix(incoming)
    assert initial is not None
    assert (
        Request.from_engine_core_request(incoming, hasher, initial).block_hashes
        == native.block_hashes
    )


def test_request_status_fmt_str():
    """Test that the string representation of RequestStatus is correct."""
    assert f"{RequestStatus.WAITING}" == "WAITING"
    assert (
        f"{RequestStatus.WAITING_FOR_STRUCTURED_OUTPUT_GRAMMAR}"
        == "WAITING_FOR_STRUCTURED_OUTPUT_GRAMMAR"
    )
    assert f"{RequestStatus.WAITING_FOR_REMOTE_KVS}" == "WAITING_FOR_REMOTE_KVS"
    assert f"{RequestStatus.WAITING_FOR_STREAMING_REQ}" == "WAITING_FOR_STREAMING_REQ"
    assert f"{RequestStatus.RUNNING}" == "RUNNING"
    assert f"{RequestStatus.PREEMPTED}" == "PREEMPTED"
    assert f"{RequestStatus.FINISHED_STOPPED}" == "FINISHED_STOPPED"
    assert f"{RequestStatus.FINISHED_LENGTH_CAPPED}" == "FINISHED_LENGTH_CAPPED"
    assert f"{RequestStatus.FINISHED_ABORTED}" == "FINISHED_ABORTED"
    assert f"{RequestStatus.FINISHED_IGNORED}" == "FINISHED_IGNORED"


def test_request_copies_session_id_from_engine_core_request():
    """Test that Request preserves session ID from EngineCoreRequest."""
    engine_request = EngineCoreRequest(
        request_id="request-1",
        prompt_token_ids=[1, 2, 3],
        mm_features=None,
        sampling_params=SamplingParams(max_tokens=1),
        pooling_params=None,
        arrival_time=0.0,
        lora_request=None,
        cache_salt=None,
        data_parallel_rank=None,
        session_id="session-1",
    )

    request = Request.from_engine_core_request(engine_request, block_hasher=None)

    assert request.session_id == "session-1"


def test_request_copies_kv_hints_from_engine_core_request():
    """Test that Request preserves KV hints from EngineCoreRequest."""
    kv_hints = KvHintsEnvelope(
        protocol_version="0.1",
        message_id="msg-1",
        actions=[
            KvHintAction(
                action_id="action-1",
                action_type="example.action",
                action_version="1.0",
                payload={},
            )
        ],
    )
    engine_request = EngineCoreRequest(
        request_id="request-1",
        prompt_token_ids=[1, 2, 3],
        mm_features=None,
        sampling_params=SamplingParams(max_tokens=1),
        pooling_params=None,
        arrival_time=0.0,
        lora_request=None,
        cache_salt=None,
        data_parallel_rank=None,
        kv_hints=kv_hints,
    )

    request = Request.from_engine_core_request(engine_request, block_hasher=None)

    assert request.kv_hints == kv_hints
