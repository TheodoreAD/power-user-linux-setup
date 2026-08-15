"""pip install apscheduler

No class literally named SQLiteJobStore — SQLite persistence comes from SQLAlchemyJobStore pointed
at a sqlite:/// URL. APScheduler 4.x has been in alpha since 2020 with no stable release; 3.x is
the only practical choice. Single-maintainer bus-factor risk is real — see references/rationale.md.
"""

from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler


def send_reminder(to: str) -> str:
    return f"reminder sent to {to}"


def configure_scheduler(db_path: str) -> BackgroundScheduler:
    jobstore = SQLAlchemyJobStore(url=f"sqlite:///{db_path}")
    scheduler = BackgroundScheduler(jobstores={"default": jobstore})
    scheduler.add_job(send_reminder, "interval", minutes=30, id="reminder", args=["a@b.com"])
    return scheduler


def test_scheduled_function_runs_correctly() -> None:
    # Don't exercise the scheduler's timing machinery in a unit test — call the target directly.
    assert send_reminder("a@b.com") == "reminder sent to a@b.com"


def test_scheduler_configures_without_error(tmp_path: Path) -> None:
    scheduler = configure_scheduler(str(tmp_path / "jobs.db"))
    assert scheduler.get_job("reminder") is not None
    scheduler.shutdown(wait=False)
