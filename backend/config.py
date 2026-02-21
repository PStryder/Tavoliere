from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Tavoliere"
    debug: bool = True
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    cors_origins: list[str] = ["*"]

    model_config = {"env_prefix": "TAVOLIERE_"}


settings = Settings()
