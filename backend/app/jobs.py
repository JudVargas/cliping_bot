"""Cola de trabajos en proceso (sin Redis/Celery).

Un solo worker a la vez (la GPU tiene 6 GB VRAM). Ejecuta el pipeline
etapa por etapa y permite reanudar desde la última etapa completada si el
proceso se reinicia.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

import app.db as _db_module
from app.db import init_db
from app.models import Video, Job, Moment
from app.pipeline.ingest import ingest
from app.pipeline.transcribe import transcribe
from app.pipeline.moments import select_moments
from app.pipeline.render import render_all_from_moments
from app.config import settings

logger = logging.getLogger(__name__)

# Estados del video
VIDEO_UPLOADED = "uploaded"
VIDEO_TRANSCRIBING = "transcribing"
VIDEO_FINDING_MOMENTS = "finding_moments"
VIDEO_READY = "ready"
VIDEO_ERROR = "error"

# Etapas del pipeline
STAGE_INGEST = "ingest"
STAGE_TRANSCRIBE = "transcribe"
STAGE_MOMENTS = "moments"
STAGE_RENDER = "render"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class JobQueue:
    """Cola de trabajos con un solo worker en segundo plano."""

    def __init__(self):
        self._queue: list[int] = []
        self._current_job_id: Optional[int] = None
        self._lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        init_db()
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("JobQueue worker iniciado")

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)

    def enqueue(self, video_id: int) -> int:
        with Session(_db_module.engine) as session:
            job = Job(video_id=video_id, status=JobStatus.PENDING, stage="")
            session.add(job)
            session.commit()
            session.refresh(job)
            job_id = job.id

        with self._lock:
            self._queue.append(job_id)

        logger.info("Trabajo %d encolado para video %d", job_id, video_id)
        return job_id

    def get_job(self, job_id: int) -> Optional[Job]:
        with Session(_db_module.engine) as session:
            return session.get(Job, job_id)

    def get_video(self, video_id: int) -> Optional[Video]:
        with Session(_db_module.engine) as session:
            return session.get(Video, video_id)

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            job_id: Optional[int] = None
            with self._lock:
                if self._queue:
                    job_id = self._queue.pop(0)
                    self._current_job_id = job_id

            if job_id is None:
                self._stop_event.wait(1.0)
                continue

            self._process_job(job_id)

            with self._lock:
                self._current_job_id = None

    def _process_job(self, job_id: int) -> None:
        logger.info("Procesando trabajo %d", job_id)

        with Session(_db_module.engine) as session:
            job = session.get(Job, job_id)
            if job is None:
                logger.error("Trabajo %d no encontrado", job_id)
                return

            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            session.add(job)
            session.commit()

            video = session.get(Video, job.video_id)
            if video is None:
                job.status = JobStatus.ERROR
                job.error_message = f"Video {job.video_id} no encontrado"
                session.add(job)
                session.commit()
                return

        current_stage: Optional[str] = None
        try:
            video_id_stem = Path(video.path).stem
            data_dir = settings.data_dir / video_id_stem

            # Etapa 1: Ingesta si no está hecha
            if video.status == VIDEO_UPLOADED:
                current_stage = STAGE_INGEST
                self._update_job_stage(job_id, STAGE_INGEST, 10)
                self._update_video_status(video.id, VIDEO_TRANSCRIBING, 10)
                info, audio_path = ingest(video.path)
                with Session(_db_module.engine) as session:
                    v = session.get(Video, video.id)
                    v.duration = info.duration
                    v.width = info.width
                    v.height = info.height
                    v.fps = info.fps
                    session.add(v)
                    session.commit()

            # Etapa 2: Transcripción si no existe transcript.json
            transcript_path = data_dir / "transcript.json"
            if not transcript_path.exists():
                current_stage = STAGE_TRANSCRIBE
                self._update_job_stage(job_id, STAGE_TRANSCRIBE, 40)
                self._update_video_status(video.id, VIDEO_TRANSCRIBING, 40)
                transcribe(video.path)

            # Etapa 3: Selección de momentos si no existe moments.json
            moments_path = data_dir / "moments.json"
            if not moments_path.exists():
                current_stage = STAGE_MOMENTS
                self._update_job_stage(job_id, STAGE_MOMENTS, 70)
                self._update_video_status(video.id, VIDEO_FINDING_MOMENTS, 70)
                select_moments(video_id_stem)

            # Cargar momentos (desde cache si existe) y guardar en BD para la API
            moments = select_moments(video_id_stem)
            with Session(_db_module.engine) as session:
                existing = session.exec(
                    select(Moment).where(Moment.video_id == video.id)
                ).all()
                if not existing:
                    for m in moments:
                        db_moment = Moment(
                            video_id=video.id,
                            start=m.start,
                            end=m.end,
                            title=m.title,
                            reason=m.reason,
                            score=m.score,
                        )
                        session.add(db_moment)
                    session.commit()

            # Etapa 4: Render de clips
            current_stage = STAGE_RENDER
            self._update_job_stage(job_id, STAGE_RENDER, 90)
            self._update_video_status(video.id, VIDEO_READY, 90)
            render_all_from_moments(video_id_stem)

            # Marcar como listo
            with Session(_db_module.engine) as session:
                v = session.get(Video, video.id)
                v.status = VIDEO_READY
                v.progress = 100.0
                v.updated_at = datetime.now(timezone.utc)
                session.add(v)

                j = session.get(Job, job_id)
                j.status = JobStatus.DONE
                j.progress = 100.0
                j.completed_at = datetime.now(timezone.utc)
                session.add(j)
                session.commit()

            logger.info("Trabajo %d completado para video %d", job_id, video.id)

        except Exception as exc:
            logger.exception("Trabajo %d fallo: %s", job_id, exc)
            with Session(_db_module.engine) as session:
                j = session.get(Job, job_id)
                j.status = JobStatus.ERROR
                j.error_message = str(exc)
                j.completed_at = datetime.now(timezone.utc)
                session.add(j)

                v = session.get(Video, job.video_id)
                if v:
                    v.status = VIDEO_ERROR
                    v.error_message = str(exc)
                    v.error_stage = current_stage
                    session.add(v)
                session.commit()

    def _update_job_stage(self, job_id: int, stage: str, progress: float) -> None:
        with Session(_db_module.engine) as session:
            j = session.get(Job, job_id)
            if j:
                j.stage = stage
                j.progress = progress
                session.add(j)
                session.commit()

    def _update_video_status(self, video_id: int, status: str, progress: float) -> None:
        with Session(_db_module.engine) as session:
            v = session.get(Video, video_id)
            if v:
                v.status = status
                v.progress = progress
                v.updated_at = datetime.now(timezone.utc)
                session.add(v)
                session.commit()


job_queue = JobQueue()

__all__ = ["job_queue", "JobQueue", "JobStatus", "VIDEO_READY", "VIDEO_ERROR"]
