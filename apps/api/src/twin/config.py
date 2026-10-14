from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "persona.yaml").exists():
            return parent
    return Path.cwd()


REPO_ROOT = _find_repo_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        extra="ignore",
    )

    env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://twin:change-me@localhost:5432/twin"

    # LLM providers: OpenAI is primary, DeepSeek is the fallback.
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_fast_model: str = "gpt-4.1-nano"
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 30.0
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Voice (OpenAI speech-to-text and text-to-speech)
    stt_model: str = "gpt-4o-mini-transcribe"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "ash"
    max_audio_bytes: int = 8 * 1024 * 1024
    max_tts_chars: int = 3_000

    # Optional Langfuse tracing (cloud or self-hosted)
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"

    knowledge_dir: Path = REPO_ROOT / "knowledge"
    persona_path: Path = REPO_ROOT / "persona.yaml"

    admin_token: SecretStr | None = None
    cors_origins: str = ""
    # Key for hashing client IPs (rate limits, session fingerprint).
    ip_hash_secret: SecretStr | None = None

    # Abuse protection
    rate_limit_per_minute: int = 12
    rate_limit_per_day: int = 200
    session_max_messages: int = 40
    session_max_tokens: int = 150_000
    # Chat messages may carry a pasted job description (job_fit intent).
    max_message_chars: int = 12_000
    max_job_description_chars: int = 12_000
    # Circuit breaker on LLM + speech spend per UTC day (0 disables it).
    daily_budget_usd: float = 5.0

    # WhatsApp (Evolution API)
    whatsapp_bot_number: str | None = None
    whatsapp_owner_number: str | None = None
    evolution_api_url: str | None = None
    evolution_api_key: SecretStr | None = None
    evolution_instance: str | None = None
    evolution_webhook_token: SecretStr | None = None
    whatsapp_debounce_seconds: float = 2.5
    whatsapp_rate_per_minute: int = 8
    whatsapp_rate_per_day: int = 150
    # A WhatsApp chat idle for longer than this starts a new interview.
    whatsapp_session_idle_hours: float = 12
    # Idle web/widget/WhatsApp interviews are closed (and summarized) after this.
    session_idle_minutes: int = 90

    # Public base URL (e.g. https://1-2-3-4.sslip.io), used in owner notifications.
    public_url: str | None = None

    @property
    def whatsapp_enabled(self) -> bool:
        return bool(
            self.evolution_api_url
            and self.evolution_api_key
            and self.evolution_instance
            and self.evolution_webhook_token
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def psycopg_url(self) -> str:
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
