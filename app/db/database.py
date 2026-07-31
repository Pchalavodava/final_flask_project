from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

from contextlib import contextmanager
from config import settings

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

db_path = BASE_DIR / "bookstore.db"

engine = create_engine(f"sqlite:///{db_path}")

SessionLocal = scoped_session(sessionmaker(autocommit=False, bind=engine, autoflush=False, expire_on_commit=False))

Base = declarative_base()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
