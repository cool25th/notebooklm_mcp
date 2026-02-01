"""NotebookLM API Client.

This module provides the HTTP client for communicating with NotebookLM's internal API.
It handles authentication, session management, and API calls.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Configuration paths
CONFIG_DIR = Path.home() / ".notebooklm-mcp"
AUTH_FILE = CONFIG_DIR / "auth.json"
COOKIES_FILE = CONFIG_DIR / "cookies.json"


class NotebookLMClient:
    """Client for NotebookLM's internal API."""
    
    BASE_URL = "https://notebooklm.google.com"
    API_BASE = "https://notebooklm.google.com/_/NotebookLmUi/data"
    
    def __init__(self):
        """Initialize the NotebookLM client."""
        self._http: httpx.AsyncClient | None = None
        self._csrf_token: str | None = None
        self._session_id: str | None = None
        self._cookies: dict[str, str] = {}
        self._load_auth()
    
    def _load_auth(self) -> None:
        """Load authentication data from disk."""
        if AUTH_FILE.exists():
            try:
                with open(AUTH_FILE) as f:
                    auth_data = json.load(f)
                self._csrf_token = auth_data.get("csrf_token")
                self._session_id = auth_data.get("session_id")
                self._cookies = auth_data.get("cookies", {})
                logger.info("Loaded authentication from %s", AUTH_FILE)
            except Exception as e:
                logger.warning("Failed to load auth file: %s", e)
    
    def _save_auth(self) -> None:
        """Save authentication data to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        auth_data = {
            "csrf_token": self._csrf_token,
            "session_id": self._session_id,
            "cookies": self._cookies,
        }
        with open(AUTH_FILE, "w") as f:
            json.dump(auth_data, f, indent=2)
        logger.info("Saved authentication to %s", AUTH_FILE)
    
    @property
    def http(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating if necessary."""
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=30.0,
                cookies=self._cookies,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Origin": self.BASE_URL,
                    "Referer": f"{self.BASE_URL}/",
                },
            )
        return self._http
    
    async def _make_request(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        method: str = "POST",
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        if not self._csrf_token:
            return {"error": "Not authenticated. Run notebooklm-mcp-auth first."}
        
        headers = {
            "X-Goog-AuthToken": self._csrf_token,
        }
        
        try:
            if method == "POST":
                response = await self.http.post(
                    endpoint,
                    json=data,
                    headers=headers,
                )
            else:
                response = await self.http.get(
                    endpoint,
                    headers=headers,
                )
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                return {
                    "error": "Authentication expired. Run notebooklm-mcp-auth to refresh.",
                    "status_code": e.response.status_code,
                }
            return {"error": str(e), "status_code": e.response.status_code}
        except Exception as e:
            return {"error": str(e)}
    
    # =========================================================================
    # Notebook Operations
    # =========================================================================
    
    async def list_notebooks(self) -> dict[str, Any]:
        """List all notebooks."""
        # NotebookLM uses a batch RPC endpoint. This is a simplified version.
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "list_notebooks"},
        )
    
    async def create_notebook(self, name: str, description: str = "") -> dict[str, Any]:
        """Create a new notebook."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "create_notebook", "name": name, "description": description},
        )
    
    async def get_notebook(self, notebook_id: str) -> dict[str, Any]:
        """Get notebook details."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "get_notebook", "notebook_id": notebook_id},
        )
    
    async def describe_notebook(self, notebook_id: str) -> dict[str, Any]:
        """Get AI summary of notebook."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "describe_notebook", "notebook_id": notebook_id},
        )
    
    async def rename_notebook(self, notebook_id: str, new_name: str) -> dict[str, Any]:
        """Rename a notebook."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "rename_notebook", "notebook_id": notebook_id, "name": new_name},
        )
    
    async def delete_notebook(self, notebook_id: str) -> dict[str, Any]:
        """Delete a notebook."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "delete_notebook", "notebook_id": notebook_id},
        )
    
    # =========================================================================
    # Source Operations
    # =========================================================================
    
    async def add_source(
        self,
        notebook_id: str,
        source_type: str,
        url: str = "",
        text: str = "",
        title: str = "",
        file_path: str = "",
        wait: bool = True,
        wait_timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Add a source to a notebook."""
        data = {
            "action": "add_source",
            "notebook_id": notebook_id,
            "source_type": source_type,
            "url": url,
            "text": text,
            "title": title,
            "file_path": file_path,
        }
        
        result = await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data=data,
        )
        
        if wait and "source_id" in result:
            # Poll for processing completion
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < wait_timeout:
                status = await self.list_sources(notebook_id)
                if "error" not in status:
                    for source in status.get("sources", []):
                        if source.get("id") == result["source_id"]:
                            if source.get("status") == "ready":
                                result["status"] = "ready"
                                return result
                await asyncio.sleep(2)
            result["status"] = "timeout"
        
        return result
    
    async def list_sources(self, notebook_id: str) -> dict[str, Any]:
        """List sources in a notebook."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "list_sources", "notebook_id": notebook_id},
        )
    
    async def delete_source(self, notebook_id: str, source_id: str) -> dict[str, Any]:
        """Delete a source."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "delete_source", "notebook_id": notebook_id, "source_id": source_id},
        )
    
    async def describe_source(self, notebook_id: str, source_id: str) -> dict[str, Any]:
        """Get AI summary of a source."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "describe_source", "notebook_id": notebook_id, "source_id": source_id},
        )
    
    async def get_source_content(self, notebook_id: str, source_id: str) -> dict[str, Any]:
        """Get raw content of a source."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "get_source_content", "notebook_id": notebook_id, "source_id": source_id},
        )
    
    # =========================================================================
    # Query Operations
    # =========================================================================
    
    async def query_notebook(self, notebook_id: str, query: str) -> dict[str, Any]:
        """Query the notebook AI."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "query", "notebook_id": notebook_id, "query": query},
        )
    
    async def configure_chat(
        self,
        notebook_id: str,
        goal: str = "",
        response_length: str = "medium",
    ) -> dict[str, Any]:
        """Configure chat settings."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={
                "action": "configure_chat",
                "notebook_id": notebook_id,
                "goal": goal,
                "response_length": response_length,
            },
        )
    
    # =========================================================================
    # Studio Operations
    # =========================================================================
    
    async def create_studio_content(
        self,
        notebook_id: str,
        artifact_type: str,
        format: str = "",
        difficulty: str = "medium",
    ) -> dict[str, Any]:
        """Create studio content."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={
                "action": "create_studio",
                "notebook_id": notebook_id,
                "artifact_type": artifact_type,
                "format": format,
                "difficulty": difficulty,
            },
        )
    
    async def get_studio_status(self, notebook_id: str, artifact_id: str) -> dict[str, Any]:
        """Get studio content generation status."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "studio_status", "notebook_id": notebook_id, "artifact_id": artifact_id},
        )
    
    async def download_artifact(
        self,
        notebook_id: str,
        artifact_id: str,
        artifact_type: str,
        output_path: str = "",
    ) -> dict[str, Any]:
        """Download an artifact."""
        # Get download URL first
        status = await self.get_studio_status(notebook_id, artifact_id)
        if "download_url" not in status:
            return {"error": "Artifact not ready or download URL not available"}
        
        # Download the file
        try:
            response = await self.http.get(status["download_url"])
            response.raise_for_status()
            
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return {"status": "downloaded", "path": output_path}
            else:
                return {"status": "ready", "content_length": len(response.content)}
        except Exception as e:
            return {"error": str(e)}
    
    # =========================================================================
    # Research Operations
    # =========================================================================
    
    async def start_research(
        self,
        notebook_id: str,
        query: str,
        search_type: str = "web",
    ) -> dict[str, Any]:
        """Start web or Drive research."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={
                "action": "start_research",
                "notebook_id": notebook_id,
                "query": query,
                "search_type": search_type,
            },
        )
    
    async def get_research_status(self, notebook_id: str, research_id: str) -> dict[str, Any]:
        """Get research status."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "research_status", "notebook_id": notebook_id, "research_id": research_id},
        )
    
    async def import_research_sources(
        self,
        notebook_id: str,
        research_id: str,
        source_indices: list[int] | None = None,
    ) -> dict[str, Any]:
        """Import sources from research."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={
                "action": "import_research",
                "notebook_id": notebook_id,
                "research_id": research_id,
                "source_indices": source_indices or [],
            },
        )
    
    # =========================================================================
    # Sharing Operations
    # =========================================================================
    
    async def get_share_status(self, notebook_id: str) -> dict[str, Any]:
        """Get sharing settings."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "share_status", "notebook_id": notebook_id},
        )
    
    async def set_public_sharing(self, notebook_id: str, enabled: bool) -> dict[str, Any]:
        """Enable/disable public sharing."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={"action": "set_public", "notebook_id": notebook_id, "enabled": enabled},
        )
    
    async def invite_collaborator(
        self,
        notebook_id: str,
        email: str,
        role: str = "viewer",
    ) -> dict[str, Any]:
        """Invite a collaborator."""
        return await self._make_request(
            "/_/NotebookLmUi/data/batchexecute",
            data={
                "action": "invite",
                "notebook_id": notebook_id,
                "email": email,
                "role": role,
            },
        )
    
    # =========================================================================
    # Auth Operations
    # =========================================================================
    
    async def refresh_auth(self) -> dict[str, Any]:
        """Reload auth tokens from disk."""
        self._load_auth()
        if self._csrf_token:
            return {
                "status": "refreshed",
                "has_csrf_token": True,
                "has_session_id": bool(self._session_id),
            }
        return {"status": "no_auth_found"}
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None
