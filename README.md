# AppMedica

A healthcare practice management platform built to make everyday administration simpler for independent professionals and small clinics in Argentina.

The product brings patient records, appointments, health insurance workflows, payments, and reporting into one place. This repository is a portfolio project that demonstrates end-to-end product development across the interface, API, and database.

## Product areas

- Patient records, including spreadsheet import
- Appointment scheduling and administrative closeout
- Health insurance follow-up and claims tracking
- Payments, monthly reports, and data export
- Team access with authentication and role-based permissions

## Technology

- **Frontend:** React and TypeScript
- **Backend:** Python and FastAPI
- **Data:** PostgreSQL
- **Local development:** Docker Compose
- **Quality:** automated core-flow checks

## Run locally

Requirements: Docker Desktop.

```bash
cp .env.example .env
# Set local values in .env; never commit credentials or production secrets.
docker compose up --build
```

Open the frontend at `http://localhost:5173`. The API documentation is available at `http://localhost:8000/docs`.

To create a local account, use the registration page. Demo credentials and production access details are intentionally not published in this README.

Run the core-flow check with:

```bash
docker compose exec backend python scripts/test_core_flow.py
```

## Project focus

AppMedica was shaped around real administrative workflows: reduce repetitive steps, keep information organized, and make the status of appointments, payments, and insurance follow-up easier to understand.

