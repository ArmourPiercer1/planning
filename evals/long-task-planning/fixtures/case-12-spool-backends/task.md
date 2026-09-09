# Task: in-memory spool backend for tests

The spool currently has one backend (`file`). Add a **memory** backend for
tests:

1. `config['spool_backend'] = 'memory'` must give a writer and a reader
   with the **same public contract** as the file backend (same factories
   `open_writer`/`open_reader`, same method signatures, same event format,
   same observable semantics where the contract defines them).
2. The memory backend must not write anything to disk.
3. The file backend remains the **default** and must keep working exactly
   as it does today (including byte-offset semantics for
   `read_from`/`offset_of_last`, which existing callers persist between
   polls).
4. If any part of the file contract cannot be honored by a memory backend
   as-is, the plan must make that explicit and choose a legal response —
   do not silently change the file contract, and do not add unrelated
   features (no ring buffers, no compaction, no replication).

All existing tests must keep passing (note: one existing test pins that
the memory backend is NOT yet implemented — update it to pin the NEW
behavior). Add tests for the memory backend covering the shared contract.

Repo layout:

```
spool/
  __init__.py
  config.py      # DEFAULT_CONFIG, get/set/reset_config
  writer.py      # FileSpoolWriter, open_writer(cfg)
  reader.py      # FileSpoolReader (read_all/read_from/offset_of_last/truncate),
                 # open_reader(cfg)  — offsets are BYTE offsets
tests/
  test_spool.py
```
