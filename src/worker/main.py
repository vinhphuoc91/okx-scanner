"""Background worker entry point — tier-scheduled scanner loop."""

from __future__ import annotations

import signal

from src.utils.logger import configure_logging, get_logger
from src.worker.scanner_loop import ScannerLoop

log = get_logger(__name__)

_loop: ScannerLoop | None = None


def _handle_signal(signum: int, _frame: object) -> None:
    log.info("worker.signal", signum=signum)
    if _loop is not None:
        _loop.request_shutdown()


def main() -> None:
    """Start the scanner worker loop."""
    global _loop  # noqa: PLW0603

    configure_logging()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _loop = ScannerLoop()
    _loop.run_forever()


if __name__ == "__main__":
    main()
