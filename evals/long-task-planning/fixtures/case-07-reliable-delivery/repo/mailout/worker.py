"""Queue worker: pops messages and delivers them.

Current behavior: one attempt per message; failures are appended to the
module-level DROPPED list and otherwise forgotten.
"""

DROPPED = []


def process_queue(publisher, queue, max_items=None):
    """Process up to max_items messages (all if None).

    Returns a list of {"id": str, "ok": bool} in processing order.
    """
    results = []
    n = 0
    while queue.qsize() > 0 and (max_items is None or n < max_items):
        msg = queue.get()
        ok = publisher.deliver(msg)
        if not ok:
            DROPPED.append(msg["id"])
        results.append({"id": msg["id"], "ok": ok})
        n += 1
    return results
