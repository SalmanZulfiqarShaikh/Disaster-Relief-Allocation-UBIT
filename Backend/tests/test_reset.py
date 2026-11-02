
import pytest

from core import config
from data import areas
from data import seed as seed_module
from scripts import reset_demo
from tests.fake_db import FakeDB


@pytest.fixture
def db(monkeypatch):
    database = FakeDB()
    monkeypatch.setattr("core.db.get_db", lambda: database)
    monkeypatch.setattr("core.db.execute", lambda query: query.execute())
    monkeypatch.setattr(seed_module, "get_db", lambda: database)
    monkeypatch.setattr(seed_module, "execute", lambda query: query.execute())
    monkeypatch.setattr(config, "MOCK_MODE", True)
    return database


def populated(db):
    db.tables["volunteers"].append(
        {
            "id": 1,
            "name": "Demo volunteer A",
            "phone": "923000000001",
            "zone_ids": ["johar"],
            "capabilities": ["foot"],
            "status": "on_duty",
        }
    )
    db.tables["incidents"].append({"id": 10, "category": "flood", "status": "open"})
    db.tables["cases"].append({"id": 11, "incident_id": 10, "status": "proposed"})
    db.tables["reports"].append({"id": 12, "incident_id": 10})
    db.tables["people"].append({"id": 13, "phone": "923000000009"})
    return db


def test_volunteers_are_cleared_by_default(db):
    populated(db)

    reset_demo.main(["--yes", "--no-seed"])

    assert db.tables["volunteers"] == []


def test_keep_volunteers_leaves_them_alone(db):
    populated(db)

    reset_demo.main(["--yes", "--no-seed", "--keep-volunteers"])

    assert len(db.tables["volunteers"]) == 1


def test_keep_volunteers_preserves_on_duty_status(db):
    populated(db)

    reset_demo.main(["--yes", "--no-seed", "--keep-volunteers"])

    assert db.tables["volunteers"][0]["status"] == "on_duty"


def test_keep_volunteers_still_clears_the_queue(db):
    populated(db)

    reset_demo.main(["--yes", "--no-seed", "--keep-volunteers"])

    assert db.tables["cases"] == []
    assert db.tables["incidents"] == []
    assert db.tables["reports"] == []
    assert db.tables["people"] == []


def test_nothing_is_deleted_without_yes(db):
    populated(db)

    code = reset_demo.main([])

    assert code == 1
    assert len(db.tables["cases"]) == 1


def test_re_seeding_does_not_reset_duty_status(db):
    populated(db)
    db.tables["volunteers"][0]["phone"] = seed_module.volunteer_plan()[0]["phone"]

    reset_demo.main(["--yes", "--keep-volunteers", "--no-samples"])

    kept = [v for v in db.tables["volunteers"] if v["status"] == "on_duty"]
    assert kept


def test_no_samples_leaves_the_queue_empty(db):
    reset_demo.main(["--yes", "--no-samples"])

    assert db.tables["cases"] == []
    assert db.tables["incidents"] == []


def test_samples_are_seeded_by_default(db):
    reset_demo.main(["--yes"])

    assert db.tables["incidents"]


def test_zones_come_back_after_a_wipe(db):
    reset_demo.main(["--yes", "--no-samples"])

    assert len(db.tables["zones"]) == len(areas.AREAS)
