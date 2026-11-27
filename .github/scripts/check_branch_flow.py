"""Fail a pull request that skips feature branch, then dev, then main."""

import os
import sys


def check(base: str, head: str) -> str | None:
    """Return an error message, or None when this pull request follows the flow.

    An empty base means the event is not a pull request, so there is nothing to enforce.
    """
    if not base:
        return None
    if base == "main" and head != "dev":
        return f"Pull requests into main must come from dev (got {head or 'an empty head'})."
    if base == "dev" and head == "main":
        return "main is updated from dev, not the other way around."
    return None


def main() -> int:
    message = check(os.environ.get("BASE_REF", ""), os.environ.get("HEAD_REF", ""))
    if message:
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
