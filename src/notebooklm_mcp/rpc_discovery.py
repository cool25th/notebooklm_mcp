"""RPC ID Discovery for NotebookLM.

Uses browser automation to intercept network requests and discover RPC IDs
for various NotebookLM operations.
"""

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote

# Cache file for discovered RPC IDs
CONFIG_DIR = Path.home() / ".notebooklm-mcp"
RPC_CACHE_FILE = CONFIG_DIR / "rpc_ids.json"
PROFILE_DIR = CONFIG_DIR / "browser-profile"

NOTEBOOKLM_URL = "https://notebooklm.google.com/"


def load_rpc_cache() -> dict[str, str]:
    """Load cached RPC IDs from disk."""
    if RPC_CACHE_FILE.exists():
        try:
            with open(RPC_CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_rpc_cache(rpc_ids: dict[str, str]) -> None:
    """Save RPC IDs to cache file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(RPC_CACHE_FILE, "w") as f:
        json.dump(rpc_ids, f, indent=2)


def extract_rpc_ids_from_request(request_url: str, post_data: str | None) -> list[str]:
    """Extract RPC IDs from a batchexecute request.
    
    Args:
        request_url: The request URL
        post_data: The POST data body
        
    Returns:
        List of RPC IDs found in the request
    """
    rpc_ids = []
    
    # Check URL for rpcids parameter
    if "rpcids=" in request_url:
        match = re.search(r'rpcids=([^&]+)', request_url)
        if match:
            ids = unquote(match.group(1))
            rpc_ids.extend(ids.split(","))
    
    # Check POST data for f.req parameter
    if post_data:
        try:
            # Parse form data
            if "f.req=" in post_data:
                # Extract f.req value
                match = re.search(r'f\.req=([^&]+)', post_data)
                if match:
                    freq_data = unquote(match.group(1))
                    # Parse the nested JSON array
                    parsed = json.loads(freq_data)
                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, list) and len(item) > 0:
                                for inner in item:
                                    if isinstance(inner, list) and len(inner) > 0:
                                        # First element is usually the RPC ID
                                        if isinstance(inner[0], str) and len(inner[0]) < 20:
                                            rpc_ids.append(inner[0])
        except (json.JSONDecodeError, IndexError):
            pass
    
    return list(set(rpc_ids))  # Remove duplicates


def discover_rpc_ids_interactive(notebook_id: str | None = None) -> dict[str, Any]:
    """Discover RPC IDs by intercepting browser network requests.
    
    Opens a browser window and instructs the user to perform actions.
    Captures the corresponding RPC IDs from network requests.
    
    Args:
        notebook_id: Optional notebook ID to use for discovery
        
    Returns:
        Dictionary with discovered RPC IDs and status
    """
    try:
        from patchright.sync_api import sync_playwright
    except ImportError:
        return {"error": "patchright not installed. Run: pip install patchright"}
    
    discovered_rpcs: dict[str, list[str]] = {
        "research": [],
        "other": [],
    }
    
    captured_requests: list[dict[str, Any]] = []
    
    def on_request(request):
        """Capture batchexecute requests."""
        if "batchexecute" in request.url:
            post_data = request.post_data
            rpc_ids = extract_rpc_ids_from_request(request.url, post_data)
            
            if rpc_ids:
                captured_requests.append({
                    "url": request.url,
                    "rpc_ids": rpc_ids,
                    "post_data": post_data,
                    "timestamp": time.time(),
                })
                print(f"  Captured RPC IDs: {rpc_ids}")
    
    print("RPC ID Discovery")
    print("=" * 50)
    print()
    print("A browser window will open.")
    print("Please perform the following actions:")
    print()
    print("  1. Navigate to a notebook")
    print("  2. Click 'Find sources' or 'Add source'")
    print("  3. Click 'Search the web' or 'Google Drive'")
    print("  4. Enter a search query and wait for results")
    print()
    print("Press Ctrl+C when done.")
    print()
    
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
            ],
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        # Set up request interception
        page.on("request", on_request)
        
        # Navigate to NotebookLM
        print("Navigating to NotebookLM...")
        if notebook_id:
            page.goto(f"{NOTEBOOKLM_URL}notebook/{notebook_id}", 
                     wait_until="domcontentloaded", timeout=60000)
        else:
            page.goto(NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=60000)
        
        print()
        print("Browser ready. Perform the actions, then close the browser.")
        print("Listening for network requests...")
        print()
        
        try:
            # Wait for user to close the browser or press Ctrl+C
            page.wait_for_event("close", timeout=300000)
        except KeyboardInterrupt:
            print("\nStopping capture...")
        except Exception:
            pass
        
        context.close()
    
    # Process captured requests
    all_rpc_ids = []
    for req in captured_requests:
        all_rpc_ids.extend(req["rpc_ids"])
    
    unique_rpc_ids = list(set(all_rpc_ids))
    
    print()
    print("=" * 50)
    print("Discovery Complete")
    print("=" * 50)
    print()
    print(f"Captured {len(captured_requests)} batchexecute requests")
    print(f"Found {len(unique_rpc_ids)} unique RPC IDs:")
    print()
    
    for rpc_id in unique_rpc_ids:
        print(f"  - {rpc_id}")
    
    # Save to cache
    if unique_rpc_ids:
        cache = load_rpc_cache()
        cache["discovered"] = unique_rpc_ids
        cache["timestamp"] = time.time()
        save_rpc_cache(cache)
        print()
        print(f"Saved to: {RPC_CACHE_FILE}")
        
        # Also save detailed request data for analysis
        requests_file = CONFIG_DIR / "rpc_requests.json"
        with open(requests_file, "w") as f:
            json.dump(captured_requests, f, indent=2)
        print(f"Request details: {requests_file}")
    
    return {
        "status": "success",
        "rpc_ids": unique_rpc_ids,
        "requests_captured": len(captured_requests),
    }


def discover_research_rpc_automated(notebook_id: str) -> dict[str, Any]:
    """Automatically discover Research RPC ID by triggering the action.
    
    This is a more automated approach that clicks the Research button
    and captures the resulting RPC ID.
    
    Args:
        notebook_id: The notebook ID to use
        
    Returns:
        Dictionary with discovered RPC ID and status
    """
    try:
        from patchright.sync_api import sync_playwright
    except ImportError:
        return {"error": "patchright not installed"}
    
    discovered_rpc_id = None
    
    def on_request(request):
        nonlocal discovered_rpc_id
        if "batchexecute" in request.url and discovered_rpc_id is None:
            post_data = request.post_data
            rpc_ids = extract_rpc_ids_from_request(request.url, post_data)
            # Look for unfamiliar RPC IDs (not the common ones)
            known_ids = {"HdY7pc", "JjGjQe", "gGZdY"}  # Query, describe, etc.
            for rpc_id in rpc_ids:
                if rpc_id not in known_ids:
                    discovered_rpc_id = rpc_id
                    print(f"  Found potential Research RPC ID: {rpc_id}")
    
    print("Automated RPC Discovery for Research")
    print("=" * 50)
    
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        page.on("request", on_request)
        
        # Navigate to notebook
        print(f"Navigating to notebook {notebook_id}...")
        page.goto(f"{NOTEBOOKLM_URL}notebook/{notebook_id}", 
                 wait_until="domcontentloaded", timeout=60000)
        
        time.sleep(3)  # Wait for page to load
        
        # Try to find and click "Find sources" or similar button
        print("Looking for Research/Find sources button...")
        
        # Common selectors for the research button
        selectors = [
            "button:has-text('Find sources')",
            "button:has-text('Add source')",
            "[data-action='research']",
            "[aria-label*='Find']",
            "[aria-label*='Research']",
        ]
        
        clicked = False
        for selector in selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  Clicking: {selector}")
                    page.locator(selector).first.click()
                    clicked = True
                    break
            except Exception:
                continue
        
        if clicked:
            time.sleep(2)
            
            # Look for web search option
            web_selectors = [
                "button:has-text('Search the web')",
                "[data-action='web-search']",
                "text=Search the web",
            ]
            
            for selector in web_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"  Clicking: {selector}")
                        page.locator(selector).first.click()
                        time.sleep(3)
                        break
                except Exception:
                    continue
        
        time.sleep(5)  # Wait for any network requests
        context.close()
    
    if discovered_rpc_id:
        # Save to cache
        cache = load_rpc_cache()
        cache["RESEARCH_START"] = discovered_rpc_id
        cache["timestamp"] = time.time()
        save_rpc_cache(cache)
        
        return {
            "status": "success",
            "rpc_id": discovered_rpc_id,
            "saved_to": str(RPC_CACHE_FILE),
        }
    
    return {
        "status": "not_found",
        "message": "Could not automatically discover Research RPC ID. Try interactive mode.",
    }


def main():
    """CLI entry point for RPC discovery."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discover NotebookLM RPC IDs")
    parser.add_argument("--notebook", "-n", help="Notebook ID to use")
    parser.add_argument("--auto", action="store_true", 
                       help="Try automated discovery (requires notebook ID)")
    
    args = parser.parse_args()
    
    if args.auto:
        if not args.notebook:
            print("Error: --auto requires --notebook <id>")
            return
        result = discover_research_rpc_automated(args.notebook)
    else:
        result = discover_rpc_ids_interactive(args.notebook)
    
    print()
    print("Result:", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
