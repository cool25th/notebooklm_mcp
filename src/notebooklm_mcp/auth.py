"""NotebookLM MCP Authentication Module.

This module provides browser-based authentication for NotebookLM using Patchright
(a Playwright fork). It extracts cookies and CSRF tokens from the browser session.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration paths
CONFIG_DIR = Path.home() / ".notebooklm-mcp"
AUTH_FILE = CONFIG_DIR / "auth.json"
CHROME_PROFILE_DIR = CONFIG_DIR / "chrome-profile"

# Set browser path to project-local folder (avoids macOS permission issues)
PROJECT_DIR = Path(__file__).parent.parent.parent
BROWSERS_DIR = PROJECT_DIR / ".browsers"
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(BROWSERS_DIR))


async def authenticate(
    headless: bool = False,
    timeout: int = 120,
    devtools_timeout: int = 10,
) -> dict:
    """Authenticate with NotebookLM using browser automation.
    
    Args:
        headless: Run browser in headless mode (not recommended for login).
        timeout: Maximum time to wait for login (seconds).
        devtools_timeout: Time to wait for DevTools connection (seconds).
    
    Returns:
        Authentication result with status and token info.
    """
    try:
        from patchright.async_api import async_playwright
    except ImportError:
        return {
            "error": "Patchright not installed. Run: pip install patchright && patchright install chromium"
        }
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    print("🔐 Starting NotebookLM authentication...")
    print("   A browser window will open. Please log in with your Google account.")
    print()
    
    async with async_playwright() as p:
        # Launch browser with persistent context for login persistence
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_PROFILE_DIR),
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )
        
        try:
            page = await browser.new_page()
            
            # Navigate to NotebookLM
            print("📱 Opening NotebookLM...")
            await page.goto("https://notebooklm.google.com/")
            
            # Wait for user to complete login
            print("⏳ Waiting for login... (you have %d seconds)" % timeout)
            print("   Complete Google sign-in in the browser window.")
            print()
            
            # Wait for the main app to load (indicates successful login)
            try:
                await page.wait_for_selector(
                    '[data-testid="create-notebook-button"], [aria-label="Create notebook"], .notebook-list',
                    timeout=timeout * 1000,
                )
                print("✅ Login detected!")
            except Exception:
                print("❌ Login timeout. Please try again.")
                return {"error": "Login timeout", "status": "timeout"}
            
            # Extract cookies
            cookies = await browser.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            
            # Extract CSRF token from page
            csrf_token = None
            session_id = None
            
            # Try to extract from page scripts
            try:
                scripts = await page.evaluate("""
                    () => {
                        const scripts = document.querySelectorAll('script');
                        for (const script of scripts) {
                            const content = script.textContent || '';
                            if (content.includes('WIZ_global_data')) {
                                return content;
                            }
                        }
                        return null;
                    }
                """)
                
                if scripts:
                    # Parse CSRF token from WIZ_global_data
                    import re
                    csrf_match = re.search(r'"FdrFJe":"([^"]+)"', scripts)
                    if csrf_match:
                        csrf_token = csrf_match.group(1)
                    
                    sid_match = re.search(r'"SNlM0e":"([^"]+)"', scripts)
                    if sid_match:
                        session_id = sid_match.group(1)
            except Exception as e:
                logger.warning("Failed to extract tokens from page: %s", e)
            
            # Get email if available
            email = None
            try:
                email_element = await page.query_selector('[data-email], [aria-label*="@"]')
                if email_element:
                    email = await email_element.get_attribute("data-email")
                    if not email:
                        label = await email_element.get_attribute("aria-label")
                        if label and "@" in label:
                            email = label.split()[-1] if "@" in label.split()[-1] else None
            except Exception:
                pass
            
            # Save authentication data
            auth_data = {
                "cookies": cookie_dict,
                "csrf_token": csrf_token,
                "session_id": session_id,
                "email": email,
                "timestamp": asyncio.get_event_loop().time(),
            }
            
            with open(AUTH_FILE, "w") as f:
                json.dump(auth_data, f, indent=2)
            
            print()
            print("🎉 SUCCESS! Authentication saved to:", AUTH_FILE)
            if email:
                print("   Account:", email)
            print()
            print("Next steps:")
            print("  1. Configure your MCP client (Claude Code, Cursor, etc.)")
            print("  2. Add: notebooklm-mcp to your MCP servers")
            print()
            
            return {
                "status": "success",
                "email": email,
                "has_csrf_token": bool(csrf_token),
                "has_session_id": bool(session_id),
                "cookies_count": len(cookie_dict),
            }
            
        finally:
            await browser.close()


def main():
    """CLI entry point for authentication."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="NotebookLM MCP Authentication Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  notebooklm-mcp-auth              # Normal mode (browser window opens)
  notebooklm-mcp-auth --headless   # Headless mode (not recommended for first login)
  notebooklm-mcp-auth --timeout 180  # Extended timeout for slow connections
        """,
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (only works if already logged in)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Timeout for login in seconds (default: 120)",
    )
    parser.add_argument(
        "--devtools-timeout",
        type=int,
        default=10,
        help="Timeout for DevTools connection (default: 10)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    result = asyncio.run(
        authenticate(
            headless=args.headless,
            timeout=args.timeout,
            devtools_timeout=args.devtools_timeout,
        )
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
