"""Supabase PostgreSQL persistence repository for the Lead Intelligence Database."""

import json
from typing import Any

import structlog

from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.db.repository import LeadRepositoryBase, SqliteLeadRepository
from linkedin_intelligence.models.lead import (
    Lead,
    LeadOutcomeRecord,
    SearchRunRecord,
)

logger = structlog.get_logger(__name__)


class SupabaseLeadRepository(LeadRepositoryBase):
    """Production Supabase PostgreSQL repository with automatic SQLite fallback."""

    def __init__(self, url: str | None = None, key: str | None = None):
        settings = get_settings()
        self.url = url or settings.supabase_url or ""
        key_val = (
            key
            or (settings.supabase_service_role_key.get_secret_value() if settings.supabase_service_role_key else None)
            or (settings.supabase_anon_key.get_secret_value() if settings.supabase_anon_key else None)
            or ""
        )
        self.key = key_val
        self.fallback_repo = SqliteLeadRepository()
        self.is_connected = False
        self._client: Any = None

        if self.url and self.key:
            try:
                from supabase import create_client
                self._client = create_client(self.url, self.key)
                # Verify table exists
                self._client.table("leads").select("id").limit(1).execute()
                self.is_connected = True
                logger.info("supabase_connected_successfully", url=self.url)
            except Exception as err:
                logger.warning(
                    "supabase_table_not_ready_falling_back_to_sqlite",
                    error=str(err),
                    hint="Run supabase/lead_intelligence_schema.sql in your Supabase SQL Editor to activate.",
                )
                self.is_connected = False

    def upsert_lead(self, lead: Lead) -> Lead:
        # Always write to local SQLite as reliable cache
        self.fallback_repo.upsert_lead(lead)

        if not self.is_connected or not self._client:
            return lead

        has_email = bool(lead.primary_email or any(c.type == "business_email" for c in lead.contacts))
        has_phone = bool(lead.primary_phone or any(c.type == "phone" for c in lead.contacts))

        payload = {
            "id": lead.id,
            "score": float(lead.score),
            "temperature": lead.temperature,
            "status": lead.status,
            "company_name": lead.company.name,
            "person_name": lead.person.name,
            "industry": lead.company.industry,
            "location": lead.company.location,
            "has_email": has_email,
            "has_phone": has_phone,
            "is_decision_maker": lead.person.is_decision_maker,
            "first_seen": lead.first_seen,
            "last_seen": lead.last_seen,
            "last_enriched": lead.last_enriched,
            "in_watchlist": lead.in_watchlist,
            "data_json": json.loads(lead.model_dump_json()),
        }

        try:
            self._client.table("leads").upsert(payload).execute()
        except Exception as err:
            logger.error("supabase_upsert_failed", lead_id=lead.id, error=str(err))

        return lead

    def upsert_leads(self, leads: list[Lead]) -> list[Lead]:
        self.fallback_repo.upsert_leads(leads)
        if not self.is_connected or not self._client:
            return leads

        for lead in leads:
            self.upsert_lead(lead)
        return leads

    def get_lead(self, lead_id: str) -> Lead | None:
        if self.is_connected and self._client:
            try:
                res = self._client.table("leads").select("data_json").eq("id", lead_id).execute()
                if res.data:
                    return Lead.model_validate(res.data[0]["data_json"])
            except Exception as err:
                logger.error("supabase_get_lead_failed", lead_id=lead_id, error=str(err))

        return self.fallback_repo.get_lead(lead_id)

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
        if self.is_connected and self._client:
            try:
                q = self._client.table("leads").select("data_json")
                if temperature:
                    if isinstance(temperature, list):
                        q = q.in_("temperature", temperature)
                    else:
                        q = q.eq("temperature", temperature)

                if status:
                    if isinstance(status, list):
                        q = q.in_("status", status)
                    else:
                        q = q.eq("status", status)

                if industry and industry != "All":
                    q = q.ilike("industry", f"%{industry}%")

                if has_email is True:
                    q = q.eq("has_email", True)

                if has_phone is True:
                    q = q.eq("has_phone", True)

                if is_decision_maker is True:
                    q = q.eq("is_decision_maker", True)

                if min_score is not None:
                    q = q.gte("score", min_score)

                if max_score is not None:
                    q = q.lte("score", max_score)

                q = q.order("score", desc=True).limit(limit)
                res = q.execute()

                leads = [Lead.model_validate(r["data_json"]) for r in res.data]
                if search_term and search_term.strip():
                    term = search_term.strip().lower()
                    leads = [
                        lead for lead in leads
                        if term in lead.company.name.lower() or term in lead.person.name.lower() or term in str(lead.intent).lower()
                    ]
                return leads
            except Exception as err:
                logger.warning("supabase_list_failed_using_local_sqlite", error=str(err))

        return self.fallback_repo.list_leads(
            temperature=temperature,
            status=status,
            search_term=search_term,
            industry=industry,
            location=location,
            has_email=has_email,
            has_phone=has_phone,
            is_decision_maker=is_decision_maker,
            min_score=min_score,
            max_score=max_score,
            limit=limit,
            offset=offset,
        )

    def record_outcome(
        self, lead_id: str, action: str, label: int, features: dict | None = None, notes: str = ""
    ) -> LeadOutcomeRecord:
        rec = self.fallback_repo.record_outcome(lead_id, action, label, features, notes)

        if self.is_connected and self._client:
            try:
                self._client.table("lead_outcomes").insert({
                    "lead_id": lead_id,
                    "action": action,
                    "label": label,
                    "features_json": features or {},
                    "notes": notes,
                }).execute()
                # Update status in Supabase leads table
                self._client.table("leads").update({"status": action.lower()}).eq("id", lead_id).execute()
            except Exception as err:
                logger.error("supabase_record_outcome_failed", error=str(err))

        return rec

    def get_outcomes_dataset(self) -> list[dict[str, Any]]:
        if self.is_connected and self._client:
            try:
                res = self._client.table("lead_outcomes").select("*").order("id", desc=False).execute()
                if res.data:
                    return [
                        {
                            "lead_id": r["lead_id"],
                            "action": r["action"],
                            "label": r["label"],
                            "features": r.get("features_json") or {},
                            "created_at": r.get("created_at"),
                        }
                        for r in res.data
                    ]
            except Exception as err:
                logger.warning("supabase_get_outcomes_failed", error=str(err))

        return self.fallback_repo.get_outcomes_dataset()

    def save_search_run(self, run: SearchRunRecord) -> None:
        self.fallback_repo.save_search_run(run)
        if self.is_connected and self._client:
            try:
                self._client.table("search_runs").upsert({
                    "run_id": run.run_id,
                    "user_query": run.user_query,
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "result_count": run.result_count,
                    "qualified_count": run.qualified_count,
                    "data_json": json.loads(run.model_dump_json()),
                }).execute()
            except Exception as err:
                logger.error("supabase_save_run_failed", error=str(err))

    def get_search_runs(self, limit: int = 20) -> list[SearchRunRecord]:
        if self.is_connected and self._client:
            try:
                res = self._client.table("search_runs").select("data_json").order("start_time", desc=True).limit(limit).execute()
                if res.data:
                    return [SearchRunRecord.model_validate(r["data_json"]) for r in res.data]
            except Exception as err:
                logger.warning("supabase_get_runs_failed", error=str(err))

        return self.fallback_repo.get_search_runs(limit=limit)

    def get_stats(self) -> dict[str, Any]:
        return self.fallback_repo.get_stats()
