import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Job:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    message: str = ""
    result: Any = None
    error: str | None = None
    _cancel_flag: bool = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_flag

    def cancel(self):
        self._cancel_flag = True

class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def create_job(self) -> Job:
        job = Job()
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job and job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
            job.cancel()
            job.status = JobStatus.CANCELLED
            return True
        return False

# Global singleton
job_manager = JobManager()

class JobProgressReporter:
    def __init__(self, job: Job):
        self.job = job

    def on_progress(self, label: str, current: int, total: int) -> None:
        if total > 0:
            self.job.progress = (current / total) * 100
        self.job.message = label

    def on_log(self, message: str) -> None:
        self.job.message = message

    def on_error(self, error: str) -> None:
        self.job.status = JobStatus.FAILED
        self.job.error = error

    def on_finished(self, result: Any) -> None:
        self.job.status = JobStatus.COMPLETED
        self.job.progress = 100
        self.job.result = result

