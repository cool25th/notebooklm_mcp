#!/usr/bin/env python3
"""Antigravity MCP Auto-Configuration Installer.

This script automatically registers the NotebookLM MCP server with Antigravity IDE
by detecting the configuration directory and injecting server settings.
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_antigravity_config_paths() -> list[Path]:
    """Get possible Antigravity configuration paths based on OS.
    
    Returns:
        List of possible configuration file paths.
    """
    system = platform.system()
    paths = []
    
    if system == "Darwin":  # macOS
        # User settings folder (has proper permissions)
        paths.append(Path.home() / "Library" / "Application Support" / "Antigravity" / "User" / "globalStorage" / "mcp_servers.json")
        # Alternative locations
        paths.append(Path.home() / ".config" / "antigravity" / "mcp_servers.json")
        paths.append(Path.home() / ".antigravity" / "mcp.json")
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            paths.append(Path(appdata) / "Antigravity" / "User" / "globalStorage" / "mcp_servers.json")
        # Alternative locations
        paths.append(Path.home() / ".config" / "antigravity" / "mcp_servers.json")
        paths.append(Path.home() / ".antigravity" / "mcp.json")
    else:  # Linux
        paths.append(Path.home() / ".config" / "Antigravity" / "User" / "globalStorage" / "mcp_servers.json")
        paths.append(Path.home() / ".config" / "antigravity" / "mcp_servers.json")
        paths.append(Path.home() / ".antigravity" / "mcp.json")
    
    return paths


def find_existing_config() -> Path | None:
    """Find an existing Antigravity configuration file.
    
    Returns:
        Path to existing config, or None if not found.
    """
    for path in get_antigravity_config_paths():
        if path.exists():
            return path
    return None


def get_default_config_path() -> Path:
    """Get the default configuration path for the current OS.
    
    Returns:
        Default configuration file path.
    """
    return get_antigravity_config_paths()[0]


def get_server_command() -> tuple[str, list[str]]:
    """Get the command and args to run the MCP server.
    
    Returns:
        Tuple of (command, args).
    """
    # Get the Python executable from current environment
    python_path = sys.executable
    
    # Check if we should use the module or entry point
    try:
        # If installed via pip/uv, use the entry point
        result = subprocess.run(
            [python_path, "-m", "notebooklm_mcp.server", "--help"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return python_path, ["-m", "notebooklm_mcp.server"]
    except Exception:
        pass
    
    # Fallback to direct path
    script_dir = Path(__file__).parent
    server_path = script_dir / "src" / "notebooklm_mcp" / "server.py"
    if server_path.exists():
        return python_path, [str(server_path)]
    
    # Last resort: assume installed entry point
    return "notebooklm-mcp", []


def install_to_antigravity(
    config_path: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """Install NotebookLM MCP to Antigravity configuration.
    
    Args:
        config_path: Optional explicit config path. Auto-detected if not provided.
        force: Overwrite existing server configuration if present.
        dry_run: Only show what would be done without making changes.
    
    Returns:
        Installation result with status and details.
    """
    result = {
        "status": "pending",
        "config_path": None,
        "server_config": None,
        "backup_path": None,
        "errors": [],
        "warnings": [],
    }
    
    # Find or use provided config path
    if config_path:
        target_path = Path(config_path)
    else:
        existing = find_existing_config()
        if existing:
            target_path = existing
            result["warnings"].append(f"Using existing config: {existing}")
        else:
            target_path = get_default_config_path()
            result["warnings"].append(f"No existing config found, will create: {target_path}")
    
    result["config_path"] = str(target_path)
    
    # Load existing config or create new
    config = {"mcpServers": {}}
    if target_path.exists():
        try:
            with open(target_path) as f:
                config = json.load(f)
            if "mcpServers" not in config:
                config["mcpServers"] = {}
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON in config: {e}")
            result["status"] = "error"
            return result
    
    # Check if already installed
    if "notebooklm-mcp" in config["mcpServers"] and not force:
        result["status"] = "already_installed"
        result["warnings"].append("NotebookLM MCP is already configured. Use --force to overwrite.")
        return result
    
    # Get server command
    command, args = get_server_command()
    
    # Build server configuration
    server_config = {
        "command": command,
    }
    if args:
        server_config["args"] = args
    
    # Add environment variables for common settings
    server_config["env"] = {
        "NOTEBOOKLM_MCP_TRANSPORT": "stdio",
    }
    
    result["server_config"] = server_config
    
    if dry_run:
        result["status"] = "dry_run"
        return result
    
    # Create backup if modifying existing file
    if target_path.exists():
        backup_path = target_path.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            with open(backup_path, "w") as f:
                json.dump(config, f, indent=2)
            result["backup_path"] = str(backup_path)
        except Exception as e:
            result["warnings"].append(f"Could not create backup: {e}")
    
    # Update configuration
    config["mcpServers"]["notebooklm-mcp"] = server_config
    
    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write configuration
    try:
        with open(target_path, "w") as f:
            json.dump(config, f, indent=2)
        result["status"] = "success"
    except Exception as e:
        result["errors"].append(f"Failed to write config: {e}")
        result["status"] = "error"
    
    return result


def uninstall_from_antigravity(config_path: Path | None = None) -> dict:
    """Remove NotebookLM MCP from Antigravity configuration.
    
    Args:
        config_path: Optional explicit config path.
    
    Returns:
        Uninstallation result.
    """
    result = {
        "status": "pending",
        "config_path": None,
    }
    
    if config_path:
        target_path = Path(config_path)
    else:
        target_path = find_existing_config()
    
    if not target_path or not target_path.exists():
        result["status"] = "not_found"
        return result
    
    result["config_path"] = str(target_path)
    
    try:
        with open(target_path) as f:
            config = json.load(f)
        
        if "mcpServers" not in config or "notebooklm-mcp" not in config["mcpServers"]:
            result["status"] = "not_installed"
            return result
        
        del config["mcpServers"]["notebooklm-mcp"]
        
        with open(target_path, "w") as f:
            json.dump(config, f, indent=2)
        
        result["status"] = "success"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


def main():
    """CLI entry point for installer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Install NotebookLM MCP to Antigravity IDE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install.py             # Auto-detect and install
  python install.py --dry-run   # Show what would be done
  python install.py --force     # Overwrite existing config
  python install.py --uninstall # Remove from Antigravity
        """,
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Explicit path to mcp_config.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing server configuration",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove NotebookLM MCP from Antigravity",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )
    
    args = parser.parse_args()
    
    if args.uninstall:
        result = uninstall_from_antigravity(
            config_path=Path(args.config) if args.config else None
        )
    else:
        result = install_to_antigravity(
            config_path=Path(args.config) if args.config else None,
            force=args.force,
            dry_run=args.dry_run,
        )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        print()
        if result["status"] == "success":
            print("✅ NotebookLM MCP successfully installed to Antigravity!")
            print(f"   Config: {result['config_path']}")
            if result.get("backup_path"):
                print(f"   Backup: {result['backup_path']}")
            print()
            print("Next steps:")
            print("  1. Run: notebooklm-mcp-auth")
            print("  2. Restart Antigravity IDE")
            print("  3. Check Settings → Manage MCP Servers")
        elif result["status"] == "already_installed":
            print("ℹ️  NotebookLM MCP is already configured.")
            print("   Use --force to overwrite.")
        elif result["status"] == "dry_run":
            print("🔍 Dry run - no changes made")
            print(f"   Would write to: {result['config_path']}")
            print(f"   Server config: {json.dumps(result['server_config'], indent=2)}")
        elif result["status"] == "error":
            print("❌ Installation failed:")
            for error in result.get("errors", []):
                print(f"   - {error}")
        else:
            print(f"Status: {result['status']}")
        
        for warning in result.get("warnings", []):
            print(f"⚠️  {warning}")
        print()
    
    sys.exit(0 if result["status"] in ("success", "already_installed", "dry_run") else 1)


if __name__ == "__main__":
    main()
