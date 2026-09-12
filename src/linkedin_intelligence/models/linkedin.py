"""LinkedIn post domain entity and normalized representations."""

from typing import Any

from pydantic import BaseModel, Field


class LinkedInPost(BaseModel):
    """Normalized LinkedIn post data representation."""

    id: str = Field(description="Unique deterministic ID of the post")
    url: str | None = Field(default=None, description="Canonical URL to the LinkedIn post")
    content: str = Field(default="", description="Post text body")
    author_name: str | None = Field(default=None, description="Author full name")
    author_profile_url: str | None = Field(default=None, description="Author public profile URL")
    author_headline: str | None = Field(default=None, description="Author headline / title")
    company_name: str | None = Field(default=None, description="Detected employer or subject company")
    company_identifier: str | None = Field(default=None, description="Company handle or public identifier")
    published_at: str | None = Field(default=None, description="ISO timestamp or relative date string")
    source: str = Field(default="linkedin", description="Source provider identifier")
    matched_queries: list[str] = Field(default_factory=list, description="Queries that matched this post")
    raw_data: dict[str, Any] = Field(default_factory=dict, description="Raw provider payload for debugging")

    @property
    def post_url(self) -> str | None:
        """Alias for url for consistent naming across lead sources."""
        return self.url

    @property
    def clean_text(self) -> str:
        """Sanitized and stripped content text."""
        return " ".join((self.content or "").split())

    @property
    def content_preview(self) -> str:
        """First 180 chars of post text."""
        txt = self.clean_text
        return txt[:180] + ("..." if len(txt) > 180 else "")
