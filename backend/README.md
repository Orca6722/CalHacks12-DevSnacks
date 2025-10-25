# DevSnacksAI — uAgents + Groq + ChromaDB

"Your code’s mood orders your food." — An agentic RAG demo for hackathons (CalHacks 12.0-ready):

- **uAgents (Fetch.ai)** orchestrate micro-agents
- **Groq LLM** extracts mood signals & fun explanations
- **ChromaDB** stores menus & user prefs for retrieval/personalization
- **(Optional)** Delivery API stub (swap to DoorDash Drive sandbox)

## High-Level Flow
1. **CommitAgent** reads local git commit messages (last N).
2. **MoodAgent** (Groq) converts commits → mood JSON + NL query.
3. **RecoAgent** queries **ChromaDB** (`menus` + `prefs`) → top picks, writes `data/last_reco.json`.
4. **(Optional)** **OrderAgent** stubs (or calls real API) to place an order.
5. Minimal **HTTP gateway** (`/api/recommendations`) serves latest picks; `/api/feedback` updates prefs.

## Quick Start

### 0) Python Setup
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```