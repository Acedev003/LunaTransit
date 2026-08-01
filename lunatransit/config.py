"""
Load .env and config
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Settings class
    """
    fr24_api_token: str
    init_zoom_level: int
    init_lat: float
    init_lon: float

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
