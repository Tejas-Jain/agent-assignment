import json
import shutil

import pytest

from app.tools import store


@pytest.fixture(autouse=True)
def isolated_live_buyers(tmp_path):
    live = tmp_path / "buyers.json"
    shutil.copy(store.SEED_BUYERS_PATH, live)
    store.LIVE_BUYERS_PATH = live
    store.reload()
    yield
    store.reload()
