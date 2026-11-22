# Contracts

The agreed shapes of messages and API calls in VitalWatch. Code follows these files, not the other way round. Changing a contract needs a PR reviewed by both members.

| File | What it describes | Producer | Consumers |
| --- | --- | --- | --- |
| [device-reading.schema.json](device-reading.schema.json) | Message a device sends | Device / simulator | `ingestion` |
| [reading-event.schema.json](reading-event.schema.json) | Validated, deduplicated reading with tenant and patient attached | `ingestion` | `vitals`, `movement` |
| [alert.schema.json](alert.schema.json) | Alert raised by a domain or by fusion | `vitals`, `movement`, `alerts` (fusion) | `alerts`, `notifications` |
| [device-config.schema.json](device-config.schema.json) | Sampling config pushed to a device | `devices` | Device / simulator |
| [core-api.openapi.yaml](core-api.openapi.yaml) | REST API: auth, tenants, users, patients, devices | `core`, `devices` | admin portal, caregiver app |

Example messages that must stay valid live in [examples/](examples/).

## Rules

- JSON Schema draft 2020-12. Validators must have **format checking turned on** (`uuid`, `date-time`), because it is off by default.
- All times are UTC, RFC 3339 with an offset. Device time goes in `event_time`, server time in `received_at` / `created_at` (see [decision 0003](../decisions/0003-event-time-processing.md)).
- Devices never send `tenant_id` or `patient_id`. Ingestion attaches them from the device registry.
- API request bodies never carry `tenant_id`. The tenant comes from the verified JWT.
- Every message has `schema_version`. A breaking change bumps it, and consumers support the old and new version during the switch-over.
- Adding an optional field is non-breaking. Removing or renaming a field, or adding a required one, is breaking.

## Checks

Contract tests in the backend (from issue #3 onwards) will:

1. Validate every file in `examples/` against its schema.
2. Validate the events the backend produces against these schemas.
3. Compare FastAPI's generated OpenAPI spec with `core-api.openapi.yaml`.
