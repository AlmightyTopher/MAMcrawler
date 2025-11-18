# Local RAG System for MAM Documentation

A local-first Retrieval-Augmented Generation (RAG) system that transforms your downloaded MAM documentation into an interactive knowledge base using FAISS, SentenceTransformers, and Claude API.

## Features

- **Local-First**: All data stays on your machine, no cloud dependencies except Claude API
- **Automatic Updates**: File watcher keeps the knowledge base synchronized
- **VS Code Integration**: Seamlessly integrates with GitHub Copilot and Aider
- **Cost-Effective**: Uses Claude Haiku for minimal API costs
- **Structure-Aware**: Markdown header-based chunking for better retrieval

## Quick Start

1. **Setup Environment**:
   ```bash
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   ```

2. **Configure API Key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

3. **Index Your Documentation**:
   ```bash
   venv\Scripts\python ingest.py
   ```

4. **Ask Questions**:
   ```bash
   venv\Scripts\python cli.py "How do I convert AA files?"
   ```

## Architecture

### Components
- **database.py**: SQLite database operations for metadata storage
- **ingest.py**: Processes and indexes Markdown files
- **cli.py**: Query interface with Claude API integration
- **watcher.py**: Monitors file changes and updates index automatically

### Data Flow
1. **Ingestion**: Markdown files → Header-aware chunking → SentenceTransformers embeddings → FAISS index + SQLite metadata
2. **Retrieval**: Query → Embedding → FAISS search → SQLite lookup → Context assembly
3. **Generation**: Context + Query → Claude API → Answer

## VS Code Integration

Add to your `.vscode/settings.json`:

```json
{
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": ".ai/docs.md" }
  ],
  "aider.read": [
    ".ai/docs.md"
  ]
}
```

Then use:
```bash
venv\Scripts\python cli.py "your question" --context-only > .ai/docs.md
```

## File Structure

```
.
├── venv/                    # Virtual environment
├── guides_output/          # Your Markdown documentation
├── database.py            # SQLite operations
├── ingest.py              # Indexing pipeline
├── cli.py                 # Query interface
├── watcher.py             # File change monitor
├── metadata.sqlite        # Document metadata
├── index.faiss           # Vector index
├── requirements.txt       # Dependencies
└── .env                   # API keys
```

## Usage Examples

```bash
# Index documentation
venv\Scripts\python ingest.py

# Query with Claude
venv\Scripts\python cli.py "What torrent clients are recommended?"

# Get context only for VS Code
venv\Scripts\python cli.py "CD ripping guide" --context-only > .ai/docs.md

# Start file watcher
venv\Scripts\python watcher.py
```

## Requirements

- Python 3.8+
- Anthropic API key
- Markdown documentation in `guides_output/` directory

## Cost Estimate

- **Ingestion**: Free (local processing)
- **Queries**: ~$0.02 per query (4K context + 1K response with Haiku)
- **Storage**: Local files only

## Troubleshooting

**"index.faiss not found"**: Run `python ingest.py` first
**"API key error"**: Check your `.env` file
**Poor results**: Ensure Markdown files have proper headers for chunking