"""pip install huey

immediate=True runs @huey.task() functions synchronously in-process — no consumer subprocess
needed, in-memory storage automatically. Real usage points filename= at a real db path and runs
`huey_consumer app.huey` as a separate process instead.
"""

from huey import SqliteHuey

huey: SqliteHuey = SqliteHuey("app", immediate=True)


@huey.task()
def send_email(to: str) -> str:
    return f"sent to {to}"


def test_task_runs_immediately() -> None:
    result = send_email("a@b.com")
    # .get() blocks until the result is ready — in immediate mode it already is, but the call
    # is the same one you'd use against a real consumer process.
    assert result.get() == "sent to a@b.com"
