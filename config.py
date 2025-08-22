import datetime
from typing import Optional
from pydantic_settings import BaseSettings
from pathlib import Path
import warnings
from models import PowerEnum


class Configuration(BaseSettings):
    DEBUG: bool = False
    log_file_path: Path | None = None
    USE_UNFORMATTED_PROMPTS: bool = False
    SIMPLE_PROMPTS: bool = True
    COUNTRY_SPECIFIC_PROMPTS: bool = False

    # Default models for tasks
    AI_DIPLOMACY_NARRATIVE_MODEL: str = "openrouter-google/gemini-2.5-flash-preview-05-20"
    AI_DIPLOMACY_FORMATTER_MODEL: str = "openrouter-google/gemini-2.5-flash-preview-05-20"

    # API Keys to be validated. Warns if they aren't present at startup, raises ValueError if you attempt to use them when they aren't present.
    DEEPSEEK_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    TOGETHER_API_KEY: str | None = None

    def __init__(self, power_name: Optional[PowerEnum] = None, **kwargs):
        super().__init__(**kwargs)
        # Add a '-POWER' to the end of the file name if it's for a specific power
        log_power_path = "-" + power_name if power_name else None
        self.log_file_path = Path(f"./logs/{datetime.datetime.now().strftime('%d-%m-%y_%H:%M')}/logs{log_power_path} .txt")
        # Make the path absolute, gets rid of weirdness of calling this in different places
        self.log_file_path = self.log_file_path.resolve()
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file_path.touch(exist_ok=True)

        self._validate_api_keys()

    def _validate_api_keys(self):
        """Validate API keys at startup and issue warnings for missing keys"""
        api_keys = [
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "OPENROUTER_API_KEY",
        ]

        for key in api_keys:
            value = super().__getattribute__(key)
            if not value or (isinstance(value, str) and len(value) == 0):
                warnings.warn(f"API key '{key}' is not set or is empty", UserWarning)

    def __getattribute__(self, name):
        """Override to check for empty API keys at access time"""
        value = super().__getattribute__(name)

        # If this is a _KEY, it must be not None, string, and length > 0 to return. We do not validate the correctness of the key.
        # e.g. "thisIsAKey" is valid in this sense.
        if name.endswith("_KEY") and (not value or (isinstance(value, str) and len(value) == 0)):
            raise ValueError(f"API key '{name}' is not set or is empty. Please configure it before use.")

        return value


config = Configuration()
