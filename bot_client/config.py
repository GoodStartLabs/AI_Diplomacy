from pydantic_settings import BaseSettings


class Configuration(BaseSettings):
    DEBUG: bool = False
