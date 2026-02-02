"""NotebookLM MCP Server.

This module provides the MCP server that exposes NotebookLM functionality
to AI agents like Antigravity.
"""

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from .api import NotebookLMClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    name="notebooklm-mcp",
    instructions="NotebookLM MCP Server - Access Google NotebookLM's RAG capabilities",
)

# Global client instance
_client: NotebookLMClient | None = None


def get_client() -> NotebookLMClient:
    """Get or create the NotebookLM API client."""
    global _client
    if _client is None:
        _client = NotebookLMClient()
    return _client


# =============================================================================
# Notebook Tools
# =============================================================================

@mcp.tool()
async def notebook_list() -> dict[str, Any]:
    """List all NotebookLM notebooks.
    
    Returns:
        A dictionary containing the list of notebooks with their IDs, names, and metadata.
    """
    client = get_client()
    notebooks = await asyncio.to_thread(client.list_notebooks)
    return {
        "notebooks": [
            {
                "id": nb.id,
                "title": nb.title,
                "source_count": nb.source_count,
                "url": nb.url,
                "is_owned": nb.is_owned,
                "is_shared": nb.is_shared,
                "created_at": nb.created_at,
                "modified_at": nb.modified_at,
            }
            for nb in notebooks
        ],
        "count": len(notebooks),
    }


@mcp.tool()
async def notebook_create(name: str, description: str = "") -> dict[str, Any]:
    """Create a new NotebookLM notebook.
    
    Args:
        name: The name of the notebook to create.
        description: Optional description for the notebook.
    
    Returns:
        The created notebook details including its ID.
    """
    client = get_client()
    return await asyncio.to_thread(client.create_notebook, name, description)


@mcp.tool()
async def notebook_get(notebook_id: str) -> dict[str, Any]:
    """Get details of a specific notebook including its sources.
    
    Args:
        notebook_id: The ID of the notebook to retrieve.
    
    Returns:
        Notebook details including sources and metadata.
    """
    client = get_client()
    return await asyncio.to_thread(client.get_notebook, notebook_id)


@mcp.tool()
async def notebook_describe(notebook_id: str) -> dict[str, Any]:
    """Get an AI-generated summary and suggested topics for a notebook.
    
    Args:
        notebook_id: The ID of the notebook to describe.
    
    Returns:
        AI summary and suggested conversation topics.
    """
    client = get_client()
    return await asyncio.to_thread(client.get_notebook_summary, notebook_id)


@mcp.tool()
async def notebook_rename(notebook_id: str, new_name: str) -> dict[str, Any]:
    """Rename a notebook.
    
    Args:
        notebook_id: The ID of the notebook to rename.
        new_name: The new name for the notebook.
    
    Returns:
        Updated notebook details.
    """
    client = get_client()
    return await asyncio.to_thread(client.rename_notebook, notebook_id, new_name)


@mcp.tool()
async def notebook_delete(notebook_id: str, confirm: bool = False) -> dict[str, Any]:
    """Delete a notebook. Requires confirm=True.
    
    Args:
        notebook_id: The ID of the notebook to delete.
        confirm: Must be True to confirm deletion.
    
    Returns:
        Deletion status.
    """
    if not confirm:
        return {"error": "Deletion requires confirm=True"}
    client = get_client()
    return await asyncio.to_thread(client.delete_notebook, notebook_id)


# =============================================================================
# Source Tools
# =============================================================================

@mcp.tool()
async def source_add(
    notebook_id: str,
    source_type: str,
    url: str = "",
    text: str = "",
    title: str = "",
    file_path: str = "",
    wait: bool = True,
    wait_timeout: float = 120.0,
) -> dict[str, Any]:
    """Add a source to a notebook.
    
    Args:
        notebook_id: The ID of the notebook.
        source_type: Type of source: "url", "text", "file", or "drive".
        url: URL to add (for source_type="url").
        text: Text content to add (for source_type="text").
        title: Optional title for the source.
        file_path: Path to file (for source_type="file").
        wait: Whether to wait for processing to complete.
        wait_timeout: Timeout in seconds for waiting.
    
    Returns:
        Source details and processing status.
    """
    client = get_client()
    return await asyncio.to_thread(
        client.add_source,
        notebook_id=notebook_id,
        source_type=source_type,
        url=url,
        text=text,
        title=title,
        file_path=file_path,
        wait=wait,
        wait_timeout=wait_timeout,
    )


