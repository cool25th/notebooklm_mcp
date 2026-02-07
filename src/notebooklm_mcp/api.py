"""NotebookLM API Client.

This module provides the HTTP client for communicating with NotebookLM's internal API.
It uses Google's batchexecute RPC protocol with form-urlencoded requests.

Based on the reference implementation from jacob-bd/notebooklm-mcp-cli.
"""

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Configuration paths
CONFIG_DIR = Path.home() / ".notebooklm-mcp"
AUTH_FILE = CONFIG_DIR / "auth.json"


def parse_timestamp(ts_array: list | None) -> str | None:
    """Convert [seconds, nanoseconds] timestamp array to ISO format string."""
    if not ts_array or not isinstance(ts_array, list) or len(ts_array) < 1:
        return None
    try:
        seconds = ts_array[0]
        if not isinstance(seconds, (int, float)):
            return None
        dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OSError, OverflowError):
        return None


class AuthenticationError(Exception):
    """Raised when authentication fails (HTTP 401/403 or RPC Error 16)."""
    pass


@dataclass
class Notebook:
    """Represents a NotebookLM notebook."""
    id: str
    title: str
    source_count: int
    sources: list[dict]
    is_owned: bool = True
    is_shared: bool = False
    created_at: str | None = None
    modified_at: str | None = None

    @property
    def url(self) -> str:
        return f"https://notebooklm.google.com/notebook/{self.id}"


