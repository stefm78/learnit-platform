#!/usr/bin/env python3
"""Closed V1/V6 qualified-release dispatcher; V1 semantics remain byte-identical internally."""
from __future__ import annotations

import sys

from authoring.factory import _release_set_v1 as _v1

for _name in dir(_v1):
    if not _name.startswith("__") and _name != "main":
        globals()[_name] = getattr(_v1, _name)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "v6-build":
        from authoring.factory import release_set_v6
        return release_set_v6.main(["build", *args[1:]])
    if args and args[0] == "v6-verify":
        from authoring.factory import release_set_v6
        return release_set_v6.main(["verify", *args[1:]])
    return _v1.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
