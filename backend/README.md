# Backend

One Python monolith for VitalWatch, split into modules that follow the planned service boundaries (see [decision 0001](../docs/decisions/0001-modular-monolith.md)). [admin-portal](../admin-portal/README.md), [caregiver-app](../caregiver-app/README.md) and the devices all talk to this service.

## Layout

```text
backend/
├── pyproject.toml        # dependencies, ruff and pytest config
├── uv.lock               # exact versions, committed
├── src/vitalwatch/
│   ├── main.py           # FastAPI app factory, /health
│   ├── config.py         # settings from VITALWATCH_* environment variables
│   ├── core/             # login, roles, tenants, staff, patients    (Abdullah)
│   ├── devices/          # device registry and credentials           (Abdullah)
│   ├── movement/         # fall detection, safe zones                (Abdullah)
│   ├── ingestion/        # validate, dedupe, publish readings        (Hanan)
│   ├── vitals/           # baselines, anomaly detection              (Hanan)
│   ├── notifications/    # routing and escalation                    (Hanan)
│   └── alerts/           # alert fusion                              (both)
└── tests/
    ├── contract/         # checks against ../docs/contracts
    └── ...
```

Modules talk to each other only through their public interface or events, never by importing another module's internals or reading its tables.

## Setup

Needs [uv](https://docs.astral.sh/uv/). uv installs Python 3.12 (pinned in `.python-version`) and creates `.venv` by itself; there is no need to create or activate a virtual environment.

```sh
cd backend
uv sync                 # install dependencies into .venv
```

## Everyday commands

```sh
uv run uvicorn vitalwatch.main:app --reload   # run the API on http://localhost:8000
uv run pytest                                 # all tests
uv run pytest -m contract                     # contract tests only
uv run ruff check .                           # lint
uv run ruff format .                          # format
uv add <package>                              # add a dependency
uv add --dev <package>                        # add a dev-only dependency
```

API docs are at <http://localhost:8000/docs>.

## Configuration

| Variable | Default | Values |
| --- | --- | --- |
| `VITALWATCH_ENVIRONMENT` | `local` | `local`, `test`, `staging`, `production` |
| `VITALWATCH_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Contracts

Endpoints must be in [core-api.openapi.yaml](../docs/contracts/core-api.openapi.yaml) before they are implemented: a contract test fails if the app exposes an operation the contract doesn't have.
