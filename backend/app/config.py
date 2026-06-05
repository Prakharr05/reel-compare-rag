from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    openai_api_key: str | None = None
    deepgram_api_key: str | None = None
    apify_api_token: str | None = None

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    redis_url: str = "redis://localhost:6379/0"

    # yt-dlp anonymous downloads increasingly hit 403 from YouTube's
    # anti-bot detection. Setting this to 'chrome' / 'edge' / 'firefox'
    # tells yt-dlp to read cookies from the local browser, which makes
    # requests indistinguishable from the developer's normal browsing.
    # Unset in production; use a managed cookies.txt refresh instead.
    yt_dlp_cookies_browser: str | None = None


settings = Settings()