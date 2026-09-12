"""Persistence repository layer for Lead Intelligence Database with SQLite support."""

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from linkedin_intelligence.models.lead import (
    CompanySignalProfile,
    Lead,
    LeadOutcomeRecord,
    SearchRunRecord,
)

logger = structlog.get_logger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "lead_intelligence.db"


class LeadRepositoryBase(ABC):
    """Abstract interface for lead persistence."""

    @abstractmethod
    def upsert_lead(self, lead: Lead) -> Lead: ...

    @abstractmethod
    def upsert_leads(self, leads: list[Lead]) -> list[Lead]: ...

    @abstractmethod
    def get_lead(self, lead_id: str) -> Lead | None: ...

    @abstractmethod
    def list_leads(
        self,
        temperature: str | list[str] | None = None,
        status: str | list[str] | None = None,
        search_term: str | None = None,
        industry: str | None = None,
        location: str | None = None,
        has_email: bool | None = None,
        has_phone: bool | None = None,
        is_decision_maker: bool | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Lead]: ...

    @abstractmethod
    def record_outcome(
        self, lead_id: str, action: str, label: int, features: dict | None = None, notes: str = ""
    ) -> LeadOutcomeRecord: ...

    @abstractmethod
    def get_outcomes_dataset(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def save_search_run(self, run: SearchRunRecord) -> None: ...

    @abstractmethod
    def get_search_runs(self, limit: int = 20) -> list[SearchRunRecord]: ...

    @abstractmethod
    def get_stats(self) -> dict[str, Any]: ...


class SqliteLeadRepository(LeadRepositoryBase):
    """Production-grade SQLite repository with schema migrations and indexes."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    score REAL NOT NULL,
                    temperature TEXT NOT NULL,
                    status TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    person_name TEXT NOT NULL,
                    industry TEXT,
                    location TEXT,
                    has_email INTEGER DEFAULT 0,
                    has_phone INTEGER DEFAULT 0,
                    is_decision_maker INTEGER DEFAULT 0,
                    first_seen TEXT,
                    last_seen TEXT,
                    last_enriched TEXT,
                    in_watchlist INTEGER DEFAULT 0,
                    data_json TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_temp ON leads(temperature)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_company ON leads(company_name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_leads_last_seen ON leads(last_seen)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS search_runs (
                    run_id TEXT PRIMARY KEY,
                    user_query TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    result_count INTEGER DEFAULT 0,
                    qualified_count INTEGER DEFAULT 0,
                    data_json TEXT NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS lead_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    label INTEGER NOT NULL,
                    features_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads(id)
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_lead ON lead_outcomes(lead_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_label ON lead_outcomes(label)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS company_profiles (
                    company_name TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS model_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    feature_names_json TEXT NOT NULL,
                    trained_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
                """
            )
            conn.commit()

    def upsert_lead(self, lead: Lead) -> Lead:
        has_email = 1 if (lead.primary_email or any(c.type == "business_email" for c in lead.contacts)) else 0
        has_phone = 1 if (lead.primary_phone or any(c.type == "phone" for c in lead.contacts)) else 0
        is_dm = 1 if lead.person.is_decision_maker else 0

        data_json = lead.model_dump_json()

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO leads (
                    id, score, temperature, status, company_name, person_name,
                    industry, location, has_email, has_phone, is_decision_maker,
                    first_seen, last_seen, last_enriched, in_watchlist, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    score=excluded.score,
                    temperature=excluded.temperature,
                    status=excluded.status,
                    company_name=excluded.company_name,
                    person_name=excluded.person_name,
                    industry=excluded.industry,
                    location=excluded.location,
                    has_email=excluded.has_email,
                    has_phone=excluded.has_phone,
                    is_decision_maker=excluded.is_decision_maker,
                    last_seen=excluded.last_seen,
                    last_enriched=excluded.last_enriched,
                    in_watchlist=excluded.in_watchlist,
                    data_json=excluded.data_json
                """,
                (
                    lead.id,
                    lead.score,
                    lead.temperature,
                    lead.status,
                    lead.company.name,
                    lead.person.name,
                    lead.company.industry,
                    lead.company.location,
                    has_email,
                    has_phone,
                    is_dm,
                    lead.first_seen,
                    lead.last_seen,
                    lead.last_enriched,
                    1 if lead.in_watchlist else 0,
                    data_json,
                ),
            )
            conn.commit()
        return lead

    def upsert_leads(self, leads: list[Lead]) -> list[Lead]:
        for lead in leads:
            self.upsert_lead(lead)
        return leads

    def get_lead(self, lead_id: str) -> Lead | None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT data_json FROM leads WHERE id = ?", (lead_id,))
            row = cur.fetchone()
            if row:
                return Lead.model_validate_json(row["data_json"])
        return None

    def list_leads(
        self,
        temperature: str | list[str] | None = None,
        status: str | list[str] | None = None,
        search_term: str | None = None,
        industry: str | None = None,
        location: str | None = None,
        has_email: bool | None = None,
        has_phone: bool | None = None,
        is_decision_maker: bool | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[Lead]:
        query = "SELECT data_json FROM leads WHERE 1=1"
        params: list[Any] = []

        if temperature:
            if isinstance(temperature, list):
                placeholders = ",".join("?" * len(temperature))
                query += f" AND temperature IN ({placeholders})"
                params.extend(temperature)
            else:
                query += " AND temperature = ?"
                params.append(temperature)

        if status:
            if isinstance(status, list):
                placeholders = ",".join("?" * len(status))
                query += f" AND status IN ({placeholders})"
                params.extend(status)
            else:
                query += " AND status = ?"
                params.append(status)

        if industry and industry != "All":
            query += " AND industry LIKE ?"
            params.append(f"%{industry}%")

        if location and location != "All":
            query += " AND location LIKE ?"
            params.append(f"%{location}%")

        if has_email is True:
            query += " AND has_email = 1"
        elif has_email is False:
            query += " AND has_email = 0"

        if has_phone is True:
            query += " AND has_phone = 1"

        if is_decision_maker is True:
            query += " AND is_decision_maker = 1"

        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)

        if max_score is not None:
            query += " AND score <= ?"
            params.append(max_score)

        if search_term and search_term.strip():
            term = f"%{search_term.strip()}%"
            query += " AND (company_name LIKE ? OR person_name LIKE ? OR industry LIKE ? OR data_json LIKE ?)"
            params.extend([term, term, term, term])

        query += " ORDER BY score DESC, last_seen DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            return [Lead.model_validate_json(r["data_json"]) for r in rows]

    def record_outcome(
        self, lead_id: str, action: str, label: int, features: dict | None = None, notes: str = ""
    ) -> LeadOutcomeRecord:
        now = datetime.now(timezone.utc).isoformat()
        feat = features or {}
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO lead_outcomes (lead_id, action, label, features_json, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (lead_id, action, label, json.dumps(feat), now, notes),
            )
            # Update lead outcome and status
            cur.execute(
                "UPDATE leads SET status = ? WHERE id = ?",
                (action.lower(), lead_id),
            )
            conn.commit()

        # Update in-memory data_json
        lead = self.get_lead(lead_id)
        if lead:
            lead.outcome = action
            lead.status = action.lower() if action.lower() in [
                "new", "reviewed", "in_progress", "contacted", "responded", "meeting", "won", "lost", "disqualified"
            ] else lead.status
            self.upsert_lead(lead)

        return LeadOutcomeRecord(
            lead_id=lead_id,
            action=action,
            label=label,
            features=feat,
            created_at=now,
            notes=notes,
        )

    def get_outcomes_dataset(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT lead_id, action, label, features_json, created_at
                FROM lead_outcomes ORDER BY id ASC
                """
            )
            rows = cur.fetchall()
            dataset = []
            for r in rows:
                features = json.loads(r["features_json"]) if r["features_json"] else {}
                dataset.append({
                    "lead_id": r["lead_id"],
                    "action": r["action"],
                    "label": r["label"],
                    "features": features,
                    "created_at": r["created_at"],
                })
            return dataset

    def save_search_run(self, run: SearchRunRecord) -> None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO search_runs (run_id, user_query, start_time, end_time, result_count, qualified_count, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    end_time=excluded.end_time,
                    result_count=excluded.result_count,
                    qualified_count=excluded.qualified_count,
                    data_json=excluded.data_json
                """,
                (
                    run.run_id,
                    run.user_query,
                    run.start_time,
                    run.end_time,
                    run.result_count,
                    run.qualified_count,
                    run.model_dump_json(),
                ),
            )
            conn.commit()

    def get_search_runs(self, limit: int = 20) -> list[SearchRunRecord]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT data_json FROM search_runs ORDER BY start_time DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            return [SearchRunRecord.model_validate_json(r["data_json"]) for r in rows]

    def save_company_profile(self, profile: CompanySignalProfile) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO company_profiles (company_name, data_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(company_name) DO UPDATE SET
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
                """,
                (profile.company_name.lower(), profile.model_dump_json(), now),
            )
            conn.commit()

    def get_company_profile(self, company_name: str) -> CompanySignalProfile | None:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT data_json FROM company_profiles WHERE company_name = ?",
                (company_name.lower(),),
            )
            row = cur.fetchone()
            if row:
                return CompanySignalProfile.model_validate_json(row["data_json"])
        return None

    def get_stats(self) -> dict[str, Any]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as total, AVG(score) as avg_score FROM leads")
            row = cur.fetchone()
            total = row["total"] or 0
            avg_score = round(row["avg_score"] or 0.0, 1)

            cur.execute("SELECT temperature, COUNT(*) as cnt FROM leads GROUP BY temperature")
            temp_counts = {r["temperature"]: r["cnt"] for r in cur.fetchall()}

            cur.execute("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status")
            status_counts = {r["status"]: r["cnt"] for r in cur.fetchall()}

            cur.execute("SELECT COUNT(*) as cnt FROM leads WHERE has_email = 1")
            has_email_cnt = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) as cnt FROM leads WHERE has_phone = 1")
            has_phone_cnt = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) as cnt FROM leads WHERE is_decision_maker = 1")
            decision_maker_cnt = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) as cnt FROM lead_outcomes")
            outcomes_count = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) as cnt FROM lead_outcomes WHERE label = 1")
            positive_outcomes = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) as cnt FROM lead_outcomes WHERE label = 0")
            negative_outcomes = cur.fetchone()["cnt"]

            return {
                "total_leads": total,
                "avg_score": avg_score,
                "hot_count": temp_counts.get("HOT", 0),
                "warm_count": temp_counts.get("WARM", 0),
                "cool_count": temp_counts.get("COOL", 0),
                "cold_count": temp_counts.get("COLD", 0),
                "unqualified_count": temp_counts.get("UNQUALIFIED", 0),
                "contactable_count": has_email_cnt + has_phone_cnt,
                "verified_emails": has_email_cnt,
                "decision_makers": decision_maker_cnt,
                "outcomes_count": outcomes_count,
                "positive_outcomes": positive_outcomes,
                "negative_outcomes": negative_outcomes,
                "status_counts": status_counts,
            }


_repo_instance: LeadRepositoryBase | None = None


def get_lead_repository() -> LeadRepositoryBase:
    """Singleton getter for the persistent lead repository (Supabase with SQLite fallback)."""
    global _repo_instance
    if _repo_instance is None:
        from linkedin_intelligence.config.settings import get_settings
        settings = get_settings()
        if settings.has_supabase:
            from linkedin_intelligence.db.supabase_repo import SupabaseLeadRepository
            _repo_instance = SupabaseLeadRepository()
        else:
            _repo_instance = SqliteLeadRepository()
    return _repo_instance

