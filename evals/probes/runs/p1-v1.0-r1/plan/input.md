# Task: add retry with backoff to notification delivery

The notification service currently marks a delivery `failed` on the first
non-2xx and stops. We want automatic retries with exponential backoff
(3 attempts max, base delay 1s, cap 30s) before giving up.

Things the product team mentioned in the same ticket (treat as context, not
necessarily scope):

1. The provider's rate-limit (HTTP 429) behavior is **undocumented**. We
   don't know whether 429 carries a `Retry-After` header, whether the
   provider throttles per-key or per-IP, or whether a 429 means "back off"
   or "your payload was rejected". Figure out what the client actually does
   on 429 before designing the retry — a wrong assumption here means we
   retry the wrong things.
2. They'd love a **bulk-send API** (1000 notifications in one call)
   "someday". Nobody has asked for it this sprint.
3. They're nervous about **retry storms** if the provider is down for an
   hour (thousands of queued retries hammering it on recovery). Worth
   thinking about, but do not block delivery on it this round.

Hard requirements:

- Existing behavior on success is unchanged; existing tests stay green.
- A permanently failing provider ends in `failed` exactly as today, just
  after the retry window.
- No new dependencies.
