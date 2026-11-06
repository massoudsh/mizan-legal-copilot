"""Tenant-scoped SQLite persistence; PostgreSQL/pgvector schema lives in database/postgres.sql."""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.auth import Principal, Role
from app.crypto import encrypt
from app.schemas import Connector, ConnectorInput, Decision, DecisionInput, DemoRequest, DemoRequestInput, OrganizationProfile, OrganizationProfileInput, Regulation, RegulationInput, RegulatorySource, RegulatorySourceInput, RiskLevel

DATABASE_PATH = Path(os.getenv("MIZAN_DATABASE_PATH", "mizan.db"))
_initialized: set[Path] = set()


def now() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def connection():
    if DATABASE_PATH not in _initialized:
        initialize_database()
    db = sqlite3.connect(DATABASE_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def initialize_database() -> None:
    if DATABASE_PATH in _initialized:
        return
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    try:
        db.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS organizations (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, organization_id TEXT NOT NULL REFERENCES organizations(id), email TEXT NOT NULL UNIQUE, role TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS organization_profiles (organization_id TEXT PRIMARY KEY REFERENCES organizations(id), industry TEXT, employee_count INTEGER, contractor_ratio_pct REAL, monthly_revenue_toman REAL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, organization_id TEXT NOT NULL REFERENCES organizations(id), title TEXT NOT NULL, rationale TEXT NOT NULL, supporting_document TEXT, risk_level TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS obligations (id INTEGER PRIMARY KEY AUTOINCREMENT, organization_id TEXT NOT NULL REFERENCES organizations(id), title TEXT NOT NULL, description TEXT NOT NULL, due_on TEXT NOT NULL, owner_email TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, organization_id TEXT NOT NULL REFERENCES organizations(id), decision_id INTEGER NOT NULL, reviewer_email TEXT NOT NULL, status TEXT NOT NULL, note TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS contract_versions (id INTEGER PRIMARY KEY AUTOINCREMENT, organization_id TEXT NOT NULL REFERENCES organizations(id), contract_key TEXT NOT NULL, version TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(organization_id, contract_key, version));
        CREATE INDEX IF NOT EXISTS decisions_org_created ON decisions(organization_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS regulations (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, body TEXT NOT NULL, source_url TEXT, source_name TEXT NOT NULL, source_version TEXT NOT NULL, trust_score INTEGER NOT NULL DEFAULT 50, published_on TEXT, effective_from TEXT, effective_to TEXT, created_at TEXT NOT NULL, UNIQUE(source_name, source_version));
        CREATE VIRTUAL TABLE IF NOT EXISTS regulations_fts USING fts5(title, body, content='regulations', content_rowid='id');
        CREATE TRIGGER IF NOT EXISTS regulations_insert AFTER INSERT ON regulations BEGIN INSERT INTO regulations_fts(rowid,title,body) VALUES(new.id,new.title,new.body); END;
        CREATE TRIGGER IF NOT EXISTS regulations_delete AFTER DELETE ON regulations BEGIN INSERT INTO regulations_fts(regulations_fts,rowid,title,body) VALUES('delete',old.id,old.title,old.body); END;
        CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, organization_id TEXT NOT NULL REFERENCES organizations(id), title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL, read_at TEXT);
        CREATE TABLE IF NOT EXISTS connectors (id INTEGER PRIMARY KEY AUTOINCREMENT, organization_id TEXT NOT NULL REFERENCES organizations(id), name TEXT NOT NULL, kind TEXT NOT NULL, base_url TEXT NOT NULL, secret_reference TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS regulatory_sources (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, feed_url TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, last_checked_at TEXT);
        CREATE TABLE IF NOT EXISTS demo_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, organization TEXT NOT NULL, work_email TEXT NOT NULL, phone TEXT, employee_count INTEGER, message TEXT, created_at TEXT NOT NULL);
        """)
        columns = {row[1] for row in db.execute("PRAGMA table_info(regulations)")}
        if "trust_score" not in columns:
            db.execute("ALTER TABLE regulations ADD COLUMN trust_score INTEGER NOT NULL DEFAULT 50")
        db.commit()
    finally:
        db.close()
    _initialized.add(DATABASE_PATH)


def create_organization(organization_id: str, name: str) -> None:
    with connection() as db:
        db.execute("INSERT INTO organizations(id,name,created_at) VALUES(?,?,?)", (organization_id, name, now().isoformat()))


def create_user(organization_id: str, email: str, role: str, token_hash: str) -> int:
    with connection() as db:
        result = db.execute("INSERT INTO users(organization_id,email,role,token_hash,created_at) VALUES(?,?,?,?,?)", (organization_id, email, role, token_hash, now().isoformat()))
    return result.lastrowid


def get_principal(token_hash: str) -> Principal | None:
    with connection() as db:
        row = db.execute("SELECT id,organization_id,role FROM users WHERE token_hash=?", (token_hash,)).fetchone()
    return Principal(row["id"], row["organization_id"], Role(row["role"])) if row else None


def get_identity(principal: Principal) -> dict:
    with connection() as db:
        row = db.execute("SELECT email,role,organization_id FROM users WHERE id=? AND organization_id=?", (principal.user_id, principal.organization_id)).fetchone()
    return dict(row)


def save_profile(principal: Principal, value: OrganizationProfileInput) -> OrganizationProfile:
    timestamp = now()
    with connection() as db:
        db.execute("""INSERT INTO organization_profiles VALUES(?,?,?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET industry=excluded.industry,employee_count=excluded.employee_count,contractor_ratio_pct=excluded.contractor_ratio_pct,monthly_revenue_toman=excluded.monthly_revenue_toman,updated_at=excluded.updated_at""", (principal.organization_id, value.industry, value.employee_count, value.contractor_ratio_pct, value.monthly_revenue_toman, timestamp.isoformat()))
    return OrganizationProfile(organization_id=principal.organization_id, **value.model_dump(), updated_at=timestamp)


def get_profile(principal: Principal) -> OrganizationProfile | None:
    with connection() as db:
        row = db.execute("SELECT * FROM organization_profiles WHERE organization_id=?", (principal.organization_id,)).fetchone()
    return OrganizationProfile(**dict(row)) if row else None


def create_decision(principal: Principal, value: DecisionInput) -> Decision:
    timestamp = now()
    with connection() as db:
        result = db.execute("INSERT INTO decisions(organization_id,title,rationale,supporting_document,risk_level,created_at) VALUES(?,?,?,?,?,?)", (principal.organization_id, value.title, value.rationale, value.supporting_document, value.risk_level.value, timestamp.isoformat()))
    return Decision(**value.model_dump(), id=result.lastrowid, created_at=timestamp)


def list_decisions(principal: Principal, limit: int | None = 50) -> list[Decision]:
    with connection() as db:
        query = "SELECT * FROM decisions WHERE organization_id=? ORDER BY created_at DESC, id DESC"
        params = [principal.organization_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = db.execute(query, params).fetchall()
    return [Decision(**dict(row)) for row in rows]


def create_regulation(value: RegulationInput) -> tuple[Regulation, bool]:
    timestamp, values = now(), value.model_dump()
    with connection() as db:
        old = db.execute("SELECT source_version FROM regulations WHERE source_name=? ORDER BY id DESC LIMIT 1", (value.source_name,)).fetchone()
        result = db.execute("INSERT INTO regulations(title,body,source_url,source_name,source_version,trust_score,published_on,effective_from,effective_to,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (value.title, value.body, str(value.source_url) if value.source_url else None, value.source_name, value.source_version, value.trust_score, str(value.published_on) if value.published_on else None, str(value.effective_from) if value.effective_from else None, str(value.effective_to) if value.effective_to else None, timestamp.isoformat()))
    return Regulation(**values, id=result.lastrowid, created_at=timestamp), bool(old)


def search_regulations(query: str, on_date: str | None, limit: int = 5) -> list[Regulation]:
    terms = " OR ".join('"' + t.replace('"', '""') + '"' for t in dict.fromkeys(query.split()) if len(t) >= 3)
    if not terms:
        return []
    with connection() as db:
        rows = db.execute("""SELECT r.* FROM regulations_fts JOIN regulations r ON r.id=regulations_fts.rowid WHERE regulations_fts MATCH ? AND (? IS NULL OR (r.effective_from IS NULL OR r.effective_from<=?) AND (r.effective_to IS NULL OR r.effective_to>=?)) ORDER BY bm25(regulations_fts) LIMIT ?""", (terms, on_date, on_date, on_date, limit)).fetchall()
    return [Regulation(**dict(row)) for row in rows]



def create_regulatory_source(value: RegulatorySourceInput) -> RegulatorySource:
    with connection() as db:
        result = db.execute("INSERT INTO regulatory_sources(name,feed_url) VALUES(?,?)", (value.name, str(value.feed_url)))
    return RegulatorySource(id=result.lastrowid, **value.model_dump(), enabled=True)


def list_regulatory_sources() -> list[RegulatorySource]:
    with connection() as db:
        rows = db.execute("SELECT * FROM regulatory_sources WHERE enabled=1").fetchall()
    return [RegulatorySource(**dict(row)) for row in rows]


def mark_source_checked(source_id: int) -> None:
    with connection() as db:
        db.execute("UPDATE regulatory_sources SET last_checked_at=? WHERE id=?", (now().isoformat(), source_id))

def create_alert_for_all(title: str, body: str) -> None:
    with connection() as db:
        for row in db.execute("SELECT id FROM organizations").fetchall():
            db.execute("INSERT INTO alerts(organization_id,title,body,created_at) VALUES(?,?,?,?)", (row["id"], title, body, now().isoformat()))


def create_obligation(principal: Principal, value) -> object:
    timestamp = now()
    with connection() as db:
        result = db.execute("INSERT INTO obligations(organization_id,title,description,due_on,owner_email,status,created_at) VALUES(?,?,?,?,?,?,?)", (principal.organization_id, value.title, value.description, str(value.due_on), str(value.owner_email) if value.owner_email else None, value.status, timestamp.isoformat()))
    from app.schemas import Obligation
    return Obligation(**value.model_dump(), id=result.lastrowid, created_at=timestamp)


def list_obligations(principal: Principal, status: str | None = None) -> list:
    with connection() as db:
        query = "SELECT * FROM obligations WHERE organization_id=?"
        params = [principal.organization_id]
        if status:
            query += " AND status=?"
            params.append(status)
        rows = db.execute(query + " ORDER BY due_on", params).fetchall()
    from app.schemas import Obligation
    return [Obligation(**dict(row)) for row in rows]


def create_review(principal: Principal, value) -> object:
    timestamp = now()
    with connection() as db:
        decision = db.execute("SELECT id FROM decisions WHERE organization_id=? AND id=?", (principal.organization_id, value.decision_id)).fetchone()
        if decision is None:
            raise LookupError("تصمیم یافت نشد.")
        reviewer = db.execute("SELECT role FROM users WHERE organization_id=? AND email=? COLLATE NOCASE", (principal.organization_id, str(value.reviewer_email))).fetchone()
        if reviewer is None:
            raise LookupError("بررسی‌کنندهٔ عضو سازمان یافت نشد.")
        if reviewer["role"] == "viewer":
            raise PermissionError("بررسی‌کننده باید مجوز ثبت نتیجه داشته باشد.")
        result = db.execute("INSERT INTO reviews(organization_id,decision_id,reviewer_email,status,note,created_at) VALUES(?,?,?,?,?,?)", (principal.organization_id, value.decision_id, str(value.reviewer_email), value.status, value.note, timestamp.isoformat()))
    from app.schemas import Review
    return Review(**value.model_dump(), id=result.lastrowid, created_at=timestamp)


def resolve_review(principal: Principal, review_id: int, value):
    from app.schemas import Review
    with connection() as db:
        row = db.execute("SELECT * FROM reviews WHERE organization_id=? AND id=?", (principal.organization_id, review_id)).fetchone()
        if row is None:
            raise LookupError("بررسی یافت نشد.")
        user = db.execute("SELECT email FROM users WHERE organization_id=? AND id=?", (principal.organization_id, principal.user_id)).fetchone()
        if user is None or user["email"].casefold() != row["reviewer_email"].casefold():
            raise PermissionError("فقط بررسی‌کنندهٔ تعیین‌شده می‌تواند نتیجه را ثبت کند.")
        if row["status"] != "pending":
            raise ValueError("بررسی قبلاً نهایی شده است.")
        result = db.execute("UPDATE reviews SET status=?,note=? WHERE organization_id=? AND id=? AND status='pending'", (value.status, value.note, principal.organization_id, review_id))
        if result.rowcount != 1:
            raise ValueError("بررسی قبلاً نهایی شده است.")
    return Review(**{**dict(row), "status": value.status, "note": value.note})


def update_obligation_status(principal: Principal, obligation_id: int, status: str):
    from app.schemas import Obligation
    with connection() as db:
        row = db.execute("SELECT * FROM obligations WHERE organization_id=? AND id=?", (principal.organization_id, obligation_id)).fetchone()
        if row is None:
            raise LookupError("تعهد یافت نشد.")
        db.execute("UPDATE obligations SET status=? WHERE organization_id=? AND id=?", (status, principal.organization_id, obligation_id))
    return Obligation(**{**dict(row), "status": status})


def list_reviews(principal: Principal, decision_id: int | None = None) -> list:
    with connection() as db:
        query = "SELECT * FROM reviews WHERE organization_id=?"
        params = [principal.organization_id]
        if decision_id is not None:
            query += " AND decision_id=?"
            params.append(decision_id)
        rows = db.execute(query + " ORDER BY created_at DESC", params).fetchall()
    from app.schemas import Review
    return [Review(**dict(row)) for row in rows]


def save_contract_version(principal: Principal, value) -> None:
    with connection() as db:
        db.execute("INSERT INTO contract_versions(organization_id,contract_key,version,body,created_at) VALUES(?,?,?,?,?)", (principal.organization_id, value.contract_key, value.version, value.body, now().isoformat()))


def diff_contract_versions(principal: Principal, contract_key: str, from_version: str, to_version: str):
    import difflib
    with connection() as db:
        rows = db.execute("SELECT version,body FROM contract_versions WHERE organization_id=? AND contract_key=? AND version IN (?,?)", (principal.organization_id, contract_key, from_version, to_version)).fetchall()
    bodies = {row["version"]: row["body"].splitlines() for row in rows}
    if set(bodies) != {from_version, to_version}:
        raise ValueError("نسخهٔ قرارداد یافت نشد.")
    diff = list(difflib.ndiff(bodies[from_version], bodies[to_version]))
    from app.schemas import ContractDiff
    return ContractDiff(contract_key=contract_key, from_version=from_version, to_version=to_version, added=[x[2:] for x in diff if x.startswith("+ ")], removed=[x[2:] for x in diff if x.startswith("- ")])


def audit_export(principal: Principal):
    from app.schemas import AuditExport
    return AuditExport(organization_id=principal.organization_id, generated_at=now(), decisions=list_decisions(principal, limit=None), reviews=list_reviews(principal), obligations=list_obligations(principal))


def create_connector(principal: Principal, value: ConnectorInput) -> Connector:
    timestamp = now()
    with connection() as db:
        result = db.execute("INSERT INTO connectors(organization_id,name,kind,base_url,secret_reference,created_at) VALUES(?,?,?,?,?,?)", (principal.organization_id, value.name, value.kind, str(value.base_url), value.secret_reference, timestamp.isoformat()))
    return Connector(**value.model_dump(), id=result.lastrowid, enabled=True, created_at=timestamp)


def list_connectors(principal: Principal) -> list[Connector]:
    with connection() as db:
        rows = db.execute("SELECT * FROM connectors WHERE organization_id=?", (principal.organization_id,)).fetchall()
    return [Connector(**dict(row)) for row in rows]


def create_demo_request(value: DemoRequestInput) -> DemoRequest:
    timestamp = now()
    with connection() as db:
        result = db.execute("INSERT INTO demo_requests(name,organization,work_email,phone,employee_count,message,created_at) VALUES(?,?,?,?,?,?,?)", (value.name, value.organization, encrypt(str(value.work_email)), encrypt(value.phone), value.employee_count, encrypt(value.message), timestamp.isoformat()))
    return DemoRequest(id=result.lastrowid, created_at=timestamp)


def dashboard(principal: Principal):
    decisions = list_decisions(principal, limit=None)
    distribution = {level: 0 for level in RiskLevel}
    for decision in decisions:
        distribution[decision.risk_level] += 1
    with connection() as db:
        unread = db.execute("SELECT count(*) FROM alerts WHERE organization_id=? AND read_at IS NULL", (principal.organization_id,)).fetchone()[0]
    return decisions, distribution, unread
