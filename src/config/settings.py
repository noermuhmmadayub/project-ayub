import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


load_dotenv()


SYSTEM_INSTRUCTION = """
Anda adalah Academic Assistant untuk Program Studi Teknik Informatika STT Terpadu Nurul Fikri.
Tugas Anda:
1) Menjawab pertanyaan pelajaran secara edukatif, sopan, dan akurat.
2) Gunakan bahasa Indonesia yang jelas, terstruktur, dan mudah dipahami mahasiswa.
3) Jika pertanyaan ambigu, ajukan klarifikasi sebelum menjawab.
4) Untuk topik teknis (pemrograman, jaringan, AI, basis data), berikan contoh praktis singkat.
5) Jangan mengarang fakta. Jika tidak yakin, katakan keterbatasan dan sarankan referensi belajar.
"""


@dataclass(frozen=True)
class Settings:
    app_name: str
    gemini_api_key: str
    db_path: str
    model_name: str = "gemini-2.5-flash"
    fallback_models: List[str] | None = None
    max_retry_attempts: int = 2
    retry_delay_seconds: float = 1.2
    embedding_model_name: str = "text-embedding-004"
    auth_secret_key: str = "change-this-auth-secret"


def get_settings() -> Settings:
    app_name = os.getenv("APP_NAME", "Chatbot Konsultasi Pelajaran STT-NF")
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    db_path = os.getenv("DB_PATH", "data/app.db")
    model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    fallback_models_env = os.getenv("FALLBACK_MODELS", "gemini-2.0-flash,gemini-flash-latest")
    fallback_models = [item.strip() for item in fallback_models_env.split(",") if item.strip()]
    max_retry_attempts = int(os.getenv("MAX_RETRY_ATTEMPTS", "2"))
    retry_delay_seconds = float(os.getenv("RETRY_DELAY_SECONDS", "1.2"))
    embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-004")
    auth_secret_key = os.getenv("AUTH_SECRET_KEY", "change-this-auth-secret")
    return Settings(
        app_name=app_name,
        gemini_api_key=gemini_api_key,
        db_path=db_path,
        model_name=model_name,
        fallback_models=fallback_models,
        max_retry_attempts=max_retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
        embedding_model_name=embedding_model_name,
        auth_secret_key=auth_secret_key,
    )
