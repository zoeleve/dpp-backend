from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DPP Management Platform"
    app_env: str
    app_host: str
    app_port: int
    db_user: str
    db_pass: str
    db_host: str
    db_port: str
    db_name: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    log_level: str

    class Config:
        env_file = ".env"


settings = Settings()
