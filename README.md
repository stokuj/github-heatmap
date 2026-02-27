# Github Heatmap

FastAPI service that receives requests through the `GET /heatmap/me` endpoint with an `Authorization: Bearer <GITHUB_TOKEN>` header, reads GitHub contribution activity for the authenticated user, and returns a heatmap-friendly JSON payload. 

It was created to integrate with my **Django** portfolio, but due to its **API-first**, **stateless** design it can cooperate with any backend framework. The service is containerized with **Docker**, and **GitHub Actions** workflows are included for automated testing and container image build checks.
The service was deployed on Google Cloud Run.

## Project Structure

```text
github-heatmap/
|- backend/
|  |- main.py                  # FastAPI app factory and app instance
|  |- settings.py              # Environment-based settings
|  |- api/
|  |  |- routes/
|  |  |  |- heatmap.py         # API routes/endpoints
|  |- services/
|  |  |- heatmap_service.py    # Heatmap business logic
|  |- clients/
|  |  |- github_client.py      # GitHub REST/GraphQL requests
|  |- core/
|  |  |- security.py           # Bearer token extraction/validation
|  |  |- observability.py      # Sentry initialization
|- tests/
|  |- test_main.py            # API tests
|  |- test_sentry.py          # Sentry setup tests
|- docs/
|  |- usage.md                # Setup and run guide
|- Dockerfile
|- docker-compose.yml
|- pyproject.toml
|- uv.lock
|- .env.example
```

## Showcase

### Raw API Response
The service accepts a GitHub Bearer token via the Authorization header and returns a structured JSON payload, ready to be consumed by any frontend or backend.
<img width="2574" height="1678" alt="ok" src="https://github.com/user-attachments/assets/9e61d6b2-3614-4169-968f-82e885660fc0" />

### Rendered Heatmap
The JSON output maps directly to a visual contribution heatmap. Each cell represents a single day; the intensity level drives the color, mimicking the familiar GitHub contribution graph.
<img width="2059" height="721" alt="Zrzut ekranu z 2026-02-24 14-34-02" src="https://github.com/user-attachments/assets/829d9392-b1ee-4e3f-a520-7f9dd45f6f96" />

### Observability

Despite its minimal footprint, the service ships with two layers of observability:
**Structured** logs streamed to Google Cloud Logging give a real-time view of incoming requests, response times, and lifecycle events.
<img width="2678" height="753" alt="Zrzut ekranu z 2026-02-24 14-39-39" src="https://github.com/user-attachments/assets/1c0a5a8e-80aa-4c9f-811f-acc87be702d9" />

**Sentry.io integration** captures and groups exceptions automatically.
<img width="2678" height="753" alt="image" src="https://github.com/user-attachments/assets/c5a84b63-ef2b-4953-8505-1a7ffbabf432" />


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
