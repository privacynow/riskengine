import logging
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "risk_engine_db")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD: str = ""

CONFIG_HELP = (
    "Set DB_PASSWORD (and other DB_* vars as needed). "
    "Docker Compose sets these for local demo."
)


def validate_config() -> None:
    global DB_PASSWORD
    password = os.environ.get("DB_PASSWORD")
    if not password:
        raise RuntimeError(f"Missing DB_PASSWORD. {CONFIG_HELP}")
    DB_PASSWORD = password

APP_TITLE = "Decision Engine"
LOGGER_NAME = "decision-engine"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
)
logger = logging.getLogger(LOGGER_NAME)
