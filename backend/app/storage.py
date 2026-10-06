"""SQLite persistence for organization context, decisions, and regulatory knowledge."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import (
    DashboardSummary,
    Decision,
    DecisionInput,
    OrganizationProfile,
    OrganizationProfileInput,
    Regulation,
    RegulationInput,
    RiskLevel,
)

DATABASE_PATH = Path(os.getenv("MIZAN_DATABASE_PATH", "mizan.db"))


_initialized_paths: set[Path] = set()


@contextmanager
def _connection(*, create_schema: bool = True):
    if create_schema and DATABASE_PATH not in _initialized_paths:
        initialize_database()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database() -> None:
    with _connection(create_schema=False) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS organization_profiles (
                organization_id TEXT PRIMARY KEY,
                industry TEXT,
                employee_count INTEGER,
                contractor_ratio_pct REAL,
                monthly_revenue_toman REAL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id TEXT NOT NULL,
                title TEXT NOT NULL,
                rationale TEXT NOT NULL,
                supporting_document TEXT,
                risk_level TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS decisions_organization_created
            ON decisions(organization_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS regulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                source_url TEXT,
                published_on TEXT,
                effective_from TEXT,
                effective_to TEXT,
                created_at TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS regulations_fts
            USING fts5(title, body, content='regulations', content_rowid='id');
            CREATE TRIGGER IF NOT EXISTS regulations_after_insert AFTER INSERT ON regulations BEGIN
                INSERT INTO regulations_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
            END;
            CREATE TRIGGER IF NOT EXISTS regulations_after_delete AFTER DELETE ON regulations BEGIN
                INSERT INTO regulations_fts(regulations_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
            END;
            CREATE TRIGGER IF NOT EXISTS regulations_after_update AFTER UPDATE ON regulations BEGIN
                INSERT INTO regulations_fts(regulations_fts, rowid, title, body) VALUES ('delete', old.id, old.title, old.body);
                INSERT INTO regulations_fts(rowid, title, body) VALUES (new.id, new.title, new.body);
            END;
            """
        )
    _initialized_paths.add(DATABASE_PATH)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def save_profile(value: OrganizationProfileInput) -> OrganizationProfile:
    now = _now()
    with _connection() as connection:
        connection.execute(
            """INSERT INTO organization_profiles VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(organization_id) DO UPDATE SET industry=excluded.industry,
            employee_count=excluded.employee_count, contractor_ratio_pct=excluded.contractor_ratio_pct,
            monthly_revenue_toman=excluded.monthly_revenue_toman, updated_at=excluded.updated_at""",
            (value.organization_id, value.industry, value.employee_count, value.contractor_ratio_pct, value.monthly_revenue_toman, now.isoformat()),
        )
    return OrganizationProfile(**value.model_dump(), updated_at=now)


def get_profile(organization_id: str) -> OrganizationProfile | None:
    with _connection() as connection:
        row = connection.execute("SELECT * FROM organization_profiles WHERE organization_id = ?", (organization_id,)).fetchone()
    return OrganizationProfile(**dict(row)) if row else None


def create_decision(value: DecisionInput) -> Decision:
    now = _now()
    with _connection() as connection:
        cursor = connection.execute(
            "INSERT INTO decisions (organization_id, title, rationale, supporting_document, risk_level, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (value.organization_id, value.title, value.rationale, value.supporting_document, value.risk_level.value, now.isoformat()),
        )
    return Decision(**value.model_dump(), id=cursor.lastrowid, created_at=now)


def list_decisions(organization_id: str, limit: int = 50) -> list[Decision]:
    with _connection() as connection:
        rows = connection.execute("SELECT * FROM decisions WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?", (organization_id, limit)).fetchall()
    return [Decision(**dict(row)) for row in rows]


def create_regulation(value: RegulationInput) -> Regulation:
    now = _now()
    values = value.model_dump()
    with _connection() as connection:
        cursor = connection.execute(
            """INSERT INTO regulations (title, body, source_url, published_on, effective_from, effective_to, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                values["title"],
                values["body"],
                values["source_url"],
                values["published_on"].isoformat() if values["published_on"] else None,
                values["effective_from"].isoformat() if values["effective_from"] else None,
                values["effective_to"].isoformat() if values["effective_to"] else None,
                now.isoformat(),
            ),
        )
    return Regulation(**values, id=cursor.lastrowid, created_at=now)


def search_regulations(query: str, on_date: str | None = None, limit: int = 5) -> list[Regulation]:
    tokens = dict.fromkeys(token for token in query.split() if len(token) >= 3)
    terms = " OR ".join('"' + token.replace('"', '""') + '"' for token in list(tokens)[:30])
    if not terms:
        return []
    with _connection() as connection:
        rows = connection.execute(
            """SELECT regulations.* FROM regulations_fts JOIN regulations ON regulations.id = regulations_fts.rowid
            WHERE regulations_fts MATCH ? AND (? IS NULL OR (effective_from IS NULL OR effective_from <= ?) AND (effective_to IS NULL OR effective_to >= ?))
            ORDER BY rank LIMIT ?""",
            (terms, on_date, on_date, on_date, limit),
        ).fetchall()
    return [Regulation(**dict(row)) for row in rows]


def dashboard(organization_id: str) -> DashboardSummary:
    decisions = list_decisions(organization_id)
    distribution = {level: 0 for level in RiskLevel}
    for decision in decisions:
        distribution[decision.risk_level] += 1
    return DashboardSummary(
        organization_id=organization_id,
        decision_count=len(decisions),
        critical_decision_count=distribution[RiskLevel.CRITICAL],
        risk_distribution=distribution,
        recent_decisions=decisions[:10],
    )
