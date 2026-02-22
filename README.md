# github-heatmap

FastAPI service that receives requests through the `GET /heatmap/me` endpoint with an `Authorization: Bearer <GITHUB_TOKEN>` header, reads GitHub contribution activity for the authenticated user, and returns a heatmap-friendly JSON payload. 

It was created to integrate with my Django portfolio, but due to its API-first, stateless design it can cooperate with any backend framework. The service is containerized (Docker), and GitHub Actions workflows are included for automated testing and container image build checks.

## Project Structure

```text
github-heatmap/
|- backend/
|  |- main.py          # FastAPI app and endpoints
|  |- github_api.py    # GitHub REST/GraphQL requests
|  |- settings.py      # Environment-based settings
|- tests/
|  |- test_main.py     # API tests
|- docs/
|  |- usage.md         # Setup and run guideic)
|- Dockerfile
|- docker-compose.yml
|- pyproject.toml
|- uv.lock
|- .env.example
```

## Usage

Docker:

```bash
docker compose up --build
```

Run tests:

```bash
uv run pytest -v
```

API endpoints:

- `GET /` - basic hello response
- `GET /health/live` - liveness probe
- `GET /heatmap/me` - authenticated heatmap payload (Bearer token required)

See `docs/usage.md` for full setup details.

## Solved Problems

- Converts GitHub contribution calendar into stable weekly heatmap JSON.
- Normalizes raw contribution counts into 5 visual levels (`0..4`).
- Handles missing/invalid bearer tokens with explicit `401` responses.
- Maps GitHub auth failures (`401/403`) to API-level auth errors.

## Roadmap

- Add persistent storage for sync history and caching.
- Add scheduled sync jobs for offline heatmap generation.
- Add metrics/observability (request timing, error rates).
- Add richer filtering options (date range, organization scope).

Detailed info: `docs/`.

## License

MIT License. See `LICENSE`.
