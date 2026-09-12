# QEVN INTELLIGENCE — LinkedIn Public-Signal Multi-Agent Engine

A production-minded LinkedIn public hiring signal intelligence platform built with **Python 3.11+, LangGraph, LangChain, Apify MCP, and Streamlit**.

## Core Workflow

```
Natural Language Input
        ↓
Intent Extraction Agent
        ↓
Query Expansion Agent (8-20 queries)
        ↓
Query Validation
        ↓
Apify LinkedIn Retrieval Service
        ↓
Deterministic Normalization
        ↓
Deterministic Deduplication
        ↓
Signal Detection Agent
        ↓
Qualification Agent & Scoring Engine
        ↓
Conditional Routing (Score Threshold >= 60)
 ├── LOW (< 60) ──> Opportunity Agent (Low) ──> END
 └── QUALIFIED (>= 60) ──> Enrichment Agent
                                 ↓
                           Decision Maker Agent
                                 ↓
                           Opportunity Agent ──> END
```

## Setup & Running

```bash
# Activate environment
source .venv/bin/activate

# Configure environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and APIFY_TOKEN

# Run Streamlit UI
streamlit run app/Home.py

# Run LangGraph Dev Server (in another terminal)
langgraph dev

# Run test suite
pytest -v
```
