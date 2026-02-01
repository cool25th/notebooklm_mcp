---
description: Use this skill when the user asks to research information from NotebookLM, needs context from uploaded documents, or wants to leverage RAG (Retrieval-Augmented Generation) for coding tasks.
---

# NotebookLM Integration Skill

This skill enables AI agents to access Google NotebookLM's powerful RAG capabilities for research-driven coding support.

## When to Activate

Activate this skill when the user:
- Asks to "find in NotebookLM" or "search my notebooks"
- Needs context from previously uploaded documents
- Requests research-based code generation
- Mentions "notebook sources" or "document references"
- Wants to create or manage NotebookLM notebooks programmatically

## Available Tools

### Notebook Management
- `notebook_list` - List all notebooks
- `notebook_create` - Create a new notebook
- `notebook_get` - Get notebook details
- `notebook_describe` - Get AI summary of notebook
- `notebook_rename` - Rename a notebook
- `notebook_delete` - Delete a notebook (requires confirm=True)

### Source Management
- `source_add` - Add URL, text, file, or Drive source
- `source_list` - List sources with metadata
- `source_delete` - Remove a source
- `source_describe` - Get AI keywords and summary
- `source_get_content` - Get raw text content

### Querying (Core for RAG)
- `notebook_query` - Ask questions about sources (PRIMARY TOOL)
- `chat_configure` - Set conversation style and length

### Content Generation
- `studio_create` - Generate audio, video, reports, quizzes, etc.
- `studio_status` - Check generation progress
- `download_artifact` - Download generated content

### Research
- `research_start` - Start web/Drive research
- `research_status` - Check research progress
- `research_import` - Import discovered sources

### Sharing
- `notebook_share_status` - Get sharing settings
- `notebook_share_public` - Enable/disable public link
- `notebook_share_invite` - Invite collaborators

## Typical Workflows

### 1. Research → Code Flow
```
1. notebook_list → Find relevant notebook
2. notebook_query("How does the authentication module work?")
3. Use response to inform code generation
```

### 2. Add Documentation → Query
```
1. source_add(notebook_id, source_type="url", url="https://docs.example.com")
2. Wait for processing
3. notebook_query("Summarize the API endpoints")
```

### 3. Deep Research
```
1. research_start(notebook_id, query="enterprise authentication patterns")
2. research_status → Check progress
3. research_import → Add relevant sources
4. notebook_query → Query combined sources
```

## Best Practices

1. **Always list notebooks first** - Identify relevant notebooks before querying
2. **Be specific in queries** - "How does X handle Y?" not "Tell me about X"
3. **Check source freshness** - Use `source_list` to verify sources are current
4. **Combine sources** - Add multiple related documents for comprehensive context

## Example Agent Interaction

**User:** "Find information about our API rate limiting in NotebookLM"

**Agent workflow:**
1. `notebook_list()` → Find "API Documentation" notebook
2. `notebook_query(notebook_id, "What are the rate limiting rules?")` → Get answer with citations
3. Return response with relevant code examples

## Troubleshooting

### Authentication Issues
If tools return auth errors, user should run:
```bash
notebooklm-mcp-auth
```

### Rate Limits
NotebookLM free tier has ~50 queries/day. Batch queries when possible.

### Source Processing
After adding sources, wait for `status: ready` before querying.
