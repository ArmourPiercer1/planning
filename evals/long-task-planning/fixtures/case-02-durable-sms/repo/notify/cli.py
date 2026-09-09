"""Command entry points for the notify service."""

import datetime as _dt

from notify import sender
from notify.store import JsonQueue

QUEUE_PATH = "sms-queue.json"


def _queue():
    return JsonQueue(QUEUE_PATH)


def send_command(phone, body):
    """Send an SMS.

    Current behavior: synchronous carrier call, no persistence — a crash
    between the decision to send and carrier acceptance loses the message.
    """
    return sender.send_sms(phone, body)


def dispatch_command():
    """Drain the durable queue.

    TODO: not implemented yet. Should send every pending message via the
    carrier, mark each one sent when accepted, and return the ids attempted.
    """
    return []
