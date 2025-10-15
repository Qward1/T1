from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional, Sequence

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .settings import get_settings

Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender = Column(String(16), nullable=False)
    text = Column(Text, nullable=False)
    category = Column(String(128), nullable=True)
    subcategory = Column(String(128), nullable=True)
    template_answer = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


_ENGINE: Optional[Engine] = None
SessionLocal: sessionmaker[Session] | None = None


def _build_engine() -> Engine:
    settings = get_settings()
    db_path = settings.chat_database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    return engine


def init_chat_storage() -> None:
    global _ENGINE, SessionLocal
    if _ENGINE is None:
        _ENGINE = _build_engine()
        SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
        Base.metadata.create_all(_ENGINE, checkfirst=True)


@contextmanager
def _session_scope() -> Generator[Session, None, None]:
    if SessionLocal is None:
        init_chat_storage()
    assert SessionLocal is not None  # for mypy
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def persist_messages(messages: Sequence[ChatMessage]) -> List[ChatMessage]:
    if not messages:
        return []
    with _session_scope() as session:
        session.add_all(messages)
        session.flush()
        for message in messages:
            session.refresh(message)
        return list(messages)


def list_messages() -> List[ChatMessage]:
    with _session_scope() as session:
        rows = session.execute(select(ChatMessage).order_by(ChatMessage.id.asc()))
        return [row[0] for row in rows]


def delete_all_messages() -> None:
    with _session_scope() as session:
        session.execute(delete(ChatMessage))
