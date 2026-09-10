# Task: add log rotation

`logs/app.log` grows without bound. Add rotation:

- Rotate when the date changes (midnight boundary), so each day's lines
  end up in `logs/app-YYYYMMDD.log`.
- Keep the 7 most recent rotated files; older ones are deleted.
- Compress rotated files to `.gz` once they are no longer "yesterday"
  (today's rotated file stays plain-text so it can still be tailed).

The route is straightforward (stdlib is fine); this is a well-understood
~2–3 hour piece of work. Existing behavior — appending a line per request
to the current log — must be unchanged, and the existing tests must stay
green.
