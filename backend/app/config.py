from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    twelve_data_api_key: str = "demo"
    database_url: str = "postgresql+asyncpg://forexlive:forexlive@localhost:5432/forexlive"
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"
    max_connections: int = 100
    max_key_levels_per_session: int = 10

    class Config:
        env_file = ".env"


settings = Settings()
