"""pip install sqlalchemy alembic

Real multi-table joins + migrations. Alembic is a CLI scaffold, not importable inline:

    alembic init migrations
    alembic revision --autogenerate -m "..."
    alembic upgrade head

driven by migrations/env.py pointed at this file's Base.metadata.
"""

from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))


def test_insert_and_query() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(name="widget"))
        session.commit()
        # select()/scalar_one() is the current SQLAlchemy 2.0 style — prefer it over the legacy
        # session.query(...) API in new code.
        user = session.execute(select(User).filter_by(name="widget")).scalar_one()
        assert user.name == "widget"
