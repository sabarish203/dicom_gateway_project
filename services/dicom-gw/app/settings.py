from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DICOM Gateway"
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
