import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="bilanco_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["RAW_STORE_DIR"] = f"{_tmp}/raw"
os.environ["MIN_SECONDS_BETWEEN_REQUESTS"] = "0"
os.environ["HTTP_MAX_RETRIES"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.db import init_db, get_session  # noqa: E402
from app.pipeline import seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    init_db()
    with get_session() as db:
        seed(db)
    yield
