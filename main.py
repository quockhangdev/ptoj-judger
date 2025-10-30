import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from rich.logging import RichHandler
from rich.traceback import install as install_traceback

from judger import Scheduler, LOGGER_NAME


def setup_logger(
    log_file: Optional[str] = None,
    debug: bool = True
) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    console_handler = RichHandler(
        log_time_format="[%X.%f]",
        rich_tracebacks=True)
    logger.addHandler(console_handler)

    if log_file is not None:
        log_format = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)


async def main():
    install_traceback()

    redis_url: str = os.getenv(
        'PTOJ_REDIS_URL',
        'redis://localhost:6379'
    )
    sandbox_endpoint: str = os.getenv(
        'PTOJ_SANDBOX_ENDPOINT',
        'http://localhost:5050'
    )
    init_concurrent: int = int(os.getenv(
        'PTOJ_INIT_CONCURRENT',
        '4'
    ))
    log_file: Optional[str] = os.getenv(
        'PTOJ_LOG_FILE',
        'judger.log'
    )
    debug: bool = os.getenv('PTOJ_DEBUG', '1') == '1'

    setup_logger(log_file, debug)

    logger = logging.getLogger(f"{LOGGER_NAME}.main")
    logger.info(
        "Starting with "
        f"redis_url={redis_url}, "
        f"sandbox_endpoint={sandbox_endpoint}, "
        f"init_concurrent={init_concurrent}, "
        f"log_file='{log_file}'"
    )

    scheduler = Scheduler(
        redis_url=redis_url,
        sandbox_endpoint=sandbox_endpoint,
        init_concurrent=init_concurrent
    )
    scheduler.start()

    loop = asyncio.get_running_loop()

    if sys.platform == 'linux':
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(scheduler.stop())
            )
    try:
        await scheduler.wait()
    except asyncio.CancelledError:
        await scheduler.stop()
        raise
    finally:
        logger.info("Scheduler stopped")

if __name__ == '__main__':
    asyncio.run(main())
