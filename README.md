# Donna - Agentic AI Executive Assistant

Donna is an advanced, autonomous "Agentic AI" executive assistant built for a Kaggle Capstone Project. It is designed to interpret natural language commands, route them to specialized domain sub-agents, and autonomously manage a user's digital workspace, specifically targeting Google Workspace (Gmail and Calendar).

## Project Overview

Modern knowledge workers navigate a fragmented digital ecosystem. Donna solves this by providing a unified, intelligent interface that bridges standard chat capabilities with secure, state-mutating actions across external APIs. 

### Key Features
* **Intent Orchestration:** Utilizes an LLM-powered router to accurately classify user queries into distinct functional domains (Communications, Scheduling, Ledger, Logistics, General).
* **Model Context Protocol (MCP):** Implements the MCP standard to decouple the reasoning engine from raw API schemas, enabling seamless tool discovery and execution.
* **Resilient Architecture (Local MVP):** Capable of switching from live OAuth-backed network requests to local mock data stacks instantly. This ensures the agentic logic remains testable and fully functional even when encountering enterprise API rate limits or quota exhaustions.
* **Automated Parameter Extraction:** Parses unstructured natural language (e.g., "tomorrow at 4 PM") into rigid, ISO-compliant JSON payloads for external tool consumption.

## Repository Structure
* `/donna-workspace/backend/` - Contains the FastAPI backend, Orchestrator (`orchestrator.py`), and MCP client logic (`mcp_clients.py`).
* `/donna-workspace/frontend/` - Next.js frontend providing the chat interface, notifications, and calendar widget.
* `/donna-workspace/kaggle_capstone_mvp.py` - The 100% self-contained Minimal Viable Product script that runs the agentic pipeline against local mock databases (built for rigorous capstone evaluation).
* `kaggle_capstone_writeup.md` - The comprehensive academic report detailing the system architecture, constraints, and transition to the local MVP.

## Quick Start (Kaggle MVP Evaluation)

For the Kaggle capstone review, a self-contained MVP has been provided that bypasses live Google OAuth limits. It runs entirely on local mock data and requires zero external API keys.

```bash
# Navigate to the workspace
cd donna-workspace

# Run the MVP script
python3 kaggle_capstone_mvp.py
```

## Running the Live Server (Development)

To run the full backend server with the live Google Workspace MCP integration:

1. Ensure your `credentials.json` is properly configured in `~/.google-workspace-mcp/`.
2. Activate the virtual environment:
   ```bash
   cd donna-workspace
   source .venv/bin/activate
   ```
3. Start the Uvicorn server:
   ```bash
   PYTHONPATH=. python -m uvicorn backend.app.main:app --reload
   ```

## Architecture Details
For a deeper dive into how Donna utilizes the Model Context Protocol (MCP) and dynamic prompt engineering to mitigate hallucination and enforce schema validation, please refer to the `kaggle_capstone_writeup.md` report.