@mcp.tool()
async def source_list(notebook_id: str) -> dict[str, Any]:
    """List all sources in a notebook with their freshness status.
    
    Args:
        notebook_id: The ID of the notebook.
    
    Returns:
        List of sources with metadata and freshness information.
    """
    client = get_client()
    return await asyncio.to_thread(client.list_sources, notebook_id)


@mcp.tool()
async def source_delete(
    notebook_id: str, source_id: str, confirm: bool = False
) -> dict[str, Any]:
    """Delete a source from a notebook. Requires confirm=True.
    
    Args:
        notebook_id: The ID of the notebook.
        source_id: The ID of the source to delete.
        confirm: Must be True to confirm deletion.
    
    Returns:
        Deletion status.
    """
    if not confirm:
        return {"error": "Deletion requires confirm=True"}
    client = get_client()
    return await client.delete_source(notebook_id, source_id)


@mcp.tool()
async def source_describe(notebook_id: str, source_id: str) -> dict[str, Any]:
    """Get an AI summary of a specific source with keywords.
    
    Args:
        notebook_id: The ID of the notebook.
        source_id: The ID of the source to describe.
    
    Returns:
        AI-generated summary and keywords.
    """
    client = get_client()
    return await client.describe_source(notebook_id, source_id)


@mcp.tool()
async def source_get_content(notebook_id: str, source_id: str) -> dict[str, Any]:
    """Get the raw text content of a source.
    
    Args:
        notebook_id: The ID of the notebook.
        source_id: The ID of the source.
    
    Returns:
        Raw text content of the source.
    """
    client = get_client()
    return await client.get_source_content(notebook_id, source_id)


# =============================================================================
# Query Tools
# =============================================================================

@mcp.tool()
async def notebook_query(notebook_id: str, query: str) -> dict[str, Any]:
    """Ask the AI about sources in a notebook.
    
    Args:
        notebook_id: The ID of the notebook to query.
        query: The question to ask about the sources.
    
    Returns:
        AI-generated response based on the notebook sources.
    """
    client = get_client()
    return await client.query_notebook(notebook_id, query)


@mcp.tool()
async def chat_configure(
    notebook_id: str,
    goal: str = "",
    response_length: str = "medium",
) -> dict[str, Any]:
    """Configure chat settings for a notebook.
    
    Args:
        notebook_id: The ID of the notebook.
        goal: The conversation goal (e.g., "learning guide", "expert consultation").
        response_length: Response length: "short", "medium", or "long".
    
    Returns:
        Updated chat configuration.
    """
    client = get_client()
    return await client.configure_chat(notebook_id, goal, response_length)


# =============================================================================
# Studio Tools
# =============================================================================

@mcp.tool()
async def studio_create(
    notebook_id: str,
    artifact_type: str,
    format: str = "",
    difficulty: str = "medium",
) -> dict[str, Any]:
    """Create studio content (audio, video, report, quiz, etc.).
    
    Args:
        notebook_id: The ID of the notebook.
        artifact_type: Type of content: "audio", "video", "report", "quiz", 
                      "flashcards", "mind_map", "slide_deck", "infographic", "data_table".
        format: Format variant (e.g., "deep_dive", "brief" for audio).
        difficulty: Difficulty level for quizzes: "easy", "medium", "hard".
    
    Returns:
        Creation status and artifact ID.
    """
    client = get_client()
    return await client.create_studio_content(notebook_id, artifact_type, format, difficulty)


@mcp.tool()
async def studio_status(notebook_id: str, artifact_id: str) -> dict[str, Any]:
    """Check the generation status of studio content.
    
    Args:
        notebook_id: The ID of the notebook.
        artifact_id: The ID of the artifact.
    
    Returns:
        Generation status and download URL if complete.
    """
    client = get_client()
    return await client.get_studio_status(notebook_id, artifact_id)


@mcp.tool()
async def download_artifact(
    notebook_id: str,
    artifact_id: str,
    artifact_type: str,
    output_path: str = "",
) -> dict[str, Any]:
    """Download a generated artifact.
    
    Args:
        notebook_id: The ID of the notebook.
        artifact_id: The ID of the artifact.
        artifact_type: Type of artifact.
        output_path: Optional path to save the file.
    
    Returns:
        Download status and file path.
    """
    client = get_client()
    return await client.download_artifact(notebook_id, artifact_id, artifact_type, output_path)


