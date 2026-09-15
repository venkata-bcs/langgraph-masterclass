# Installation
> Venkata Bhattaram (c) 2026

## Contents (Planned)
* Installing langgraph
* Installing langchain and provider SDKs
* Verifying the installation
* Choosing a Python version

## Overview
Every chapter in this tutorial runs against one shared [requirements.txt](../../requirements.txt)
at the repo root, rather than each lesson listing its own ad-hoc `pip install`.
Install it once, up front, and every later chapter — persistence, RAG,
streaming, deployment — already has what it needs.

It's grouped by what unlocks what:

* **Core** — `langgraph` and `langchain-core`. This alone is enough for
  everything through State Management and Control Flow.
* **Provider SDKs** — `langchain-groq`, `langchain-ollama`, and
  `langchain-openai` (the last one doubles as the client for OpenRouter,
  since OpenRouter speaks the OpenAI-compatible chat completions format).
  This tutorial standardizes on Groq, Ollama Cloud, and OpenRouter because
  those are the providers this repo already has keys for — see
  [Environment Setup](./environment_setup.md) — rather
  than requiring separate OpenAI or Anthropic accounts.
* **Persistence** — `langgraph-checkpoint-sqlite` + `aiosqlite`. Covered
  starting in [Checkpointers](../../to-review/persistence-and-memory/checkpointers/checkpointers.md).
* **RAG, streaming, testing, deployment** — installed up front too, so
  Retrieval Augmented Generation, Streaming to a Frontend, and Deployment
  don't ask you to stop and install something new mid-chapter.

Choose **Python 3.11 or 3.12**. LangGraph itself supports 3.10+, but several
packages later in the course (`faiss-cpu`, `psycopg`) publish prebuilt
wheels for 3.11/3.12 well before they do for the newest interpreter release
each year — using the newest Python the day it ships is the most common
reason an install fails on this course. (The `ml-automation-genai-agents-agenticloop`
demo project elsewhere in this repo happens to run on a newer interpreter;
that's a narrower dependency set with no vector-store or Postgres driver
wheels to worry about.)

## Code Example
```powershell
# 1. Create and activate a virtual environment (Windows/PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install everything the course needs, in one shot
pip install -r requirements.txt
```

```bash
# 1. Create and activate a virtual environment (macOS/Linux)
python3 -m venv .venv
source .venv/bin/activate

# 2. Install everything the course needs, in one shot
pip install -r requirements.txt
```

Run the Python code located here
[Veryfy Installation Code](..\code\verify_installation.py)
```bash
python verify_installation.py
```

## Conclusion
One `requirements.txt`, installed once, covers this entire tutorial —
core LangGraph, the three LLM providers we standardize on, the SQLite
checkpointer we start persistence with, and everything RAG/streaming/testing/
deployment need later. Run the verification script above; if it prints
"Installation verified," you're set up correctly and ready for
[Environment Setup](./environment_setup.md), where API
keys get wired in.
