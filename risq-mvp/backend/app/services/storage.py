from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from backend.app.schemas.report import Report


@dataclass
class Job:
    job_id: str
    status: str
    step: str
    created_at: datetime
    error: Optional[str] = None
    report: Optional[Report] = None


class InMemoryStorage:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create_job(self) -> Job:
        job_id = str(uuid4())
        job = Job(
            job_id=job_id,
            status="queued",
            step="Ожидание запуска…",
            created_at=datetime.utcnow(),
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def set_status(self, job_id: str, status: str, step: str, error: str | None = None) -> None:
        job = self._jobs[job_id]
        job.status = status
        job.step = step
        job.error = error

    def set_report(self, job_id: str, report: Report) -> None:
        job = self._jobs[job_id]
        job.report = report
        job.status = "done"
        job.step = "Готово"
