from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from core.settings import settings

# NullPool: don't hold a fixed-size connection pool. Services create a session per RPC
# and many read paths never commit/close, which exhausted the default QueuePool under
# load. With NullPool there is no pool limit and the connection is released when the
# short-lived per-RPC service (and its session) is garbage-collected.
engine = create_engine(
    settings.ALEMBIC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    return SessionLocal()