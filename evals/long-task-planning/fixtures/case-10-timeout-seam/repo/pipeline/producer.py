"""Producer-side job emission."""


def make_job(job_id, payload, timeout_ms=30000):
    """Emit a job dict for the pipeline.

    Producer contract: the timeout field is 'timeout_ms'.
    """
    return {"id": job_id, "payload": payload, "timeout_ms": timeout_ms}
