"""Quick RTSP connectivity smoke test (no analysis, just frame grab).

Usage:
    python scripts/smoke_rtsp.py "rtsp://user:pass@host/stream"
"""

from __future__ import annotations

import sys
import time

from retail_monitor.io import RTSPStream
from retail_monitor.logging_setup import configure_logging


def main(url: str, seconds: int = 10) -> int:
    log = configure_logging("INFO")
    with RTSPStream(url) as stream:
        deadline = time.time() + seconds
        last_id = -1
        frames = 0
        while time.time() < deadline:
            frame, fid = stream.read_with_id()
            if frame is not None and fid != last_id:
                frames += 1
                last_id = fid
            time.sleep(0.05)
        log.info("Captured %d unique frames in %ds", frames, seconds)
        return 0 if frames > 0 else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
