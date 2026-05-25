# OKX Opportunity Scanner

Real-time crypto market opportunity detection on OKX — Phase 1 (Scanner Only).

## Quick start

```bash
cp .env.example .env
pip install -e ".[dev]"
docker compose up -d
alembic upgrade head
pytest tests/ -v
```

## Stack

Python 3.14 · FastAPI · PostgreSQL · Redis · SQLAlchemy · Pydantic v2 · Structlog
