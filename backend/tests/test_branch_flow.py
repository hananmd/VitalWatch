"""The CI branch check matches team-rules.json: feature branch, then dev, then main."""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "check_branch_flow.py"
_spec = importlib.util.spec_from_file_location("check_branch_flow", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
_flow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_flow)


def test_dev_may_merge_into_main() -> None:
    assert _flow.check("main", "dev") is None


def test_a_feature_branch_may_merge_into_dev() -> None:
    assert _flow.check("dev", "feat/8-tenant-isolation") is None


def test_a_feature_branch_may_not_merge_into_main() -> None:
    message = _flow.check("main", "feat/8-tenant-isolation")
    assert message is not None
    assert "dev" in message


def test_main_may_not_merge_into_dev() -> None:
    assert _flow.check("dev", "main") is not None


def test_a_push_is_not_a_pull_request() -> None:
    assert _flow.check("", "") is None
