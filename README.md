# Personal Finance and Subscription Tracker

This project is a Dockerized microservices application where users manually track recurring subscriptions and view analytics insights.

## Architecture

- `frontend` (React + Vite)
- `api1` Subscription Manager (FastAPI + PostgreSQL)
- `api2` Analytics API (FastAPI + PostgreSQL)
- `db1` dedicated database for subscriptions
- `db2` dedicated database for analytics data

```mermaid
flowchart LR
    Browser[Browser / Frontend UI] --> Frontend[frontend]
    Frontend --> API1[api1 Subscription Manager]
    Frontend --> API2[api2 Analytics Service]
    API1 --> DB1[(db1 PostgreSQL)]
    API2 --> DB2[(db2 PostgreSQL)]
    API2 --> API1
```

## Technology Stack

- Frontend: React, Vite
- Backend APIs: FastAPI, SQLAlchemy, Pydantic
- Databases: PostgreSQL 16 Alpine
- Containerization: Docker, Docker Compose
- CI/CD and security: Gitea Actions, Trivy, Docker Hub

## Key Requirements Covered

- Manual subscription CRUD.
- Monthly/yearly totals, category breakdown, recommendations, upcoming renewals.
- Frontend hot reload via Docker bind mount.
- Two backend microservices with separate databases.
- Isolated Docker networks (`frontend_net`, `backend1_net`, `backend2_net`) to enforce access rules.
- Named volumes for database persistence.
- Non-root runtime users in all service Dockerfiles.
- Health checks for frontend and APIs.
- CI/CD workflow with Trivy scan and Docker Hub push.

## Environment

| Variable | Purpose | Default / Example |
| --- | --- | --- |
| `POSTGRES_USER` | PostgreSQL username for both databases | `study_user` |
| `POSTGRES_PASSWORD` | PostgreSQL password for both databases | `study_pass` |
| `POSTGRES_DB_TASKS` | Database name for API 1 | `subscriptions_db` |
| `POSTGRES_DB_RESOURCES` | Database name for API 2 | `analytics_db` |
| `API1_DB_URL` | SQLAlchemy connection string for API 1 | `postgresql://study_user:study_pass@db1:5432/subscriptions_db` |
| `API2_DB_URL` | SQLAlchemy connection string for API 2 | `postgresql://study_user:study_pass@db2:5432/analytics_db` |
| `VITE_API1_URL` | Browser-facing URL for API 1 | `http://localhost:8001` |
| `VITE_API2_URL` | Browser-facing URL for API 2 | `http://localhost:8002` |
| `DOCKERHUB_USERNAME` | Namespace for pushed images | `your-dockerhub-username` |

## Repository Structure

- `frontend/`
- `api1/`
- `api2/`
- `.gitea/workflows/`
- `docs/`

## Quick Start

1. Clone the repository:

```bash
git clone <your-gitea-repository-url>
cd team-03
```

2. Copy environment file:

```bash
cp .env.example .env
```

3. Start all services:

```bash
docker compose up --build
```

4. Open services:

- Frontend: `http://localhost:5173`
- Subscription API Docs: `http://localhost:8001/docs`
- Analytics API Docs: `http://localhost:8002/docs`

## Hot Reload

- The frontend source is bind mounted into the `frontend` container.
- Changes to files inside `frontend/src/` should appear in the browser after refresh without rebuilding the container.

## Verification Checklist

- Create, update, and delete subscriptions from frontend.
- Confirm dashboard totals and category breakdown update.
- Restart stack and verify data still exists (named volumes).
- Prove isolation:
	- `api1 -> db1` allowed
	- `api2 -> db2` allowed
	- `api1 -> db2` forbidden
	- `api2 -> db1` forbidden
	- host has no published DB ports

## Presentation Proof Commands

```bash
docker compose ps
docker compose exec api1 python -c "import socket; print(socket.gethostbyname('db1'))"
docker compose exec api2 python -c "import socket; print(socket.gethostbyname('db2'))"
docker compose exec api1 python -c "import socket; print(socket.gethostbyname('db2'))"
docker compose exec api2 python -c "import socket; print(socket.gethostbyname('db1'))"
docker volume ls
```

## Demo

### Frontend

![Frontend dashboard](docs/demo/frontend-dashboard.png)

### API 1 Docs

![API 1 Swagger docs](docs/demo/api1-docs.png)

### API 2 Docs

![API 2 Swagger docs](docs/demo/api2-docs.png)

## Bonus-Ready Extensions

- Add Traefik/Nginx reverse proxy in front of services.
- Add Redis queue for asynchronous analytics refresh.
- Add multi-stage Docker builds for smaller production images.
- Add replicas for one backend service as load-balancing demo.

## CI/CD Notes

The workflow in `.gitea/workflows/ci.yml`:

- Builds all service images.
- Runs Trivy and fails on `MEDIUM`, `HIGH`, or `CRITICAL` findings.
- Pushes versioned images to Docker Hub from `main` branch.

Set repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
