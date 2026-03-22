# Personal Finance and Subscription Tracker

This project is a Dockerized microservices application where users manually track recurring subscriptions and view analytics insights.

## Architecture

- `frontend` (React + Vite)
- `api1` Subscription Manager (FastAPI + PostgreSQL)
- `api2` Analytics API (FastAPI + PostgreSQL)
- `db1` dedicated database for subscriptions
- `db2` dedicated database for analytics data

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

## Repository Structure

- `frontend/`
- `api1/`
- `api2/`
- `.gitea/workflows/`
- `docs/`

## Quick Start

1. Copy environment file:

```bash
cp .env.example .env
```

2. Start all services:

```bash
docker compose up --build
```

3. Open services:

- Frontend: `http://localhost:5173`
- Subscription API Docs: `http://localhost:8001/docs`
- Analytics API Docs: `http://localhost:8002/docs`

## Verification Checklist

- Create/update/delete subscriptions from frontend.
- Confirm dashboard totals and category breakdown update.
- Restart stack and verify data still exists (named volumes).
- Prove isolation:
	- `api1 -> db1` allowed
	- `api2 -> db2` allowed
	- `api1 -> db2` forbidden
	- `api2 -> db1` forbidden
	- host has no published DB ports

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
