# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Session-selected prompt hash snapshots; never retains physical KV blocks."""

import struct
import sys
import threading
from collections import Counter
from dataclasses import dataclass

from vllm.logger import init_logger
from vllm.utils.session_prefix import SessionPrefixStore, token_bound, token_bytes
from vllm.v1.core import kv_cache_utils
from vllm.v1.core.kv_cache_utils import BlockHash
from vllm.v1.engine import EngineCoreRequest
from vllm.v1.request import Request

logger = init_logger(__name__)


@dataclass(frozen=True)
class HashSnapshot:
    ids: list[int]
    hashes: list[BlockHash]
    # Validated upper bound of ``ids`` (see token_bound), or None if unknown.
    bound: int | None = None


@dataclass(frozen=True)
class HashPrefix:
    """Snapshot block hashes that a request's prompt can reuse.

    The first ``tokens`` IDs of ``ids`` equal the snapshot's IDs, whose
    validated upper bound is ``bound``.
    """

    block_size: int
    hashes: list[BlockHash]
    ids: list[int]
    tokens: int
    bound: int | None

    @property
    def initial_block_hashes(self) -> tuple[int, list[BlockHash]]:
        return self.block_size, self.hashes


class SessionHashCache:
    @classmethod
    def create(cls, capacity: int, block_size: int) -> "SessionHashCache | None":
        try:
            return cls(capacity, block_size)
        except ImportError as exc:
            logger.warning("Session hash cache disabled: %s", exc)
            return None

    def __init__(self, capacity: int, block_size: int):
        from vllm import _session_prefix

        self.helper = _session_prefix
        self.block_size = block_size
        self.none_hash = kv_cache_utils.NONE_HASH
        self.store: SessionPrefixStore[HashSnapshot] = SessionPrefixStore(capacity)
        self.stats: Counter[str] = Counter()
        self._stats_lock = threading.Lock()

    @staticmethod
    def eligible(request: EngineCoreRequest) -> bool:
        return bool(
            request.session_id
            and type(request.prompt_token_ids) is list
            and request.prompt_embeds is None
            and request.prompt_is_token_ids is None
            and not request.mm_features
            and request.lora_request is None
            and not request.resumable
            and request.pooling_params is None
            and request.sampling_params is not None
        )

    def prefix(self, request: EngineCoreRequest) -> HashPrefix | None:
        if not self.eligible(request) or self.none_hash != kv_cache_utils.NONE_HASH:
            return None
        key = (request.cache_salt, request.session_id)
        with self.store.borrow(key) as old:
            if old is None:
                return None
            ids = request.prompt_token_ids
            assert ids is not None
            limit = min(len(old.hashes), len(ids) // self.block_size) * self.block_size
            try:
                tokens = self.helper.token_lcp(ids, old.ids, limit)
            except (OverflowError, ValueError):
                return None
            count = tokens // self.block_size
            with self._stats_lock:
                self.stats["reused_blocks"] += count
            logger.debug("Session hash reuse: reused_blocks=%d", count)
            if not count:
                return None
            return HashPrefix(
                self.block_size, old.hashes[:count], ids, tokens, old.bound
            )

    def publish(
        self,
        request: EngineCoreRequest,
        result: Request,
        epoch: int,
        prefix: HashPrefix | None = None,
    ) -> None:
        if (
            not self.eligible(request)
            or epoch != self.store.epoch
            or self.none_hash != kv_cache_utils.NONE_HASH
        ):
            return
        ids = request.prompt_token_ids
        assert ids is not None
        if prefix is not None and prefix.ids is ids and prefix.bound is not None:
            # token_lcp matched the leading IDs against a snapshot validated when
            # it was stored, so only the remaining IDs need scanning.
            suffix = token_bound(ids[prefix.tokens :])
            bound = None if suffix is None else max(prefix.bound, suffix)
        else:
            bound = token_bound(ids)
        hashes = result.block_hashes
        key = (request.cache_salt, request.session_id)
        size = (
            1024
            + sum(map(sys.getsizeof, key))
            + token_bytes(ids, bound)
            + sys.getsizeof([])
            + len(hashes) * struct.calcsize("P")
            + sum(map(sys.getsizeof, hashes))
        )
        reservation = self.store.reserve(key, size)
        if reservation is not None:
            try:
                snapshot = HashSnapshot(ids.copy(), hashes.copy(), bound)
                if reservation.epoch == epoch:
                    reservation.commit(snapshot, size)
            finally:
                reservation.cancel()
