# 0002: Plain PostgreSQL first, defer TimescaleDB, Mosquitto and Redpanda

- Status: proposed
- Date: 2026-11-22
- Deciders: Abdullah, Hanan

## Context

The target stack has TimescaleDB for time-series readings, Mosquitto for device MQTT and Redpanda as a Kafka-compatible broker between services. The first milestone (weeks 1 to 4) covers the backend skeleton, CI, the data model, auth, tenant isolation and the device registry. None of that work stores high-volume readings or exchanges messages between services.

## Decision

The initial version uses **plain PostgreSQL** only. Mosquitto, Redpanda and TimescaleDB are added when the ingestion work needs them, each in its own issue:

- **Mosquitto:** when the ingestion module starts receiving device messages.
- **Redpanda:** when readings need to flow from ingestion to the vitals and movement modules.
- **TimescaleDB:** when the readings table is added. TimescaleDB is a PostgreSQL extension, so the move means changing the image and turning the readings table into a hypertable in a migration, not switching databases.

## Consequences

- Docker Compose and CI start small (backend and PostgreSQL), which keeps local runs light and CI fast.
- Migrations must stay plain PostgreSQL-compatible so the move to the TimescaleDB image is a drop-in change.
- The event contracts are written now, so adding the brokers later doesn't change the event shapes.

## Alternatives considered

- **Full stack from day one:** more containers to run and debug before any of them is used.
- **SQLite for development:** faster to start, but it differs from PostgreSQL in types and constraints, and the tenant isolation tests need to run against the real database.
