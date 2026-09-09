# Task: crash-safe SMS sending

`notify/cli.py` currently sends SMS synchronously: if the process dies
between the decision to send and the carrier acceptance, the message is
lost. Make sending durable:

1. `send_command(phone, body)` must first enqueue the message in the
   durable queue (`notify/store.py`, class `JsonQueue`, queue file
   `sms-queue.json`), then dispatch it: call the carrier
   (`notify/sender.py`) and mark the message sent on success. A failed
   send leaves the message in the queue (status stays non-sent).
2. `dispatch_command()` must drain the queue: send every pending message
   via the carrier, mark each one sent when the carrier accepts, and
   return the list of message ids it attempted (in queue order).
3. Message record shape in the queue:
   `{"id": str, "phone": str, "body": str, "enqueued_at": ISO-8601 str,
   "status": "pending"|"sent"}`.
   Generate a unique `id` (e.g. `uuid4` or timestamp-based) per message.
4. `send_sms` in `notify/sender.py` (carrier-facing behavior, including
   its rejection rules) must NOT change.

All existing tests must keep passing. Add tests for the new behavior:
durable send, drain, and failed-send-stays-queued (you may point the queue
at a temp file in tests; do not rely on `sms-queue.json` in the CWD).

The repo layout:

```
notify/
  __init__.py
  sender.py      # send_sms(phone, body) -> {"ok": bool, "carrier_response": str}
  store.py       # JsonQueue: enqueue / pending / mark_done / all
  cli.py         # send_command, dispatch_command (stub), QUEUE_PATH
tests/
  test_notify.py
```
