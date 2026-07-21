from pathlib import Path

import pytest
from dotenv import load_dotenv

from src.modules.logger.logger import Logger


load_dotenv(Path(__file__).resolve().parents[1] / ".env.test", override=True)


@pytest.fixture
def log():
    log = Logger()
    yield log
