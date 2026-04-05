# RelationshipAI Monorepo

RelationshipAI is a sophisticated AI-driven platform for multi-modal relationship counseling and insights.

## Repository Structure

```
relationshipai/
├── mobile/                          # Flutter app
├── backend-django/                  # Auth, consent, users, memory, therapist portal
├── backend-fastapi/                 # LLM orchestration, safety, real-time sessions
├── shared/                          # Shared Pydantic schemas and constants
├── infra/                           # Infrastructure documentation (Railway, Supabase, Upstash)
├── docs/                            # ADRs and design documents
├── docker-compose.yml               # Local development environment
└── Makefile                         # Automation tasks
```

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- [Flutter SDK](https://docs.flutter.dev/get-started/install)
- [Python 3.12+](https://www.python.org/downloads/)

### Setup

1. Clone the repository.
2. Configure environment variables (refer to `.env.example` in each service).
3. Start the development environment:
   ```bash
   make dev
   ```

### Development Commands

- `make test`: Run all tests across platforms.
- `make migrate`: Apply Django migrations.
- `make lint`: Run all linters.
- `make clean`: Clean up build artifacts and containers.

## Infrastructure Decision (MVP Phase)

See [infra/README.md](infra/README.md) for details on the current infrastructure choices for the 20-user pilot.
