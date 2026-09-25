import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./bugforge.db"   # override with DATABASE_URL env var for Postgres
    LLM_PROVIDER: str = "openai"          # "openai" or "watsonx"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    WATSONX_PROJECT_ID: str = ""
    WATSONX_API_URL: str = "https://us-south.ml.cloud.ibm.com"
    DOCKER_SOCKET_PATH: str = "/var/run/docker.sock"
    LLM_REPORT_NARRATIVE: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
