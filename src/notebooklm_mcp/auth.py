"""Authentication helper for NotebookLM MCP.

Provides token management and validation for NotebookLM API access.
"""

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AuthTokens:
    """Authentication tokens for NotebookLM.
    
    Only cookies are required. CSRF token and session ID are optional because
    they can be auto-extracted from the NotebookLM page when needed.
    """
    cookies: dict[str, str]
    csrf_token: str = ""
    session_id: str = ""
    extracted_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "cookies": self.cookies,
            "csrf_token": self.csrf_token,
            "session_id": self.session_id,
            "extracted_at": self.extracted_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthTokens":
        return cls(
            cookies=data.get("cookies", {}),
            csrf_token=data.get("csrf_token", ""),
            session_id=data.get("session_id", ""),
            extracted_at=data.get("extracted_at", 0),
        )

    def is_expired(self, max_age_hours: float = 168) -> bool:
        """Check if cookies are older than max_age_hours (default 1 week)."""
        age_seconds = time.time() - self.extracted_at
        return age_seconds > (max_age_hours * 3600)

    @property
    def cookie_header(self) -> str:
        """Get cookies as a header string."""
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())


# Required cookies for authentication
REQUIRED_COOKIES = ["SID", "HSID", "SSID", "APISID", "SAPISID"]


def get_cache_path() -> Path:
    """Get the path to the auth cache file."""
    cache_dir = Path.home() / ".notebooklm-mcp"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / "auth.json"


def load_cached_tokens() -> AuthTokens | None:
    """Load tokens from cache if they exist."""
    cache_path = get_cache_path()
    if not cache_path.exists():
        return None

    try:
        with open(cache_path) as f:
            data = json.load(f)
        return AuthTokens.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def save_tokens_to_cache(tokens: AuthTokens, silent: bool = False) -> None:
    """Save tokens to cache."""
    cache_path = get_cache_path()
    with open(cache_path, "w") as f:
        json.dump(tokens.to_dict(), f, indent=2)
    if not silent:
        print(f"Auth tokens cached to {cache_path}")


def validate_cookies(cookies: dict[str, str]) -> bool:
    """Check if required cookies are present."""
    return all(required in cookies for required in REQUIRED_COOKIES)


def extract_csrf_from_page_source(html: str) -> str | None:
    """Extract CSRF token from page HTML."""
    patterns = [
        r'"SNlM0e":"([^"]+)"',
        r'at=([^&"]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None


def extract_session_id_from_html(html: str) -> str | None:
    """Extract session ID from page HTML."""
    patterns = [
        r'"FdrFJe":"([^"]+)"',
        r'f\.sid["\s:=]+["\']?(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return None
