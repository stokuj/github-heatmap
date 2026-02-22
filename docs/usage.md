# Usage

## Requirements

- Python 3.12+
- `uv` installed
- Optional: Docker + Docker Compose
- GitHub personal access token for `/heatmap/me`

## Environment

Copy `.env.example` to `.env` and adjust values if needed.

```env
GITHUB_GRAPHQL_URL=https://api.github.com/graphql
```

## Local Run

```bash
uv sync --dev
uv run uvicorn backend.main:app --reload
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/health/live`

## Heatmap Endpoint

Request:

```bash
curl -H "Authorization: Bearer <GITHUB_TOKEN>" http://127.0.0.1:8000/heatmap/me
```

Response shape:

```json
{
  "username": "octocat",
  "total": 123,
  "weeks": [
    {
      "week_start": "2026-02-15",
      "days": [
        {
          "date": "2026-02-15",
          "weekday": 0,
          "count": 0,
          "level": 0
        }
      ]
    }
  ]
}
```

## Tests

```bash
uv run pytest -v
```

## Docker

```bash
docker compose up --build
```
