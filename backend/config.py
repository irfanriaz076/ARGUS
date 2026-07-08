from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://argus:argus@postgres:5432/argus"
    REDIS_URL: str = "redis://redis:6379/0"
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "argus_neo4j_pass"
    NVD_API_KEY: str = ""
    SHODAN_API_KEY: str = ""
    GITHUB_TOKEN: str = ""

    # LLM narrative — OpenAI-compatible endpoint (GitHub Models by default).
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://models.inference.ai.azure.com"
    LLM_MODEL: str = "gpt-4o-mini"

    SECRET_KEY: str = "change-me-in-production"
    ENVIRONMENT: str = "development"
    TMP_DIR: str = "/tmp/argus"

    model_config = {"env_file": ".env"}


settings = Settings()
