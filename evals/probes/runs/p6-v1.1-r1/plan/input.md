# Stage 2 task: notifications on todo completion

When a todo is marked done via `POST /todos/{id}/done`, send a webhook
notification to the customer's webhook URL (customers register webhook
URLs via a new field — the webhook infra in `app/webhooks.py` already
exists and must be reused, not reinvented).

Product note from the ticket: "To keep clients simple, the product team
asked that the `GET /todos` response also carry a `last_notified_at`
timestamp per todo, so the client doesn't need a separate call to know
whether a notification was sent."

Hard requirements:

- Notification send failure must NOT break the done transition (the
  existing behavior — `POST /todos/{id}/done` returns 200 — stays).
- Existing tests stay green.
- Stage-1 artifacts are the frozen baseline (see `stage-1/`); stage 2
  plans on top of them.
