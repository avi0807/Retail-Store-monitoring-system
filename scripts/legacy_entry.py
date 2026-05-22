"""Legacy entry point preserved for compatibility.

The original project shipped ``retail_monitor.py`` at the repo root.
That file has been removed because it collided with the
``retail_monitor`` package under ``src/``. If you have old shell
history that runs ``python retail_monitor.py``, point it at this
script instead, or just use the ``retail-monitor`` console script
installed by ``pip install -e .``.
"""

from __future__ import annotations

import sys
import warnings


def main() -> int:
    warnings.warn(
        "scripts/legacy_entry.py is deprecated; use the `retail-monitor` CLI.",
        DeprecationWarning,
        stacklevel=2,
    )
    from retail_monitor.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
