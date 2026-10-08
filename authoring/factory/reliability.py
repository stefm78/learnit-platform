#!/usr/bin/env python3
"""Closed V1/V6 FactoryRun dispatcher; V1 semantics remain byte-identical internally."""
from __future__ import annotations

import sys
from typing import Any

from authoring.factory import _reliability_v1 as _v1

for _name in dir(_v1):
    if not _name.startswith("__") and _name != "main":
        globals()[_name] = getattr(_v1, _name)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "v6-run":
        from authoring.factory import reliability_v6
        return reliability_v6.main(["run", *args[1:]])
    if args and args[0] == "v6-verify-run":
        from authoring.factory import reliability_v6
        return reliability_v6.main(["verify-run", *args[1:]])
    return _v1.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
