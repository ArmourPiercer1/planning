# Task: reliable delivery (retry + dead-letter)

The mailout pipeline currently attempts each message exactly once and
silently drops failures (see `mailout/worker.py`, module-level `DROPPED`).
Make delivery reliable:

1. **Retry with backoff.** Each message is attempted up to **3 times in
   total**. Between attempts use backoff; the backoff function must be
   injectable (or overridable in tests) so tests do not actually sleep.
2. **Dead-letter.** After the final failed attempt, the message must land in
   a dead-letter store **with the failure reason** (you may create a new
   file, e.g. `mailout/dead_letter.py`, for the store).
3. **Contract.** `Publisher.deliver(msg) -> bool` is called by other
   internal call sites outside this module and **must keep working exactly
   as it does today**. If the delivery contract needs to change in order to
   expose a failure reason, the change must be non-breaking for those call
   sites — and the plan should say so explicitly.
4. **Attempt log.** Each attempt (message id, attempt number, outcome) is
   recorded in an append-only in-memory log that tests can inspect.

All existing tests must keep passing (in particular, the current
single-attempt semantics of `process_queue` for successful messages). Add
tests for: retry-then-success, retry-exhaustion-to-dead-letter (with
reason), and the attempt log.

Repo layout:

```
mailout/
  __init__.py
  message.py     # make_message(id, to, body)
  publisher.py   # Publisher.deliver(msg) -> bool  (simulated carrier)
  queue.py       # MessageQueue: put / get / qsize
  worker.py      # process_queue(publisher, queue, max_items)
tests/
  test_mailout.py
```
