"""Modelos de datos para la base de datos (SQLModel + SQLite).

Estados del video: uploaded, transcribing, finding_moments, ready, error.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Video(SQLModel, table=True):
    """Un video subido por el usuario y sus metadatos de procesamiento."""

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(index=True)  # nombre original del archivo
    path: str  # ruta absoluta al video en data/
    status: str = "uploaded"  # uploaded | transcribing | finding_moments | ready | error
    progress: float = 0.0  # 0-100
    duration: Optional[float] = None  # segundos
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class Moment(SQLModel, table=True):
    """Un momento candidato seleccionado por el LLM."""

    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(index=True, foreign_key="video.id")
    start: float  # segundos relativos al video original
    end: float
    title: str
    reason: str
    score: float  # 0-10
    rendered: bool = False  # si ya se exportó el clip
    created_at: datetime = Field(default_factory=_now)


class Job(SQLModel, table=True):
    """Un trabajo de procesamiento en la cola."""

    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(index=True, foreign_key="video.id")
    status: str = "pending"  # pending | running | done | error
    stage: str = ""  # ingest | transcribe | moments | render | ...
    progress: float = 0.0  # 0-100
    created_at: datetime = Field(default_factory=_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
