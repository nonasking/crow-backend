# crow-backend

Django REST Framework backend for tracking card payment expenses. Receives card payment SMS notifications via webhook, parses them, and syncs with Notion databases.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6 + Django REST Framework |
| Database | PostgreSQL (psycopg3) |
| Auth | JWT via `djangorestframework-simplejwt` |
| API Docs | drf-spectacular (Swagger / ReDoc) |
| Filtering | django-filter |
| Testing | pytest + pytest-django |
| Package Manager | Poetry |
| Deployment | Gunicorn + Render |

---

## Setup

### Prerequisites

- Python 3.13+
- PostgreSQL
- [Poetry](https://python-poetry.org/docs/#installation)

### 1. Install dependencies

```bash
poetry install
```

### 2. Configure environment

Create `.env.local` in the project root:

```env
SECRET_KEY=your-secret-key
DEBUG=True

DATABASE_URL=postgres://user:password@localhost:5432/crow

NOTION_TOKEN=your-notion-integration-token
NOTION_EXPENSE_DATABASE_ID=your-expense-db-id
NOTION_BUDGET_DATABASE_ID=your-budget-db-id
NOTION_VERSION=2022-06-28
```

> The app reads `.env.{DJANGO_ENV}` where `DJANGO_ENV` defaults to `local`.
> For production, set `DJANGO_ENV=production` and create `.env.production`.

### 3. Apply migrations

```bash
poetry run python manage.py migrate
```

### 4. Create a superuser

```bash
poetry run python manage.py createsuperuser
```

### 5. Run the development server

```bash
poetry run python manage.py runserver
```

---

## API Reference

Interactive docs are available at `/api/docs/` (Swagger UI) and `/api/redoc/` (ReDoc) once the server is running.

### Authentication

All endpoints require `Authorization: Bearer <access_token>` unless noted otherwise.

Tokens are issued on login: access token lifetime is **24 hours**, refresh token is **7 days**.

---

### Auth

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login/` | None | Obtain JWT token pair |
| `POST` | `/auth/logout/` | Required | Invalidate refresh token |
| `GET` | `/auth/me/` | Required | Get current user info |

**Login request:**
```json
{ "username": "admin", "password": "password123" }
```

**Login response:**
```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>",
  "user": { "id": 1, "username": "admin" }
}
```

---

### Expenses

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/expenses/expenses/` | List expenses (paginated, filterable) |
| `POST` | `/expenses/expenses/` | Create an expense |
| `GET` | `/expenses/expenses/{id}/` | Retrieve an expense |
| `PUT` | `/expenses/expenses/{id}/` | Replace an expense |
| `PATCH` | `/expenses/expenses/{id}/` | Partially update an expense |
| `DELETE` | `/expenses/expenses/{id}/` | Delete an expense |
| `GET` | `/expenses/expenses/options/` | List available categories, subcategories, and payment methods |
| `GET` | `/expenses/expenses/summary/` | Aggregated expense summary |
| `POST` | `/expenses/expenses/migrate-expenses-from-notion/` | Import expenses from Notion |

**Expense fields:** `spent_at`, `category`, `sub_category`, `item`, `payment_method`, `amount`, `memo`

**Filters:** `spent_at`, `category`, `sub_category`, `payment_method`

**Ordering:** `spent_at`, `amount`, `category`, `sub_category`, `payment_method`

---

### Budget

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/expenses/budget/` | List budgets (paginated, filterable) |
| `POST` | `/expenses/budget/` | Create a budget |
| `GET` | `/expenses/budget/{id}/` | Retrieve a budget |
| `PUT` | `/expenses/budget/{id}/` | Replace a budget |
| `PATCH` | `/expenses/budget/{id}/` | Partially update a budget |
| `DELETE` | `/expenses/budget/{id}/` | Delete a budget |
| `POST` | `/expenses/budget/migrate-budget-from-notion/` | Import budgets from Notion |

**Budget fields:** `year`, `month`, `category`, `sub_category`, `amount`, `memo`

---

### SMS Receiver

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/receivers/webhook/` | None | Receive card payment SMS and sync to Notion |

Supports **Shinhan** and **Woori** card SMS formats. The service parses the raw SMS text into structured data (`amount`, `item`, `payment_method`, `spent_at`) and writes to Notion.

**Request:**
```json
{ "message": "[Web발신]\n신한카드(1234)승인 2,400원 04/20 14:32 세븐일레븐" }
```

---

### System

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health/` | None | Health check |
| `GET` | `/api/docs/` | None | Swagger UI |
| `GET` | `/api/redoc/` | None | ReDoc |
| `GET` | `/api/schema/` | None | OpenAPI schema (YAML) |

---

## Testing

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run a specific app
poetry run pytest expenses/

# Re-run only failed tests
poetry run pytest --lf
```

Tests use `pytest-django` with a dedicated test database. Key fixtures are defined in `conftest.py`:

- `user` — creates a test `User`
- `auth_client` — returns a JWT-authenticated `APIClient`

---

## Project Structure

```
crow-backend/
├── config/            # Django settings, root URLs, WSGI/ASGI
├── authentication/    # Login, logout, current user endpoints
├── expenses/          # Expense and Budget models, views, serializers, services
├── receivers/         # SMS webhook receiver and parsing service
├── analytics/         # Analytics app (in development)
├── conftest.py        # Shared pytest fixtures
└── pyproject.toml     # Dependencies and tooling config
```
