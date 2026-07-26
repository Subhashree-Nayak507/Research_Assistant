from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET_KEY: str = "dev_secret_change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DATABASE_URL: str = ""

    TAVILY_API_KEY: str = ""
    TAVILY_MAX_RESULTS: int = 5

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash" 
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"

    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5174"

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self):
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
