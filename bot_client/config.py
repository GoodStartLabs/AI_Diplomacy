from pydantic_settings import BaseSettings
from pathlib import Path


class Configuration(BaseSettings):
    DEBUG: bool = False
    log_file_path: Path = Path("./logs/")
