"""
app/db/session.py — SQLAlchemy engine, session factory, declarative base,
and the `get_db()` FastAPI dependency that every router/service uses to
talk to Postgres.

The actual DDL (tables, constraints, indexes) lives in `sql/01_schema.sql`
and is applied directly via psql — that file, not this module, is the
source of truth for the schema. The ORM models under `app/models/` mirror
it for querying and CRUD; nothing here calls `Base.metadata.create_all()`.
"""
import os
from collections.abc import Generator

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Settings(BaseSettings):
    """App configuration, read from the process environment / `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "ecommerce"
    postgres_password: str = "change_me"
    postgres_db: str = "ecommerce"
    # Deliberately NOT named postgres_host/postgres_port: `.env` already
    # defines POSTGRES_HOST=db / POSTGRES_PORT=5432 for the Docker-internal
    # target, and pydantic-settings matches field names to env vars
    # case-insensitively — using those names here would silently pick up
    # the container-only host/port for local runs too. `_external` matches
    # the POSTGRES_HOST_EXTERNAL/POSTGRES_PORT_EXTERNAL convention already
    # used by app/db/seed.py and app/db/reconcile.py for the same reason.
    postgres_host_external: str = "localhost"
    postgres_port_external: str = "5435"

    @property
    def sqlalchemy_database_url(self) -> str:
        # A real DATABASE_URL exported into the process environment always
        # wins — this is how docker-compose.yml wires up the containerized
        # `app` service (`db:5432` over the Docker network). We check
        # os.environ directly rather than adding a dotenv-backed field for
        # it: `.env`'s own DATABASE_URL line is that same Docker-internal
        # value, and if pydantic-settings read it here too it would silently
        # break every local (non-Docker) run of the API.
        if url := os.environ.get("DATABASE_URL"):
            return url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host_external}:{self.postgres_port_external}/{self.postgres_db}"
        )


settings = Settings()

engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    """Shared declarative base — every model in `app/models/` inherits this."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields one request-scoped session, always closed.

    Usage: `def route(db: Session = Depends(get_db)): ...`
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
