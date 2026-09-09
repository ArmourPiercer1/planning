"""Message records."""


def make_message(msg_id, to, body):
    return {"id": msg_id, "to": to, "body": body, "attempts": 0}
