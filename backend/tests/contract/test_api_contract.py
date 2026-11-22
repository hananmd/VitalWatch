"""The running API must stay inside the agreed contract in docs/contracts/core-api.openapi.yaml."""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

pytestmark = pytest.mark.contract

CONTRACT_URI = "urn:vitalwatch:core-api"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


@pytest.fixture(scope="module")
def contract(contracts_dir: Path) -> dict:
    return yaml.safe_load((contracts_dir / "core-api.openapi.yaml").read_text(encoding="utf-8"))


def _operations(spec: dict) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, item in spec.get("paths", {}).items()
        for method in item
        if method in HTTP_METHODS
    }


def _response_validator(contract: dict, path: str, method: str, status: int):
    """Validator for a response body schema in the contract, with its $refs resolvable."""
    pointer_path = path.replace("~", "~0").replace("/", "~1")
    pointer = f"#/paths/{pointer_path}/{method}/responses/{status}/content/application~1json/schema"
    # OpenAPI 3.1 schemas are JSON Schema 2020-12, but the document has no "$schema" key.
    resource = Resource.from_contents(contract, default_specification=DRAFT202012)
    registry = Registry().with_resource(CONTRACT_URI, resource)
    return Draft202012Validator(
        {"$ref": f"{CONTRACT_URI}{pointer}"},
        registry=registry,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def test_contract_is_openapi_3_1(contract: dict) -> None:
    assert contract["openapi"].startswith("3.1")


def test_every_implemented_operation_is_in_the_contract(client: TestClient, contract: dict) -> None:
    implemented = _operations(client.get("/openapi.json").json())

    not_in_contract = implemented - _operations(contract)

    assert not_in_contract == set(), "add these to core-api.openapi.yaml first"


def test_health_response_matches_contract(client: TestClient, contract: dict) -> None:
    body = client.get("/health").json()

    errors = [
        e.message for e in _response_validator(contract, "/health", "get", 200).iter_errors(body)
    ]

    assert errors == []
