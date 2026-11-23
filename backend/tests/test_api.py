"""Pruebas de la Etapa 8: API y cola de trabajos.

Usan SQLite temporal y TestClient de FastAPI (sin servidor real ni ffmpeg).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

import app.db as db_module
from app.db import init_db
from app.models import Video, Moment, Job
from app.jobs import job_queue, JobStatus
from app.main import app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clean_db(tmp_path):
    """Usar una base de datos SQLite temporal para cada test."""
    db_file = tmp_path / "test.sqlite3"
    db_module.DB_PATH = db_file
    db_module.engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    init_db()
    yield
    job_queue.stop()


@pytest.fixture
def client():
    return TestClient(app)


# ============================================================================
# Tests de modelos y DB
# ============================================================================

def test_video_model_crud():
    """Video debe poder crearse, leerse y actualizarse."""
    with Session(db_module.engine) as session:
        v = Video(
            filename="test.mp4",
            path="/data/test.mp4",
            status="uploaded",
            progress=0.0,
        )
        session.add(v)
        session.commit()
        session.refresh(v)

        assert v.id is not None
        assert v.filename == "test.mp4"
        assert v.status == "uploaded"

        # Leer
        v2 = session.get(Video, v.id)
        assert v2 is not None
        assert v2.filename == "test.mp4"

        # Actualizar
        v2.status = "ready"
        v2.progress = 100.0
        session.add(v2)
        session.commit()

        v3 = session.get(Video, v.id)
        assert v3.status == "ready"
        assert v3.progress == 100.0


def test_moment_model_crud():
    """Moment debe poder crearse y leerse."""
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="ready")
        session.add(v)
        session.commit()
        session.refresh(v)

        m = Moment(
            video_id=v.id,
            start=10.0,
            end=30.0,
            title="Momento 1",
            reason="Buen remate",
            score=8.5,
        )
        session.add(m)
        session.commit()
        session.refresh(m)

        assert m.id is not None
        assert m.video_id == v.id
        assert m.score == 8.5

        m2 = session.get(Moment, m.id)
        assert m2.title == "Momento 1"


def test_job_model_crud():
    """Job debe poder crearse y leerse."""
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="uploaded")
        session.add(v)
        session.commit()
        session.refresh(v)

        j = Job(
            video_id=v.id,
            status="pending",
            stage="ingest",
            progress=0.0,
        )
        session.add(j)
        session.commit()
        session.refresh(j)

        assert j.id is not None
        assert j.status == "pending"

        j2 = session.get(Job, j.id)
        assert j2.stage == "ingest"


# ============================================================================
# Tests de JobQueue
# ============================================================================

def test_job_queue_enqueue_and_get():
    """JobQueue.enqueue debe crear un job y get_job debe recuperarlo."""
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="uploaded")
        session.add(v)
        session.commit()
        session.refresh(v)
        video_id = v.id

    job_id = job_queue.enqueue(video_id)
    assert job_id is not None

    job = job_queue.get_job(job_id)
    assert job is not None
    assert job.video_id == video_id
    assert job.status == JobStatus.PENDING


def test_job_queue_get_video():
    """JobQueue.get_video debe devolver el video asociado."""
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="uploaded")
        session.add(v)
        session.commit()
        session.refresh(v)
        video_id = v.id

    job_id = job_queue.enqueue(video_id)
    video = job_queue.get_video(video_id)
    assert video is not None
    assert video.id == video_id


# ============================================================================
# Tests de la API (TestClient)
# ============================================================================

def test_upload_video_api(client, tmp_path, monkeypatch):
    """POST /videos debe crear un video y devolverlo."""
    import app.main as main_module

    # Crear un objeto settings simulado con data_dir apuntando a tmp_path
    class FakeSettings:
        data_dir = tmp_path

    monkeypatch.setattr(main_module, "settings", FakeSettings())

    # Crear un archivo de video falso
    video_file = tmp_path / "test_video.mp4"
    video_file.write_bytes(b"fake video content")

    with open(video_file, "rb") as f:
        response = client.post("/videos", files={"file": ("test_video.mp4", f, "video/mp4")})

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["filename"] == "test_video.mp4"
    assert data["status"] == "uploaded"
    assert data["progress"] == 0.0
    assert "id" in data


def test_list_videos_api(client):
    """GET /videos debe devolver la lista de videos."""
    response = client.get("/videos")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_video_api(client):
    """GET /videos/{id} debe devolver el video o 404."""
    # Primero crear un video directamente en DB
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="ready")
        session.add(v)
        session.commit()
        session.refresh(v)
        video_id = v.id

    response = client.get("/videos/{}".format(video_id))
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == video_id
    assert data["filename"] == "test.mp4"

    # 404 para video inexistente
    response = client.get("/videos/99999")
    assert response.status_code == 404


def test_list_moments_api(client):
    """GET /videos/{id}/moments debe devolver los momentos."""
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="ready")
        session.add(v)
        session.commit()
        session.refresh(v)
        video_id = v.id

        m = Moment(
            video_id=video_id,
            start=10.0,
            end=30.0,
            title="Momento",
            reason="Buen remate",
            score=8.0,
        )
        session.add(m)
        session.commit()

    response = client.get("/videos/{}/moments".format(video_id))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Momento"


def test_edit_moment_api(client):
    """PATCH /moments/{id} debe editar el momento."""
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="ready")
        session.add(v)
        session.commit()
        session.refresh(v)

        m = Moment(
            video_id=v.id,
            start=10.0,
            end=30.0,
            title="Viejo",
            reason="R",
            score=5.0,
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        moment_id = m.id

    response = client.patch(
        "/moments/{}".format(moment_id),
        json={"start": 12.0, "title": "Nuevo titulo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["start"] == 12.0
    assert data["title"] == "Nuevo titulo"
    assert data["end"] == 30.0  # sin cambios


def test_get_job_api(client):
    """GET /jobs/{id} debe devolver el estado del trabajo."""
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="uploaded")
        session.add(v)
        session.commit()
        session.refresh(v)

        j = Job(video_id=v.id, status="running", stage="transcribe", progress=50.0)
        session.add(j)
        session.commit()
        session.refresh(j)
        job_id = j.id

    response = client.get("/jobs/{}".format(job_id))
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["status"] == "running"
    assert data["progress"] == 50.0


def test_download_clip_not_found(client):
    """GET /clips/{id}/download debe devolver 404 si no existe el clip."""
    with Session(db_module.engine) as session:
        v = Video(filename="test.mp4", path="/data/test.mp4", status="ready")
        session.add(v)
        session.commit()
        session.refresh(v)

        m = Moment(
            video_id=v.id,
            start=10.0,
            end=30.0,
            title="Momento",
            reason="R",
            score=5.0,
        )
        session.add(m)
        session.commit()
        session.refresh(m)
        moment_id = m.id

    response = client.get("/clips/{}/download".format(moment_id))
    assert response.status_code == 404


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
