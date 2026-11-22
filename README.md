# VitalWatch

Remote patient monitoring for care homes. Wearable readings come in, the backend checks vitals and movement, and staff see alerts on a live screen.

## Layout

- [admin-portal](admin-portal/README.md) is for the platform admin and the care home admin. They onboard care homes, register patients, staff, and devices, and set safe zones.
- [caregiver-app](caregiver-app/README.md) is for the caregiver on shift. They watch live vitals and location, and acknowledge or resolve alerts.
- [backend](backend/README.md) is the Python monolith both apps and the devices talk to.
- [docs](docs/README.md) holds setup notes and design records as they are written.

## Run it locally

Needs Docker with Compose v2.

```sh
cp .env.example .env          # then set POSTGRES_PASSWORD
docker compose up --build     # backend on http://localhost:8000, Postgres on localhost:5432
curl http://localhost:8000/health
```

`docker compose down` stops the stack and keeps the database. `docker compose down -v` also deletes the data. For working on the backend without Docker, see [backend/README.md](backend/README.md).

Branch rules are in [team-rules.json](team-rules.json).
