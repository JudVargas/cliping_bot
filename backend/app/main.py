"""API de ClipForge (FastAPI).

Endpoints:
- POST /videos (subir archivo) -> crea video y lanza pipeline en segundo plano
- GET /videos, GET /videos/{id}
- GET /videos/{id}/moments, PATCH /moments/{id} (editar start, end, title)
- POST /moments/{id}/render (opciones: estilo de subtitulos, modo de encuadre, quitar silencios)
- GET /clips/{id}/download
- GET /jobs/{id} con estado y progreso (polling)

Un solo worker a la vez (GPU 6 GB). Reanudar desde la ultima etapa completada.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

import app.db as _db_module
from app.models import Video, Moment, Job
from app.jobs import (
    job_queue,
    VIDEO_UPLOADED,
)
from app.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="ClipForge", version="0.1.0")


# ============================================================================
# Schemas (Pydantic)
# ============================================================================

class VideoOut(BaseModel):
    id: int
    filename: str
    status: str
    progress: float
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    error_message: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class MomentOut(BaseModel):
    id: int
    video_id: int
    start: float
    end: float
    title: str
    reason: str
    score: float
    rendered: bool

    class Config:
        from_attributes = True


class MomentPatch(BaseModel):
    start: Optional[float] = None
    end: Optional[float] = None
    title: Optional[str] = None


class JobOut(BaseModel):
    id: int
    video_id: int
    status: str
    stage: str
    progress: float
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class RenderOptions(BaseModel):
    captions_style: Optional[str] = None
    framing_mode: Optional[str] = 'single'
    remove_silence: Optional[bool] = False


# ============================================================================
# Eventos de arranque / parada
# ============================================================================

@app.on_event("startup")
def _startup():
    job_queue.start()


@app.on_event("shutdown")
def _shutdown():
    job_queue.stop()


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/videos", response_model=VideoOut)
async def upload_video(file: UploadFile = File(...)):
    """Subir un video y lanzar el pipeline en segundo plano."""
    data_dir = settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = Path(file.filename).name
    video_path = data_dir / safe_filename

    with video_path.open("wb") as f:
        content = await file.read()
        f.write(content)

    logger.info("Video subido: %s", video_path)

    with Session(_db_module.engine) as session:
        video = Video(
            filename=safe_filename,
            path=str(video_path),
            status=VIDEO_UPLOADED,
            progress=0.0,
        )
        session.add(video)
        session.commit()
        session.refresh(video)
        video_id = video.id

    job_queue.enqueue(video_id)

    return VideoOut(
        id=video.id,
        filename=video.filename,
        status=video.status,
        progress=video.progress,
        duration=video.duration,
        width=video.width,
        height=video.height,
        fps=video.fps,
        error_message=video.error_message,
        created_at=video.created_at.isoformat(),
    )


@app.get("/videos", response_model=List[VideoOut])
def list_videos():
    """Listar todos los videos."""
    with Session(_db_module.engine) as session:
        videos = session.exec(select(Video)).all()
    return [
        VideoOut(
            id=v.id,
            filename=v.filename,
            status=v.status,
            progress=v.progress,
            duration=v.duration,
            width=v.width,
            height=v.height,
            fps=v.fps,
            error_message=v.error_message,
            created_at=v.created_at.isoformat(),
        )
        for v in videos
    ]


@app.get("/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: int):
    """Obtener un video por su ID."""
    with Session(_db_module.engine) as session:
        video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video no encontrado")
    return VideoOut(
        id=video.id,
        filename=video.filename,
        status=video.status,
        progress=video.progress,
        duration=video.duration,
        width=video.width,
        height=video.height,
        fps=video.fps,
        error_message=video.error_message,
        created_at=video.created_at.isoformat(),
    )


@app.get("/videos/{video_id}/moments", response_model=List[MomentOut])
def list_moments(video_id: int):
    """Listar los momentos de un video."""
    with Session(_db_module.engine) as session:
        video = session.get(Video, video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video no encontrado")
        moments = session.exec(
            select(Moment).where(Moment.video_id == video_id)
        ).all()
    return [
        MomentOut(
            id=m.id,
            video_id=m.video_id,
            start=m.start,
            end=m.end,
            title=m.title,
            reason=m.reason,
            score=m.score,
            rendered=m.rendered,
        )
        for m in moments
    ]


@app.patch("/moments/{moment_id}", response_model=MomentOut)
def edit_moment(moment_id: int, patch: MomentPatch):
    """Editar inicio/fin/titulo de un momento."""
    with Session(_db_module.engine) as session:
        moment = session.get(Moment, moment_id)
        if moment is None:
            raise HTTPException(status_code=404, detail="Momento no encontrado")

        if patch.start is not None:
            moment.start = patch.start
        if patch.end is not None:
            moment.end = patch.end
        if patch.title is not None:
            moment.title = patch.title

        session.add(moment)
        session.commit()
        session.refresh(moment)

    return MomentOut(
        id=moment.id,
        video_id=moment.video_id,
        start=moment.start,
        end=moment.end,
        title=moment.title,
        reason=moment.reason,
        score=moment.score,
        rendered=moment.rendered,
    )


@app.post("/moments/{moment_id}/render")
def render_moment(moment_id: int, options: RenderOptions):
    """Renderizar un momento individual a clip."""
    with Session(_db_module.engine) as session:
        moment = session.get(Moment, moment_id)
        if moment is None:
            raise HTTPException(status_code=404, detail="Momento no encontrado")
        video = session.get(Video, moment.video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video no encontrado")

    from app.pipeline.render import render_clip
    from app.pipeline.transcribe import _load_transcript

    data_dir = settings.data_dir / Path(video.path).stem
    clips_dir = data_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    out_name = "clip_{:03d}.mp4".format(moment_id)
    out_path = clips_dir / out_name

    words = None
    audio_path = data_dir / "audio.wav"
    transcript_path = data_dir / "transcript.json"
    if options.captions_style or options.remove_silence:
        if transcript_path.exists():
            transcript = _load_transcript(transcript_path)
            words = [
                w for w in transcript.words
                if w.start >= moment.start and w.end <= moment.end
            ]

    try:
        render_clip(
            video.path,
            moment.start,
            moment.end,
            out_path,
            captions_style=options.captions_style,
            words=words,
            remove_silence=options.remove_silence,
            audio_path=audio_path if audio_path.exists() else None,
        )
    except Exception as exc:
        logger.exception("Render fallo para momento %d: %s", moment_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))

    with Session(_db_module.engine) as session:
        m = session.get(Moment, moment_id)
        m.rendered = True
        session.add(m)
        session.commit()

    return {
        "moment_id": moment_id,
        "clip_path": str(out_path),
        "download_url": "/clips/{}/download".format(moment_id),
    }


@app.get("/clips/{moment_id}/download")
def download_clip(moment_id: int):
    """Descargar el clip renderizado de un momento."""
    with Session(_db_module.engine) as session:
        moment = session.get(Moment, moment_id)
        if moment is None:
            raise HTTPException(status_code=404, detail="Momento no encontrado")
        video = session.get(Video, moment.video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video no encontrado")

    data_dir = settings.data_dir / Path(video.path).stem
    clips_dir = data_dir / "clips"
    out_path = clips_dir / "clip_{:03d}.mp4".format(moment_id)

    if not out_path.exists():
        raise HTTPException(status_code=404, detail="Clip no encontrado o no renderizado")

    return FileResponse(
        path=str(out_path),
        media_type="video/mp4",
        filename="clip_{}.mp4".format(moment_id),
    )


@app.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int):
    """Obtener el estado y progreso de un trabajo."""
    job = job_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado")
    return JobOut(
        id=job.id,
        video_id=job.video_id,
        status=job.status,
        stage=job.stage,
        progress=job.progress,
        error_message=job.error_message,
    )


def cli():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    cli()
