import asyncio
import json
import logging
from dataclasses import asdict
from time import time
from typing import List, Optional

import redis.asyncio as redis

from .client import SandboxClient
from .config import (
    LOGGER_NAME,
    RESULT_QUEUE_NAME,
    TASK_QUEUE_NAME
)
from .judger import DefaultChecker, Judger
from .models import (
    JudgeStatus,
    Submission,
    SubmissionResult
)

logger = logging.getLogger(f"{LOGGER_NAME}.scheduler")


class Scheduler:

    def __init__(
        self,
        redis_url: str,
        sandbox_endpoint: str,
        init_concurrent: int = 1
    ) -> None:
        self.redis_url = redis_url
        self.sandbox_endpoint = sandbox_endpoint
        self.init_concurrent = init_concurrent
        self.redis_pool: Optional[redis.ConnectionPool] = None
        self.comsumers: List[asyncio.Task] = []
        self.is_running: bool = False

        logger.debug(
            "Scheduler initialized with "
            f"redis_url={self.redis_url}, "
            f"sandbox_endpoint={self.sandbox_endpoint}, "
            f"init_concurrent={self.init_concurrent}"
        )

    async def get_submission(self) -> Optional[Submission]:
        async with redis.Redis.from_pool(
            connection_pool=self.redis_pool
        ) as conn:
            while self.is_running:
                pop_value = await conn.blpop(
                    TASK_QUEUE_NAME,
                    timeout=5
                )
                if pop_value is None:
                    continue

                logger.debug("Get submission %s", pop_value)
                _, value = pop_value
                return Submission(**json.loads(value))

    async def put_result(
        self,
        result: SubmissionResult
    ) -> None:
        async with redis.Redis.from_pool(
            connection_pool=self.redis_pool
        ) as conn:
            logger.debug("Put result %s", result)
            await conn.rpush(
                RESULT_QUEUE_NAME,
                json.dumps(asdict(result))
            )

    async def process(
        self,
        idx: int,
        client: SandboxClient,
        checker: DefaultChecker
    ) -> None:
        submission = await self.get_submission()
        if submission is None:
            return

        logger.debug(
            "Processor %d processing submission %s",
            idx, submission
        )
        await self.put_result(
            SubmissionResult(
                sid=submission.sid,
                judge=JudgeStatus.RunningJudge
            )
        )

        try:
            judger = Judger(client, submission, checker)
            result = await judger.get_result()
            await self.put_result(result)

            logger.info(
                "Processor %d finished submission %s with result %s",
                idx, submission.sid, result.judge.name
            )

        except Exception as e:
            logger.error(
                "Processor %d failed submission %s with error %s",
                idx, submission, e
            )
            await self.put_result(
                SubmissionResult(
                    sid=submission.sid,
                    judge=JudgeStatus.SystemError
                )
            )

    async def processor(self, idx: int) -> None:
        logger.debug("Processor %d started", idx)

        async with SandboxClient(
            endpoint=self.sandbox_endpoint
        ) as client:
            async with DefaultChecker(
                client=client
            ) as checker:
                while self.is_running:
                    await self.process(
                        idx,
                        client,
                        checker
                    )
        logger.debug("Processor %d stopped", idx)

    def start(self) -> None:
        logger.debug("Scheduler starting...")
        self.redis_pool = redis.ConnectionPool.from_url(
            url=self.redis_url
        )
        self.is_running = True
        self.comsumers = [
            asyncio.create_task(self.processor(idx))
            for idx in range(self.init_concurrent)
        ]

    async def wait(self) -> None:
        await asyncio.gather(*self.comsumers)

    async def close(self) -> None:
        if self.redis_pool is not None:
            await self.redis_pool.disconnect()
            self.redis_pool = None
        logger.debug("Scheduler dependencies closed")

    async def stop(self) -> None:
        logger.debug("Scheduler stopping...")
        self.is_running = False
        await self.wait()
        await self.close()
        logger.debug("Scheduler stopped")
