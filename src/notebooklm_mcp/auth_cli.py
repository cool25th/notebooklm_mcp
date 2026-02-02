#!/usr/bin/env python3
"""CLI tool to authenticate with NotebookLM MCP.

Uses Patchright (Playwright fork) to automate browser login and extract cookies.

Usage:
    notebooklm-mcp-auth           # Opens browser, waits for login
    notebooklm-mcp-auth --file    # Import cookies from file
"""

import json
import re
import sys
import time
from pathlib import Path

from .auth import (
    AuthTokens,
    REQUIRED_COOKIES,
    get_cache_path,
    save_tokens_to_cache,
    validate_cookies,
)

NOTEBOOKLM_URL = "https://notebooklm.google.com/"
PROFILE_DIR = Path.home() / ".notebooklm-mcp" / "browser-profile"


def run_auth_flow() -> AuthTokens | None:
    """Run the authentication flow using Patchright."""
    print("NotebookLM MCP Authentication")
    print("=" * 40)
    print()
    
    try:
        from patchright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: patchright not installed")
        print("Run: pip install patchright")
        return None
    
    # Ensure profile directory exists
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Launching browser...")
    print("(Your login will be saved for future use)")
    print()
    
    with sync_playwright() as p:
        # Launch persistent browser context (saves login state)
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel="chrome",  # Use installed Chrome
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
            ],
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        # Navigate to NotebookLM
        print("Navigating to NotebookLM...")
        page.goto(NOTEBOOKLM_URL, wait_until="networkidle", timeout=30000)
        
        # Check if logged in
        current_url = page.url
        if "accounts.google.com" in current_url:
            print()
            print("=" * 40)
            print("PLEASE LOG IN")
            print("=" * 40)
            print()
            print("Log in to your Google account in the browser window.")
            print("This tool will wait for you to complete login...")
            print("(Press Ctrl+C to cancel)")
            print()
            
            # Wait for redirect back to NotebookLM (up to 5 minutes)
            try:
                page.wait_for_url("**/notebooklm.google.com/**", timeout=300000)
                print("Login successful!")
            except Exception:
                print("ERROR: Login timeout or cancelled")
                context.close()
                return None
        
        # Wait for page to fully load
        print("Waiting for page to load...")
        time.sleep(3)
        
        # Extract cookies
        print("Extracting cookies...")
        cookies_list = context.cookies()
        cookies = {c["name"]: c["value"] for c in cookies_list if ".google.com" in c.get("domain", "")}
        
        if not validate_cookies(cookies):
            print("WARNING: Some required cookies missing")
            print(f"Required: {REQUIRED_COOKIES}")
            print(f"Found: {[c for c in REQUIRED_COOKIES if c in cookies]}")
        
        # Extract CSRF token and session ID from page
        print("Extracting tokens...")
        html = page.content()
        
        csrf_token = ""
        csrf_match = re.search(r'"SNlM0e":"([^"]+)"', html)
        if csrf_match:
            csrf_token = csrf_match.group(1)
        
        session_id = ""
        sid_match = re.search(r'"FdrFJe":"([^"]+)"', html)
        if sid_match:
            session_id = sid_match.group(1)
        
        # Close browser
        context.close()
        
        # Create and save tokens
        tokens = AuthTokens(
            cookies=cookies,
            csrf_token=csrf_token,
            session_id=session_id,
            extracted_at=time.time(),
        )
        
        save_tokens_to_cache(tokens)
        
        print()
        print("=" * 40)
        print("SUCCESS!")
        print("=" * 40)
        print()
        print(f"Cookies: {len(cookies)} extracted")
        print(f"CSRF Token: {'Yes' if csrf_token else 'No'}")
        print(f"Session ID: {session_id[:20] + '...' if session_id else 'No'}")
        print()
        print(f"Saved to: {get_cache_path()}")
        print()
        print("You can now use the NotebookLM MCP server!")
        
        return tokens


def run_file_mode(cookie_file: str | None = None) -> AuthTokens | None:
    """Import cookies from a file."""
    print("NotebookLM MCP - Cookie File Import")
    print("=" * 50)
    print()
    
    if not cookie_file:
        print("Steps to extract cookies:")
        print()
        print("  1. Open Chrome and go to: https://notebooklm.google.com")
        print("  2. Press F12 to open DevTools")
        print("  3. Click 'Network' tab → Filter: 'batchexecute'")
        print("  4. Click any notebook to trigger a request")
        print("  5. Click a request → Headers → cookie: value")
        print("  6. Copy the value and paste into a text file")
        print()
        
        try:
            cookie_file = input("Enter path to cookie file: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return None
        
        if not cookie_file:
            print("ERROR: No file path provided")
            return None
        
        cookie_file = str(Path(cookie_file).expanduser())
    
    try:
        with open(cookie_file) as f:
            cookie_string = f.read().strip()
    except FileNotFoundError:
        print(f"ERROR: File not found: {cookie_file}")
        return None
    
    # Parse cookies
    cookies = {}
    for cookie in cookie_string.split(";"):
        if "=" in cookie:
            key, value = cookie.strip().split("=", 1)
            cookies[key.strip()] = value.strip()
    
    if not cookies:
        print("ERROR: Could not parse cookies")
        return None
    
    if not validate_cookies(cookies):
        print("WARNING: Some required cookies missing")
    
    tokens = AuthTokens(
        cookies=cookies,
        csrf_token="",
        session_id="",
        extracted_at=time.time(),
    )
    
    save_tokens_to_cache(tokens)
    
    print()
    print("SUCCESS!")
    print(f"Saved {len(cookies)} cookies to {get_cache_path()}")
    
    return tokens


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Authenticate with NotebookLM MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  notebooklm-mcp-auth              # Opens browser for login
  notebooklm-mcp-auth --file       # Import cookies from file
  notebooklm-mcp-auth --file ~/cookies.txt
        """
    )
    parser.add_argument("--file", nargs="?", const="", metavar="PATH",
                        help="Import cookies from file instead of browser")
    
    args = parser.parse_args()
    
    if args.file is not None:
        run_file_mode(args.file if args.file else None)
    else:
        run_auth_flow()


if __name__ == "__main__":
    main()
