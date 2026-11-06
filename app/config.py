from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "local-dev-secret-change-me"
    database_url: str = "sqlite:///./labflow.db"
    report_link_ttl_hours: int = 72
    otp_ttl_minutes: int = 5
    ai_api_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
