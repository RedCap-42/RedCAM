from __future__ import annotations

import sys

from redcam.app.bootstrap import run


def main() -> int:
    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