# =============================================================================
# Research Tools
# =============================================================================

@mcp.tool()
async def research_start(
    notebook_id: str,
    query: str,
    search_type: str = "web",
) -> dict[str, Any]:
    """Start web or Drive research.
    
    Args:
        notebook_id: The ID of the notebook.
        query: The research query.
        search_type: "web" or "drive".
    
    Returns:
        Research session ID and status.
    """
    client = get_client()
    return await client.start_research(notebook_id, query, search_type)


@mcp.tool()
async def research_status(notebook_id: str, research_id: str) -> dict[str, Any]:
    """Check research progress.
    
    Args:
        notebook_id: The ID of the notebook.
        research_id: The ID of the research session.
    
    Returns:
        Research status and discovered sources.
    """
    client = get_client()
    return await client.get_research_status(notebook_id, research_id)


@mcp.tool()
async def research_import(
    notebook_id: str,
    research_id: str,
    source_indices: list[int] | None = None,
) -> dict[str, Any]:
    """Import discovered sources from research.
    
    Args:
        notebook_id: The ID of the notebook.
        research_id: The ID of the research session.
        source_indices: Optional list of source indices to import. Imports all if not specified.
    
    Returns:
        Import status.
    """
    client = get_client()
    return await client.import_research_sources(notebook_id, research_id, source_indices)


# =============================================================================
# Sharing Tools
# =============================================================================

@mcp.tool()
async def notebook_share_status(notebook_id: str) -> dict[str, Any]:
    """Get sharing settings for a notebook.
    
    Args:
        notebook_id: The ID of the notebook.
    
    Returns:
        Current sharing settings and collaborators.
    """
    client = get_client()
    return await client.get_share_status(notebook_id)


@mcp.tool()
async def notebook_share_public(notebook_id: str, enabled: bool) -> dict[str, Any]:
    """Enable or disable public link sharing.
    
    Args:
        notebook_id: The ID of the notebook.
        enabled: True to enable public link, False to disable.
    
    Returns:
        Updated sharing status and public URL if enabled.
    """
    client = get_client()
    return await client.set_public_sharing(notebook_id, enabled)


@mcp.tool()
async def notebook_share_invite(
    notebook_id: str,
    email: str,
    role: str = "viewer",
) -> dict[str, Any]:
    """Invite a collaborator to a notebook.
    
    Args:
        notebook_id: The ID of the notebook.
        email: Email address of the collaborator.
        role: "viewer" or "editor".
    
    Returns:
        Invitation status.
    """
    client = get_client()
    return await client.invite_collaborator(notebook_id, email, role)


# =============================================================================
# Auth Tools
# =============================================================================

@mcp.tool()
async def refresh_auth() -> dict[str, Any]:
    """Reload authentication tokens.
    
    Returns:
        Auth status and token information.
    """
    client = get_client()
    return await client.refresh_auth()


@mcp.tool()
async def server_info() -> dict[str, Any]:
    """Get server version and status.
    
    Returns:
        Server version, status, and available tools.
    """
    from . import __version__
    return {
        "name": "antigravity-notebooklm-mcp",
        "version": __version__,
        "description": "NotebookLM MCP Server for Antigravity IDE",
        "tools_count": len(mcp.get_tools()),
        "status": "running",
    }


def main():
    """Run the MCP server."""
    import sys
    
    # Parse arguments
    transport = "stdio"
    port = 8000
    debug = False
    
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--transport" and i + 1 < len(sys.argv):
            transport = sys.argv[i + 2]
        elif arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 2])
        elif arg == "--debug":
            debug = True
        elif arg in ("--help", "-h"):
            print("NotebookLM MCP Server")
            print()
            print("Usage: notebooklm-mcp [OPTIONS]")
            print()
            print("Options:")
            print("  --transport TYPE  Transport type: stdio, http, sse (default: stdio)")
            print("  --port PORT       Port for HTTP/SSE transport (default: 8000)")
            print("  --debug           Enable debug logging")
            print("  --help, -h        Show this help message")
            sys.exit(0)
    
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting NotebookLM MCP Server (transport={transport})")
    
    if transport == "stdio":
        mcp.run()
    elif transport == "http":
        mcp.run(transport="http", port=port)
    elif transport == "sse":
        mcp.run(transport="sse", port=port)
    else:
        logger.error(f"Unknown transport: {transport}")
        sys.exit(1)


if __name__ == "__main__":
    main()
