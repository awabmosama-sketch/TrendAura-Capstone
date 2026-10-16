# TrendAura API

TrendAura is an async FastAPI e-commerce backend for a unisex catalog, custom bank-transfer/COD payments, and LangGraph automation.

## GitHub setup

Do not commit `.env`. Copy `.env.example` to `.env`, replace every placeholder with local or deployment values, and rotate any credentials that have previously been exposed. The repository includes a GitHub Actions workflow that runs the test suite on pushes and pull requests.

## Run locally

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "sqlite+aiosqlite:///./trendaura.db"
uvicorn app.main:app --reload
```

API documentation is available at `http://127.0.0.1:8000/docs`.

## Current API

- `GET /api/v1/health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/products`
- `GET /api/v1/products/categories`
- `GET /api/v1/cart`
- `POST /api/v1/cart/items`
- `POST /api/v1/orders/checkout` with `bank_transfer` or `cod`
- `GET /api/v1/orders`
- `POST /api/v1/orders/{id}/pay`
- `GET /api/v1/agents/recommendations?q=...`
- `POST /api/v1/agents/onboarding`
- Admin dashboard APIs under `/api/v1/admin` for metrics, orders, products, refunds, pricing, and fraud review

## Agent and admin pages

- Admin dashboard: `http://127.0.0.1:8000/admin-dashboard.html`
- Refund review: `http://127.0.0.1:8000/admin-refunds.html`
- Customer payments: `http://127.0.0.1:8000/payments.html`

The local agent implementations are deterministic and testable without paid API keys. Configure `GROQ_API_KEY`, `GOOGLE_API_KEY`, and `TAVILY_API_KEY` when replacing the local recommendation, pricing, and onboarding heuristics with provider-backed implementations.

The application creates tables for local development. Production deployments should run Alembic migrations before starting the service.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Security

Copy `.env.example` to `.env`, use a new random `SECRET_KEY`, and never commit credentials. Rotate any credentials that have been shared outside the secret manager.