class NotebookLMClient:
    """Client for NotebookLM's internal batchexecute API.
    
    Based on the reference implementation from jacob-bd/notebooklm-mcp-cli.
    """
    
    BASE_URL = "https://notebooklm.google.com"
    BATCHEXECUTE_URL = f"{BASE_URL}/_/LabsTailwindUi/data/batchexecute"
    
    # RPC IDs from reference implementation
    RPC_LIST_NOTEBOOKS = "wXbhsf"
    RPC_GET_NOTEBOOK = "rLM1Ne"
    RPC_CREATE_NOTEBOOK = "CCqFvf"
    RPC_RENAME_NOTEBOOK = "s0tc2d"
    RPC_DELETE_NOTEBOOK = "WWINqb"
    RPC_ADD_SOURCE = "izAoDd"
    RPC_GET_SOURCE = "hizoJc"
    RPC_DELETE_SOURCE = "tGMBJ"
    RPC_GET_SUMMARY = "VfAZjd"
    RPC_GET_SOURCE_GUIDE = "tr032e"
    RPC_QUERY = "HdY7pc"  # Query endpoint is different
    RPC_RESEARCH_START = "QEJOe"  # Web/Drive research initiation
    RPC_RESEARCH_STATUS = "x7qWae"  # Research progress polling
    
    # Page fetch headers for CSRF extraction
    _PAGE_FETCH_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
    }
    
    def __init__(self):
        """Initialize the NotebookLM client."""
        self._http: httpx.Client | None = None
        self._csrf_token: str = ""
        self._session_id: str = ""
        self._cookies: dict[str, str] = {}
        self._load_auth()
        
        # Refresh CSRF token if not available
        if not self._csrf_token and self._cookies:
            self._refresh_auth_tokens()
    
    def _load_auth(self) -> None:
        """Load authentication data from disk."""
        if AUTH_FILE.exists():
            try:
                with open(AUTH_FILE) as f:
                    auth_data = json.load(f)
                self._csrf_token = auth_data.get("csrf_token", "")
                self._session_id = auth_data.get("session_id", "")
                self._cookies = auth_data.get("cookies", {})
                logger.info("Loaded authentication from %s", AUTH_FILE)
            except Exception as e:
                logger.warning("Failed to load auth file: %s", e)
    
    def _save_auth(self) -> None:
        """Save authentication data to disk."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            import time
            auth_data = {
                "cookies": self._cookies,
                "csrf_token": self._csrf_token,
                "session_id": self._session_id,
                "timestamp": time.time(),
            }
            with open(AUTH_FILE, "w") as f:
                json.dump(auth_data, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save auth file: %s", e)
    
    def _refresh_auth_tokens(self) -> None:
        """Refresh CSRF token and session ID by fetching the NotebookLM homepage."""
        cookie_header = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
        headers = {**self._PAGE_FETCH_HEADERS, "Cookie": cookie_header}
        
        with httpx.Client(headers=headers, follow_redirects=True, timeout=15.0) as client:
            response = client.get(f"{self.BASE_URL}/")
            
            if "accounts.google.com" in str(response.url):
                raise AuthenticationError(
                    "Authentication expired. Run 'notebooklm-mcp-auth' to re-authenticate."
                )
            
            if response.status_code != 200:
                raise AuthenticationError(f"Failed to fetch page: HTTP {response.status_code}")
            
            html = response.text
            
            # Extract CSRF token (SNlM0e)
            csrf_match = re.search(r'"SNlM0e":"([^"]+)"', html)
            if not csrf_match:
                raise AuthenticationError("Could not extract CSRF token from page.")
            
            self._csrf_token = csrf_match.group(1)
            
            # Extract session ID (FdrFJe)
            sid_match = re.search(r'"FdrFJe":"([^"]+)"', html)
            if sid_match:
                self._session_id = sid_match.group(1)
            
            # Save updated tokens
            self._save_auth()
            logger.info("Refreshed CSRF token and session ID")
    
    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._http is None:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
            
            self._http = httpx.Client(
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Origin": self.BASE_URL,
                    "Referer": f"{self.BASE_URL}/",
                    "Cookie": cookie_str,
                    "X-Same-Domain": "1",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                },
                timeout=30.0,
            )
        return self._http
    
    def _build_request_body(self, rpc_id: str, params: Any) -> str:
        """Build the batchexecute request body with CSRF token."""
        # JSON encode params with compact format
        params_json = json.dumps(params, separators=(',', ':'))
        
        # Wrap in RPC structure
        f_req = [[[rpc_id, params_json, None, "generic"]]]
        f_req_json = json.dumps(f_req, separators=(',', ':'))
        
        # URL encode
        body_parts = [f"f.req={urllib.parse.quote(f_req_json, safe='')}"]
        
        # Add CSRF token (critical!)
        if self._csrf_token:
            body_parts.append(f"at={urllib.parse.quote(self._csrf_token, safe='')}")
        
        # Trailing & to match browser format
        return "&".join(body_parts) + "&"
    
    def _build_url(self, rpc_id: str, source_path: str = "/") -> str:
        """Build the batchexecute URL with query params."""
        params = {
            "rpcids": rpc_id,
            "source-path": source_path,
            "bl": "boq_labs-tailwind-frontend_20260129.10_p0",  # Build label
            "hl": "en",
            "rt": "c",
        }
        
        if self._session_id:
            params["f.sid"] = self._session_id
        
        query = urllib.parse.urlencode(params)
        return f"{self.BATCHEXECUTE_URL}?{query}"
    
    def _parse_response(self, response_text: str) -> Any:
        """Parse the batchexecute response format."""
        # Remove anti-XSSI prefix
        if response_text.startswith(")]}'"):
            response_text = response_text[4:]
        
        lines = response_text.strip().split("\n")
        results = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            try:
                # Try as byte count followed by JSON
                int(line)
                i += 1
                if i < len(lines):
                    try:
                        data = json.loads(lines[i])
                        results.append(data)
                    except json.JSONDecodeError:
                        pass
                i += 1
            except ValueError:
                # Try as direct JSON
                try:
                    data = json.loads(line)
                    results.append(data)
                except json.JSONDecodeError:
                    pass
                i += 1
        
        return results
    
    def _extract_rpc_result(self, parsed_response: list, rpc_id: str) -> Any:
        """Extract the result for a specific RPC ID."""
        for chunk in parsed_response:
            if isinstance(chunk, list):
                for item in chunk:
                    if isinstance(item, list) and len(item) >= 3:
                        if item[0] == "wrb.fr" and item[1] == rpc_id:
                            # Check for auth error (error code 16)
                            if len(item) > 6 and item[6] == "generic" and isinstance(item[5], list) and 16 in item[5]:
                                raise AuthenticationError("RPC Error 16: Authentication expired")
                            
                            result_str = item[2]
                            if isinstance(result_str, str):
                                try:
                                    return json.loads(result_str)
                                except json.JSONDecodeError:
                                    return result_str
                            return result_str
        return None
    
    def _call_rpc(
        self,
        rpc_id: str,
        params: Any,
        path: str = "/",
        timeout: float | None = None,
        _retry: bool = False,
    ) -> Any:
        """Execute an RPC call with automatic retry on auth failure."""
        client = self._get_client()
        body = self._build_request_body(rpc_id, params)
        url = self._build_url(rpc_id, path)
        
        try:
            if timeout:
                response = client.post(url, content=body, timeout=timeout)
            else:
                response = client.post(url, content=body)
            
            response.raise_for_status()
            
            parsed = self._parse_response(response.text)
            result = self._extract_rpc_result(parsed, rpc_id)
            return result
            
        except (httpx.HTTPStatusError, AuthenticationError) as e:
            is_http_auth = isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (401, 403)
            is_rpc_auth = isinstance(e, AuthenticationError)
            
            if (is_http_auth or is_rpc_auth) and not _retry:
                # Try refreshing tokens
                try:
                    self._refresh_auth_tokens()
                    self._http = None  # Reset client
                    return self._call_rpc(rpc_id, params, path, timeout, _retry=True)
                except Exception:
                    pass
            
            raise AuthenticationError(
                "Authentication expired. Run 'notebooklm-mcp-auth' to re-authenticate."
            )
    
    # =========================================================================
    # Notebook Operations
    # =========================================================================
    
    def list_notebooks(self) -> list[Notebook]:
        """List all notebooks."""
        # Correct params from reference implementation
        params = [None, 1, None, [2]]
        result = self._call_rpc(self.RPC_LIST_NOTEBOOKS, params)
        
        notebooks = []
        if result and isinstance(result, list):
            notebook_list = result[0] if result and isinstance(result[0], list) else result
            
            for nb_data in notebook_list:
                if isinstance(nb_data, list) and len(nb_data) >= 3:
                    title = nb_data[0] if isinstance(nb_data[0], str) else "Untitled"
                    sources_data = nb_data[1] if len(nb_data) > 1 else []
                    notebook_id = nb_data[2] if len(nb_data) > 2 else None
                    
                    is_owned = True
                    is_shared = False
                    created_at = None
                    modified_at = None
                    
                    if len(nb_data) > 5 and isinstance(nb_data[5], list) and len(nb_data[5]) > 0:
                        metadata = nb_data[5]
                        is_owned = metadata[0] == 1  # 1 = mine, 2 = shared
                        if len(metadata) > 1:
                            is_shared = bool(metadata[1])
                        if len(metadata) > 5:
                            modified_at = parse_timestamp(metadata[5])
                        if len(metadata) > 8:
                            created_at = parse_timestamp(metadata[8])
                    
                    sources = []
                    if isinstance(sources_data, list):
                        for src in sources_data:
                            if isinstance(src, list) and len(src) >= 2:
                                src_ids = src[0] if src[0] else []
                                src_title = src[1] if len(src) > 1 else "Untitled"
                                src_id = src_ids[0] if isinstance(src_ids, list) and src_ids else src_ids
                                sources.append({"id": src_id, "title": src_title})
                    
                    if notebook_id:
                        notebooks.append(Notebook(
                            id=notebook_id,
                            title=title,
                            source_count=len(sources),
                            sources=sources,
                            is_owned=is_owned,
                            is_shared=is_shared,
                            created_at=created_at,
                            modified_at=modified_at,
                        ))
        
        return notebooks
    
    def get_notebook(self, notebook_id: str) -> dict[str, Any]:
        """Get notebook details."""
        result = self._call_rpc(
            self.RPC_GET_NOTEBOOK,
            [notebook_id, None, [2], None, 0],
            f"/notebook/{notebook_id}",
        )
        
        # Parse raw RPC response into structured dict
        if isinstance(result, list) and len(result) >= 3:
            title = result[0] if isinstance(result[0], str) else ""
            nb_id = result[2] if len(result) > 2 else notebook_id
            
            # Parse sources
            sources = []
            if isinstance(result[1], list):
                for src in result[1]:
                    if isinstance(src, list) and len(src) >= 2:
                        src_id = src[0][0] if isinstance(src[0], list) and src[0] else src[0]
                        src_title = src[1] if len(src) > 1 else "Untitled"
                        src_url = ""
                        if len(src) > 2 and isinstance(src[2], list) and len(src[2]) > 7:
                            urls = src[2][7]
                            if isinstance(urls, list) and urls:
                                src_url = urls[0]
                        sources.append({"id": src_id, "title": src_title, "url": src_url})
            
            # Parse metadata
            metadata = {}
            if len(result) > 5 and isinstance(result[5], list):
                meta = result[5]
                metadata["is_owned"] = meta[0] == 1 if len(meta) > 0 else True
                if len(meta) > 5:
                    metadata["modified_at"] = parse_timestamp(meta[5])
                if len(meta) > 8:
                    metadata["created_at"] = parse_timestamp(meta[8])
            
            return {
                "id": nb_id,
                "title": title,
                "sources": sources,
                "source_count": len(sources),
                **metadata,
            }
        
        if isinstance(result, dict):
            return result
        return {"data": result}
    
    def create_notebook(self, name: str, description: str = "") -> dict[str, Any]:
        """Create a new notebook."""
        params = [name]
        result = self._call_rpc(self.RPC_CREATE_NOTEBOOK, params)
        return {"status": "created", "data": result}
    
    def rename_notebook(self, notebook_id: str, new_name: str) -> dict[str, Any]:
        """Rename a notebook."""
        params = [notebook_id, new_name]
        result = self._call_rpc(self.RPC_RENAME_NOTEBOOK, params, f"/notebook/{notebook_id}")
        return {"status": "renamed", "data": result}
    
    def delete_notebook(self, notebook_id: str) -> dict[str, Any]:
        """Delete a notebook."""
        params = [notebook_id]
        result = self._call_rpc(self.RPC_DELETE_NOTEBOOK, params)
        return {"status": "deleted", "data": result}
    
    def get_notebook_summary(self, notebook_id: str) -> dict[str, Any]:
        """Get AI-generated summary and suggested topics for a notebook."""
        result = self._call_rpc(
            self.RPC_GET_SUMMARY, [notebook_id, [2]], f"/notebook/{notebook_id}"
        )
        
        summary = ""
        suggested_topics = []
        
        if result and isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], list) and len(result[0]) > 0:
                summary = result[0][0]
            
            if len(result) > 1 and result[1]:
                topics_data = result[1][0] if isinstance(result[1], list) and len(result[1]) > 0 else []
                for topic in topics_data:
                    if isinstance(topic, list) and len(topic) >= 2:
                        suggested_topics.append({
                            "question": topic[0],
                            "prompt": topic[1],
                        })
        
        return {"summary": summary, "suggested_topics": suggested_topics}
    
    # =========================================================================
    # Source Operations
    # =========================================================================
    
    def add_source(
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
        if source_type == "url":
            params = [notebook_id, [[None, url, None, None, None, None, 5]]]
        elif source_type == "text":
            params = [notebook_id, [[None, None, text, title or "Pasted Text", None, None, 4]]]
        else:
            return {"error": f"Unsupported source type: {source_type}"}
        
        result = self._call_rpc(self.RPC_ADD_SOURCE, params, f"/notebook/{notebook_id}", timeout=wait_timeout)
        return {"status": "added", "data": result}
    
    def list_sources(self, notebook_id: str) -> dict[str, Any]:
        """List sources in a notebook."""
        nb = self.get_notebook(notebook_id)
        if not nb:
            return {"sources": [], "count": 0}
        
        # get_notebook now returns a dict with parsed sources
        sources = nb.get("sources", [])
        return {"sources": sources, "count": len(sources)}
    
    def delete_source(self, notebook_id: str, source_id: str) -> dict[str, Any]:
        """Delete a source from a notebook."""
        params = [notebook_id, [[source_id]]]
        result = self._call_rpc(self.RPC_DELETE_SOURCE, params, f"/notebook/{notebook_id}")
        return {"status": "deleted", "data": result}
    
    def get_source_guide(self, source_id: str) -> dict[str, Any]:
        """Get AI-generated summary and keywords for a source."""
        result = self._call_rpc(self.RPC_GET_SOURCE_GUIDE, [[[[source_id]]]], "/")
        
        summary = ""
        keywords = []
        
        if result and isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], list):
                if len(result[0]) > 0 and isinstance(result[0][0], list):
                    inner = result[0][0]
                    if len(inner) > 1 and isinstance(inner[1], list) and len(inner[1]) > 0:
                        summary = inner[1][0]
                    if len(inner) > 2 and isinstance(inner[2], list) and len(inner[2]) > 0:
                        keywords = inner[2][0] if isinstance(inner[2][0], list) else []
        
        return {"summary": summary, "keywords": keywords}
    
    # =========================================================================
    # Query Operations (placeholder - needs streaming endpoint)
    # =========================================================================
    
    def query_notebook(self, notebook_id: str, query: str) -> dict[str, Any]:
        """Query the notebook AI. Note: This may require streaming implementation."""
        return {
            "status": "not_fully_implemented",
            "message": "Query requires streaming gRPC implementation. Use browser for now."
        }
    
    # =========================================================================
    # Research Operations
    # =========================================================================
    
    def start_research(
        self,
        notebook_id: str,
        query: str,
        search_type: str = "web",
    ) -> dict[str, Any]:
        """Start web or Drive research to discover sources.
        
        Args:
            notebook_id: The ID of the notebook.
            query: The research query.
            search_type: "web" for web search, "drive" for Google Drive search.
        
        Returns:
            Research session ID and initial status.
        """
        # search_type mapping: 1 = web, 2 = drive
        type_map = {"web": 1, "drive": 2}
        search_type_code = type_map.get(search_type, 1)
        
        # Construct research request params
        # Based on reverse-engineered batchexecute format
        params = [notebook_id, query, search_type_code]
        
        try:
            result = self._call_rpc(
                self.RPC_RESEARCH_START,
                params,
                f"/notebook/{notebook_id}",
                timeout=60.0,  # Research may take longer
            )
            
            # Parse research session response
            if result and isinstance(result, list):
                research_id = None
                status = "pending"
                
                # Extract research_id from response
                if len(result) > 0:
                    research_id = result[0] if isinstance(result[0], str) else str(result[0])
                
                if len(result) > 1:
                    # Status code: 0 = pending, 1 = in_progress, 2 = completed, 3 = failed
                    status_code = result[1] if isinstance(result[1], int) else 0
                    status_map = {0: "pending", 1: "in_progress", 2: "completed", 3: "failed"}
                    status = status_map.get(status_code, "pending")
                
                return {
                    "status": "started",
                    "research_id": research_id,
                    "research_status": status,
                    "search_type": search_type,
                    "query": query,
                }
            
            return {
                "status": "started",
                "research_id": None,
                "message": "Research initiated but could not parse response",
                "raw_result": result,
            }
            
        except Exception as e:
            logger.error(f"Research start failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_research_status(
        self,
        notebook_id: str,
        research_id: str,
    ) -> dict[str, Any]:
        """Check research progress and get discovered sources.
        
        Args:
            notebook_id: The ID of the notebook.
            research_id: The ID of the research session.
        
        Returns:
            Research status and list of discovered sources.
        """
        params = [notebook_id, research_id]
        
        try:
            result = self._call_rpc(
                self.RPC_RESEARCH_STATUS,
                params,
                f"/notebook/{notebook_id}",
            )
            
            status = "unknown"
            discovered_sources = []
            
            if result and isinstance(result, list):
                # Extract status
                if len(result) > 0:
                    status_code = result[0] if isinstance(result[0], int) else 0
                    status_map = {0: "pending", 1: "in_progress", 2: "completed", 3: "failed"}
                    status = status_map.get(status_code, "unknown")
                
                # Extract discovered sources
                if len(result) > 1 and isinstance(result[1], list):
                    for idx, source_data in enumerate(result[1]):
                        if isinstance(source_data, list) and len(source_data) >= 2:
                            source = {
                                "index": idx,
                                "url": source_data[0] if source_data[0] else "",
                                "title": source_data[1] if len(source_data) > 1 else "Untitled",
                                "summary": source_data[2] if len(source_data) > 2 else "",
                            }
                            discovered_sources.append(source)
            
            return {
                "research_id": research_id,
                "status": status,
                "discovered_sources": discovered_sources,
                "source_count": len(discovered_sources),
            }
            
        except Exception as e:
            logger.error(f"Research status check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def import_research_sources(
        self,
        notebook_id: str,
        research_id: str,
        source_indices: list[int] | None = None,
    ) -> dict[str, Any]:
        """Import discovered sources from research into the notebook.
        
        Args:
            notebook_id: The ID of the notebook.
            research_id: The ID of the research session.
            source_indices: Optional list of source indices to import.
                          If None, imports all discovered sources.
        
        Returns:
            Import status and details.
        """
        # First, get the current research status to know what sources are available
        status_result = self.get_research_status(notebook_id, research_id)
        
        if status_result.get("status") == "error":
            return status_result
        
        if status_result.get("status") != "completed":
            return {
                "status": "error",
                "error": f"Research not completed. Current status: {status_result.get('status')}",
            }
        
        discovered_sources = status_result.get("discovered_sources", [])
        
        if not discovered_sources:
            return {"status": "error", "error": "No sources discovered to import"}
        
        # Determine which sources to import
        if source_indices is None:
            indices_to_import = list(range(len(discovered_sources)))
        else:
            indices_to_import = [i for i in source_indices if 0 <= i < len(discovered_sources)]
        
        if not indices_to_import:
            return {"status": "error", "error": "No valid source indices provided"}
        
        imported = []
        failed = []
        
        for idx in indices_to_import:
            source = discovered_sources[idx]
            url = source.get("url")
            
            if not url:
                failed.append({"index": idx, "error": "No URL"})
                continue
            
            try:
                # Use add_source to import the URL
                result = self.add_source(notebook_id, "url", url=url)
                if result.get("status") == "added":
                    imported.append({
                        "index": idx,
                        "url": url,
                        "title": source.get("title", ""),
                    })
                else:
                    failed.append({"index": idx, "error": result.get("error", "Unknown error")})
            except Exception as e:
                failed.append({"index": idx, "error": str(e)})
        
        return {
            "status": "completed",
            "imported_count": len(imported),
            "failed_count": len(failed),
            "imported": imported,
            "failed": failed if failed else None,
        }
    
    # =========================================================================
    # Auth Operations
    # =========================================================================
    
    def refresh_auth(self) -> dict[str, Any]:
        """Reload auth tokens from disk and reset HTTP client."""
        if self._http:
            self._http.close()
            self._http = None
        
        self._load_auth()
        
        if self._cookies:
            return {
                "status": "refreshed",
                "has_csrf_token": bool(self._csrf_token),
                "has_session_id": bool(self._session_id),
                "cookies_count": len(self._cookies),
            }
        return {"status": "no_auth_found"}
    
    def set_auth(self, cookie_string: str) -> dict[str, Any]:
        """Set authentication from a cookie string.
        
        Args:
            cookie_string: Browser cookie string (copied from DevTools).
                          Format: "key1=value1; key2=value2; ..."
        
        Returns:
            Status and number of cookies saved.
        """
        import time
        
        # Parse cookie string
        cookies = {}
        for cookie in cookie_string.split(";"):
            cookie = cookie.strip()
            if "=" in cookie:
                key, value = cookie.split("=", 1)
                cookies[key.strip()] = value.strip()
        
        if not cookies:
            return {"status": "error", "error": "No cookies parsed from string"}
        
        # Check for required cookies
        required = ["SID", "__Secure-1PSID", "HSID", "SSID", "APISID", "SAPISID"]
        missing = [c for c in required if c not in cookies]
        
        if missing:
            logger.warning(f"Missing required cookies: {missing}")
        
        # Update client state
        self._cookies = cookies
        self._csrf_token = ""  # Will be refreshed on next request
        self._session_id = ""
        
        # Reset HTTP client
        if self._http:
            self._http.close()
            self._http = None
        
        # Save to disk
        self._save_auth()
        
        # Try to refresh CSRF token
        try:
            self._refresh_auth_tokens()
            return {
                "status": "success",
                "cookies_count": len(cookies),
                "has_csrf_token": bool(self._csrf_token),
                "has_session_id": bool(self._session_id),
                "missing_cookies": missing if missing else None,
            }
        except Exception as e:
            return {
                "status": "partial_success",
                "cookies_count": len(cookies),
                "warning": f"Cookies saved but CSRF refresh failed: {e}",
                "missing_cookies": missing if missing else None,
            }
    
    def close(self) -> None:
        """Close the HTTP client."""
        if self._http:
            self._http.close()
            self._http = None
