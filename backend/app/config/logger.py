import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Project root logs directory
root_dir = Path(__file__).resolve().parent.parent.parent.parent
LOGS_DIR = root_dir / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Formatter
log_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def create_rotating_handler(filename: str, level=logging.INFO) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        str(LOGS_DIR / filename),
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=5,
        encoding="utf-8"
    )
    handler.setLevel(level)
    handler.setFormatter(log_formatter)
    return handler


# 1. API Logger
api_logger = logging.getLogger("crowdeye.api")
api_logger.setLevel(logging.INFO)
api_logger.addHandler(create_rotating_handler("api.log"))

# 2. AI Inference Logger
ai_logger = logging.getLogger("crowdeye.ai_worker")
ai_logger.setLevel(logging.INFO)
ai_logger.addHandler(create_rotating_handler("ai_worker.log"))

# 3. Database Logger
db_logger = logging.getLogger("crowdeye.database")
db_logger.setLevel(logging.INFO)
db_logger.addHandler(create_rotating_handler("database.log"))

# 4. Authentication Logger
auth_logger = logging.getLogger("crowdeye.auth")
auth_logger.setLevel(logging.INFO)
auth_logger.addHandler(create_rotating_handler("auth.log"))

# Ensure root console handler remains active
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logging.getLogger("crowdeye").addHandler(console_handler)
