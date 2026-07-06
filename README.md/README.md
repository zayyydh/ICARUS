<div align="center">

# ⚡ Project ICARUS

### *Intelligent Conversational Agent with Reasoning, Understanding & Synthesis*

**An AI Operating System — not just a chatbot.**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-1.5_Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-FF4F64?style=flat-square)](https://qdrant.tech)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active_Development-orange?style=flat-square)]()

---

*"Sometimes you gotta run before you can walk."* — Tony Stark

---

</div>

## What is ICARUS?

ICARUS is a personal AI operating system designed to understand, remember, reason, automate, and adapt — built for the way people actually live and work.

It is **not** a ChatGPT wrapper.
It is **not** a voice assistant with a few hardcoded commands.
It is a modular, extensible AI platform built on clean architecture — where adding a new capability (Spotify, WhatsApp, smart home) means writing one new plugin, not touching existing code.

### The difference

| Chatbot | ICARUS |
|---|---|
| Answers questions | Reasons, plans, and acts |
| Forgets you exist after the session | Remembers your preferences, history, and context |
| One language | Hindi, Marathi, Urdu, Hinglish, English — naturally |
| Fixed personality | Adapts — Developer mode at 2 PM, Night Owl at 11 PM |
| You talk to it | It talks back — in your own cloned voice |
| You install tools | Tools are plugins — drop in a folder, they're discovered |

---

## Core capabilities

- 🧠 **Reasoning brain** — Orchestrator + Intent Router + Planner. Routes simple commands without wasting an LLM call.
- 🎙️ **Voice interface** — Whisper large-v3 for speech recognition. ElevenLabs with your cloned voice for output.
- 🌍 **Indian language support** — Hindi, Marathi, Urdu, Hinglish, English. Understands code-switching and desi slang natively.
- 🎭 **Personality engine** — JSON-driven profiles. Developer, Bro, Mentor, Coach, Night Owl, Minimalist. Context-aware switching.
- 🔌 **Plugin tool system** — Every tool implements one interface. GitHub, music, browser automation, code execution, weather, filesystem.
- 📚 **RAG knowledge engine** — Indexes PDFs, DOCX, Markdown, websites, and Git repos. Powered by Qdrant vector database.
- 💾 **Three-layer memory** — Short-term (conversation), long-term (preferences), semantic (vector search).
- 🌐 **Web agent** — Playwright-powered browser automation for real online tasks.
- 🐙 **GitHub integration** — Create repos, commit files, push code — by voice.
- ⚡ **Event-driven architecture** — Modules communicate through an event bus, not direct calls.

---

## Architecture

```
User (voice or text)
        │
        ▼
┌───────────────────────────────────────┐
│           Voice Layer                 │
│  Whisper STT │ Wake Word │ ElevenLabs │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│            Agent Brain                │
│  Language Detector │ Intent Router    │
│  Orchestrator      │ Planner          │
└──────┬──────────────────┬─────────────┘
       │                  │
       ▼                  ▼
┌─────────────┐   ┌───────────────────┐
│  LLM Layer  │   │   Tool Engine     │
│Model Manager│   │ GitHub │ Music    │
│Gemini Flash │   │ Browser│ Code     │
│Claude (soon)│   │Weather │ Files    │
└─────────────┘   └───────────────────┘
       │                  │
       ▼                  ▼
┌───────────────────────────────────────┐
│         Personality + Context         │
│  Profiles │ Prompt Builder │ Engine   │
└───────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│           Memory System               │
│ Short-term │ Long-term │ Vector(Qdrant)│
└───────────────────────────────────────┘
```

Full architecture documentation: [`docs/architecture.md`](docs/architecture.md)

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.13 | Modern, async-native |
| API | FastAPI + Uvicorn | Fast, automatic OpenAPI docs |
| Validation | Pydantic v2 + pydantic-settings | Type-safe config and schemas |
| LLM | Gemini 1.5 Flash | Free tier, 1M context window |
| STT | Whisper large-v3 | Best multilingual accuracy |
| TTS | ElevenLabs multilingual v2 | Voice cloning, 32+ languages |
| Wake word | Porcupine | On-device, near-zero CPU |
| Embeddings | all-MiniLM-L6-v2 | Local, free, fast |
| Vector DB | Qdrant | Production-grade, filterable |
| Database | PostgreSQL | Reliable conversation storage |
| Cache | Redis | Fast session and tool caching |
| Browser | Playwright | Real web automation |
| Container | Docker + Compose | Identical local and production |
| CI | GitHub Actions | Lint, type check, test on every push |
| Testing | pytest + pytest-asyncio | Modular, isolated tests |
| Linting | Ruff + mypy | Fast, strict |

---

## Repository structure

```
ICARUS/
├── backend/
│   └── app/
│       ├── api/v1/          # FastAPI routes
│       ├── brain/           # Orchestrator, intent router, planner
│       ├── llm/             # Model Manager — swap LLMs here
│       ├── voice/           # STT, TTS, wake word, language layer
│       │   └── language/    # Detector, normalizer, Indian slang map
│       ├── personality/     # Engine + JSON profiles
│       ├── context/         # Auto-switching context engine
│       ├── memory/          # Short-term, long-term, vector
│       ├── rag/             # Ingestion, retrieval, document loaders
│       ├── tools/           # Plugin system — each tool is a folder
│       │   ├── base.py      # BaseTool interface
│       │   ├── registry.py  # Auto-discovers all tools
│       │   ├── github/
│       │   ├── music/
│       │   ├── browser/
│       │   ├── code/
│       │   └── weather/
│       ├── config/          # Settings, logging, constants
│       ├── core/            # Exceptions, dependencies, security
│       ├── events/          # Event bus — decoupled communication
│       └── schemas/         # Pydantic request/response models
├── docs/                    # IDD + ADR design documents
├── tests/                   # Unit and integration tests
├── docker/                  # Dockerfiles
├── scripts/                 # Setup and utility scripts
└── docker-compose.yml       # Full stack — one command
```

---

## Design documents

ICARUS follows a documentation-first approach. Every major design decision is recorded.

### ICARUS Design Documents (IDD)
| Document | Description |
|---|---|
| [IDD-001](docs/IDD-001-voice-engine.md) | Voice Engine — STT, TTS, wake word, language layer |
| [IDD-002](docs/IDD-002-personality-engine.md) | Personality Engine — profiles, prompt builder, switching |
| [IDD-003](docs/IDD-003-tool-engine.md) | Tool Engine — plugin interface, registry, execution |
| [IDD-004](docs/IDD-004-rag-engine.md) | RAG Engine — ingestion, retrieval, document loaders |
| [IDD-005](docs/IDD-005-memory-system.md) | Memory System — three-layer architecture |

### Architecture Decision Records (ADR)
| Record | Decision |
|---|---|
| [ADR-001](docs/ADR-001-qdrant-over-chroma.md) | Why Qdrant over ChromaDB |
| [ADR-002](docs/ADR-002-fastapi-over-flask.md) | Why FastAPI over Flask |
| [ADR-003](docs/ADR-003-intent-router-before-llm.md) | Why intent routing before the LLM |

---

## Getting started

### Prerequisites
- Python 3.13+
- Docker + Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/zayyydh/ICARUS.git
cd ICARUS
git checkout develop
```

### 2. Set up environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Start the infrastructure

```bash
docker-compose up -d postgres qdrant redis
```

### 4. Install dependencies

```bash
pip install -r requirements/dev.txt
```

### 5. Run ICARUS

```bash
uvicorn backend.main:app --reload
```

Visit `http://localhost:8000/api/v1/health` — if you see `{"status": "online"}`, ICARUS is running.

---

## Development

### Branch strategy

```
main        ← always stable, production-ready
develop     ← integration branch, current development
feature/*   ← one branch per feature
```

### Adding a new tool

1. Create `backend/app/tools/your_tool/`
2. Create `tool.py` implementing `BaseTool`
3. Done — the registry auto-discovers it

No changes to the brain. No changes to the router. Just a new folder.

### Running tests

```bash
pytest tests/ -v --cov=backend/app
```

---

## Roadmap

### Phase 1 — Foundation (current)
- [x] Project structure and architecture
- [ ] Core config and settings system
- [ ] FastAPI backend skeleton
- [ ] Health endpoint and CI pipeline
- [ ] Docker Compose full stack

### Phase 2 — Brain
- [ ] LLM Manager (Gemini integration)
- [ ] Intent Router
- [ ] Orchestrator
- [ ] Personality engine
- [ ] Context engine

### Phase 3 — Voice
- [ ] Whisper STT (multilingual)
- [ ] ElevenLabs TTS (voice cloning)
- [ ] Wake word detection
- [ ] Indian language layer + slang normalizer

### Phase 4 — Tools
- [ ] GitHub tool
- [ ] Music tool (YouTube)
- [ ] Browser automation (Playwright)
- [ ] Code executor
- [ ] Weather tool

### Phase 5 — Memory + RAG
- [ ] Short-term conversation memory
- [ ] Long-term user memory
- [ ] Qdrant vector store
- [ ] RAG engine (PDF, DOCX, web)

### Phase 6 — Deploy
- [ ] React + TypeScript frontend
- [ ] Production Docker setup
- [ ] Railway / Render deployment

---

## Contributing

ICARUS is in active development. Contributions, ideas, and feedback are welcome.

Read [`docs/contributing.md`](docs/contributing.md) before submitting a PR.

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

Built with 🔥 by [Zayd](https://github.com/zayyydh)

*"The goal isn't to build a demo. It's to build a platform."*

</div>