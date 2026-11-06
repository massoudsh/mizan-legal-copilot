import sqlite3

import pytest

from app import storage


def test_existing_regulations_gain_trust_score_without_data_loss(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE regulations (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
            source_url TEXT, source_name TEXT NOT NULL, source_version TEXT NOT NULL,
            published_on TEXT, effective_from TEXT, effective_to TEXT, created_at TEXT NOT NULL
        )""")
        db.execute("""INSERT INTO regulations
            (id,title,body,source_name,source_version,created_at)
            VALUES (1,'Existing regulation','Original text','Official source','1','2026-01-01')""")
    monkeypatch.setattr(storage, "DATABASE_PATH", path)
    storage.initialize_database()
    storage._initialized.discard(path)
    storage.initialize_database()
    with storage.connection() as db:
        rows = db.execute("SELECT * FROM regulations").fetchall()
    assert len(rows) == 1
    assert rows[0]["body"] == "Original text"
    assert rows[0]["trust_score"] == 50


def test_foreign_keys_are_enforced_on_every_connection(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_PATH", tmp_path / "foreign-keys.db")
    storage.initialize_database()
    for _ in range(2):
        with storage.connection() as db:
            assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            with pytest.raises(sqlite3.IntegrityError):
                db.execute("""INSERT INTO users
                    (organization_id,email,role,token_hash,created_at)
                    VALUES ('nonexistent','user@example.com','viewer','digest','2026-01-01')""")
