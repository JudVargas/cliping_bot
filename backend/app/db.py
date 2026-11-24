"""Conexión a la base de datos SQLite con SQLModel.

Inicializa el motor y crea las tablas al importar el módulo.
"""

from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session, text

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
    """Crear todas las tablas definidas en models.py y asegurar columnas faltantes."""
    SQLModel.metadata.create_all(engine)
    _ensure_columns()


def _ensure_columns() -> None:
    """Agregar columnas faltantes a tablas existentes (migración ligera).

    SQLite no soporta ALTER TABLE ADD COLUMN IF NOT EXISTS de forma nativa
    en versiones antiguas, así que verificamos primero si la columna existe.
    """
    with engine.connect() as conn:
        # Verificar si la columna error_stage ya existe en la tabla video
        result = conn.execute(
            text(
                "SELECT name FROM pragma_table_info('video') "
                "WHERE name='error_stage'"
            )
        )
        if result.fetchone() is None:
            conn.execute(
                text("ALTER TABLE video ADD COLUMN error_stage TEXT")
            )
            conn.commit()


def get_session() -> Session:
    """Obtener una sesión de base de datos (usar como context manager)."""
    return Session(engine)
