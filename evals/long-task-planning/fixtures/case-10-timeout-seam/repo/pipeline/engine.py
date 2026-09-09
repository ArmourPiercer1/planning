"""Execution engine (simulated work)."""


def run_job(job, work_ms):
    """Simulate running a job whose work takes work_ms.

    Uses the producer's timeout field. Returns {"id", "status"} where
    status is 'done' or 'timeout'.
    """
    timeout = job.get("timeout_ms", 30000)
    status = "timeout" if work_ms > timeout else "done"
    return {"id": job["id"], "status": status}
