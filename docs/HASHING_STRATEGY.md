# FirstTry Hashing Strategy

There are **two** hash families in use on purpose:

1. **BLAKE3 (canonical content hashing / fast path)**
   - Implementation:
     - `firsttry.twin.hashers.hash_bytes`
     - `firsttry.twin.hashers.hash_file`
     - `firsttry.twin.hashers.hash_files`
     - Rust extension `firsttry.ft_fastpath` (via `blake3` crate)
   - Usage:
     - Fast path for repository scanning and content hashing.
     - Warm cache keys that must match between Python and Rust.
   - Guarantee:
     - Python and Rust implementations are kept in parity by
       `tests/firsttry/test_ft_fastpath_parity.py`.

2. **BLAKE2b (16-byte / 32-hex-character "historic" digests)**
   - Implementation:
     - `firsttry.runner.state` (repo fingerprint)
     - `firsttry.runner.planner` (plan cache key helper)
   - Usage:
     - Historic identifiers and fingerprints baked into tests and
       existing cache formats.
   - Guarantee:
     - We keep this format stable to avoid breaking existing caches,
       log parsing, and tests that assert specific digest lengths.

### Rules for future changes

- **Do NOT** replace BLAKE2b in `state.py` or `planner.py` without
  a deliberate migration plan and corresponding test updates.

- Any new content hashing or fast-path logic must use **BLAKE3** via:

  ```python
  from firsttry.twin.hashers import hash_bytes, hash_file, hash_files
  ```

Any changes to ft_fastpath hashing MUST keep parity between Rust and
Python; extend or update test_ft_fastpath_parity.py accordingly.

You can also add a small pointer in `CONTRIBUTING.md` or `DEVELOPING.md` like: “See `docs/HASHING_STRATEGY.md` before touching any hashing code.”
