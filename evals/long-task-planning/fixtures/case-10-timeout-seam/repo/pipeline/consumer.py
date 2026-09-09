"""Consumer-side job parsing."""

DEFAULT_TIMEOUT_MS = 30000


def job_timeout(job):
    """Effective timeout (ms) for a job, per the consumer's contract.

    NOTE: the consumer's draft contract expects a 'timeout' key.
    """
    return job.get("timeout", DEFAULT_TIMEOUT_MS)


def validate_job(job):
    """Basic shape validation for incoming jobs."""
    if "id" not in job:
        raise ValueError("job missing id")
    if "payload" not in job:
        raise ValueError("job missing payload")
    return True
