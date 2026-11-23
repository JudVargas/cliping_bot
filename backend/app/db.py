"""Conexión a la base de datos SQLite con SQLModel.

Inicializa el motor y crea las tablas al importar el módulo.
"""

from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session

from app.config import settings

# Ruta del archivo SQLite dentro de data/
DB_PATH = settings.data_dir / "clipforge.sqlite3"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    """Crear todas las tablas definidas en models.py."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Obtener una sesión de base de datos (usar como context manager)."""
    return Session(engine)
