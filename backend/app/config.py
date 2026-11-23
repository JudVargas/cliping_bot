"""Lectura de configuración desde variables de entorno (.env).

Usa pydantic-settings para cargar .env con validación y valores por defecto.
Nunca se escriben claves API ni rutas hardcodeadas en este módulo.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM (cliente compatible con OpenAI) ---
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # --- Whisper (transcripción) ---
    WHISPER_MODEL: str = "medium"
    WHISPER_COMPUTE: str = "int8_float16"
    WHISPER_LANGUAGE: str = "es"

    # --- Datos ---
    DATA_DIR: str = "./data"

    # --- Video ---
    VIDEO_ENCODER: str = "h264_nvenc"

    @property
    def data_dir(self) -> Path:
        """Devuelve la ruta absoluta del directorio de datos."""
        return Path(self.DATA_DIR).resolve()


# Instancia singleton de configuración
settings = Settings()
