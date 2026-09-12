"""Database and persistence package."""

from linkedin_intelligence.db.repository import (
    DEFAULT_DB_PATH,
    LeadRepositoryBase,
    SqliteLeadRepository,
    get_lead_repository,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "LeadRepositoryBase",
    "SqliteLeadRepository",
    "get_lead_repository",
]
