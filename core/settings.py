import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USERNAME: str
    RABBITMQ_PASSWORD: str
    ALEMBIC_DATABASE_URL: str
    GOD: str
    LOAN_MAX_AMOUNT: float = 50_000_000
    MEDIA_ROOT: str = str(BASE_DIR / "media")

    model_config = SettingsConfigDict(env_file=ENV_PATH)

settings = Settings()

class CustomFormatter(logging.Formatter):

    def format(self, record):
        RESET = "\033[0m"
        WHITE = "\033[97m"
        LIGHT_BLUE = "\033[94m"
        PINK = "\033[95m"
        GREEN = "\033[92m"

        asctime = self.formatTime(record, self.datefmt)

        level_color = {
            "INFO": LIGHT_BLUE,
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
        }.get(record.levelname, WHITE)

        msg = record.getMessage()

        formatted = (
            f"{GREEN}{asctime}{RESET} "
            f"{level_color}{record.levelname}{RESET} "
            f"{PINK}{record.name}{RESET} "
            f"{WHITE}{msg}{RESET}"
        )


        return formatted

def setup_logging():
    handler = logging.StreamHandler()

    handler.setFormatter(CustomFormatter())

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger

logger = setup_logging()