# 0001: Start as a modular monolith

- Status: proposed
- Date: 2026-11-22
- Deciders: Abdullah, Hanan

## Context

The proposal describes seven services: device registry, movement engine, Core API, ingestion, vitals engine, notification and escalation, and alert fusion. Building and running seven deployables from week 1 means seven Dockerfiles, Helm charts, CI jobs and network paths before any domain logic works. For a two-person team on a 16-week timeline, that cost lands early, when the domain boundaries are still uncertain.

## Decision

The initial version is one Python backend (FastAPI) in `backend/`, split internally into modules that follow the planned service boundaries:

| Module          | Future service                   | Owner    |
| --------------- | -------------------------------- | -------- |
| `core`          | Core API (auth, tenants, staff)  | Abdullah |
| `devices`       | Device registry and provisioning | Abdullah |
| `movement`      | Movement engine + fall model     | Abdullah |
| `ingestion`     | Ingestion service                | Hanan    |
| `vitals`        | Vitals engine + anomaly model    | Hanan    |
| `notifications` | Notification and escalation      | Hanan    |
| `alerts`        | Alert fusion                     | Both     |

Rules that keep a later split cheap:

- Modules talk to each other only through a small public interface (functions or events), not by importing each other's internals or querying each other's tables.
- Events between modules use the schemas in `docs/contracts/`, the same ones that will go over Kafka later.
- Each module has its own tests, so ownership stays visible.

## Consequences

- One image, one Compose service, one CI job to start with, so the pipeline is deployable early.
- Ownership ("you build it, you run it") is per module instead of per service until a split happens.
- We must enforce module boundaries in review (and possibly with an import-linter later), because a monolith makes shortcuts easy.
- A module is split out into its own service when there is a concrete reason: different scaling needs (ingestion), a separate deploy cadence (ML models), or failure isolation. Each split gets its own decision record.

## Alternatives considered

- **Seven services from day one:** matches the proposal diagram, but front-loads platform work and makes contract changes expensive while the contracts are still moving.
- **Unstructured monolith:** fastest at first, but would make the later split and per-member ownership hard to show.
