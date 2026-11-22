"""Event schemas in docs/contracts must be valid, and their examples must match them."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

pytestmark = pytest.mark.contract

EVENT_SCHEMAS = [
    "device-reading",
    "reading-event",
    "alert",
    "device-config",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schemas(contracts_dir: Path) -> dict[str, dict]:
    return {name: _load(contracts_dir / f"{name}.schema.json") for name in EVENT_SCHEMAS}


@pytest.fixture(scope="module")
def registry(schemas: dict[str, dict]) -> Registry:
    return Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )


def _validator(schema: dict, registry: Registry) -> Draft202012Validator:
    # Format checking is off by default in jsonschema; the contracts require it.
    return Draft202012Validator(
        schema, registry=registry, format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def test_every_schema_file_is_listed(contracts_dir: Path) -> None:
    on_disk = {p.name.removesuffix(".schema.json") for p in contracts_dir.glob("*.schema.json")}

    assert on_disk == set(EVENT_SCHEMAS)


@pytest.mark.parametrize("name", EVENT_SCHEMAS)
def test_schema_is_valid_json_schema(name: str, schemas: dict[str, dict]) -> None:
    Draft202012Validator.check_schema(schemas[name])


@pytest.mark.parametrize("name", EVENT_SCHEMAS)
def test_example_matches_schema(
    name: str, contracts_dir: Path, schemas: dict[str, dict], registry: Registry
) -> None:
    example = _load(contracts_dir / "examples" / f"{name}.json")

    errors = [e.message for e in _validator(schemas[name], registry).iter_errors(example)]

    assert errors == []


@pytest.mark.parametrize(
    ("label", "change"),
    [
        ("device sends tenant_id", {"tenant_id": "0b6a3f8e-2c1d-4e5f-8a9b-1c2d3e4f5a6b"}),
        ("device sends patient_id", {"patient_id": "a3d9e1f2-7b4c-4d8e-9f1a-2b3c4d5e6f70"}),
        ("no metrics", {"metrics": {}}),
        ("message_id is not a uuid", {"message_id": "abc"}),
        ("event_time is not a date-time", {"event_time": "yesterday"}),
        ("impossible heart rate", {"metrics": {"heart_rate_bpm": 500}}),
        (
            "accelerometer sample with two axes",
            {"metrics": {"accelerometer": {"sample_rate_hz": 50, "samples_g": [[0.0, 1.0]]}}},
        ),
    ],
)
def test_device_reading_rejects(
    label: str, change: dict, contracts_dir: Path, schemas: dict[str, dict], registry: Registry
) -> None:
    example = _load(contracts_dir / "examples" / "device-reading.json")

    assert not _validator(schemas["device-reading"], registry).is_valid(example | change), label


@pytest.mark.parametrize(
    ("label", "change"),
    [
        ("no reasons", {"reasons": []}),
        ("unknown severity", {"severity": "urgent"}),
        ("score above 1", {"score": 1.5}),
    ],
)
def test_alert_rejects(
    label: str, change: dict, contracts_dir: Path, schemas: dict[str, dict], registry: Registry
) -> None:
    example = _load(contracts_dir / "examples" / "alert.json")

    assert not _validator(schemas["alert"], registry).is_valid(example | change), label


def test_alert_requires_late_flag(
    contracts_dir: Path, schemas: dict[str, dict], registry: Registry
) -> None:
    example = _load(contracts_dir / "examples" / "alert.json")
    del example["late"]

    assert not _validator(schemas["alert"], registry).is_valid(example)
