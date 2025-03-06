import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Set, Union

from .client import SandboxClient as Client
from .config import DEFAULT_CHECKER, LOGGER_NAME
from .language import LanguageConfig, LanguageRegistry
from .models import *

logger = logging.getLogger(f"{LOGGER_NAME}.judger")


class DefaultChecker:

    SOURCE_FILENAME = "SPJ.c"
    COMPILED_FILENAME = "SPJ"
    COMPILE_CMD = ["/usr/bin/g++", "SPJ.c", "-o", "SPJ"]
    RUN_CMD = ["./SPJ", "tc.in", 'tc.out', 'user.out']

    STATUS_MAP: dict[int, JudgeStatus] = {
        0: JudgeStatus.Accepted,
        1: JudgeStatus.WrongAnswer,
        2: JudgeStatus.PresentationError
    }

    def __init__(self, client: Client, code_file: Union[str, Path]):
        self.client = client
        self.code_file = code_file
        self.compiled_file: Optional[PreparedFile] = None
        logger.debug("Checker initialized with code file: '%s'", code_file)

    async def __aenter__(self) -> 'DefaultChecker':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self.compiled_file is not None:
            await self.client.delete_file(self.compiled_file.fileId)
            logger.debug("Checker closed")

    async def compile(self) -> None:
        logger.debug("Compiling checker")

        with open(self.code_file, 'rt', encoding='utf-8') as f:
            checker_code = f.read()

        cmd = SandboxCmd(
            args=self.COMPILE_CMD,
            files=[
                MemoryFile(""),
                Collector("stdout"),
                Collector("stderr")
            ],
            copyIn={
                self.SOURCE_FILENAME:
                    MemoryFile(checker_code)
            },
            copyOutCached=[
                self.COMPILED_FILENAME
            ]
        )
        compiled_result = (await self.client.run_command([cmd]))[0]

        if compiled_result.status != SandboxStatus.Accepted:
            raise RuntimeError(
                "Failed to compile: \n%s" %
                compiled_result.files.get("stderr", "")
            )
        self.compiled_file = PreparedFile(compiled_result.fileIds['SPJ'])

    async def check(self, input_file: PreparedFile, output_file: PreparedFile,
                    user_file: PreparedFile) -> JudgeStatus:
        logger.debug(
            "Checking with 'tc.in': %s, 'tc.out': %s, 'user.out': %s",
            input_file, output_file, user_file
        )
        if self.compiled_file is None:
            await self.compile()

        cmd = SandboxCmd(
            args=self.RUN_CMD,
            files=[
                MemoryFile(""),
                Collector("stdout"),
                Collector("stderr")
            ],
            copyIn={
                self.COMPILED_FILENAME: self.compiled_file,
                "tc.in": input_file,
                "tc.out": output_file,
                "user.out": user_file
            }
        )
        checker_result = (await self.client.run_command([cmd]))[0]

        if checker_result.exitStatus not in self.STATUS_MAP:
            raise RuntimeError(
                "Checker failed with unexpected exit status: %d" %
                checker_result.exitStatus
            )
        return self.STATUS_MAP.get(checker_result.exitStatus)


class Judger:

    STATUS_PRIORITY: List[JudgeStatus] = [
        JudgeStatus.SystemError,
        JudgeStatus.OutputLimitExceeded,
        JudgeStatus.MemoryLimitExceeded,
        JudgeStatus.TimeLimitExceeded,
        JudgeStatus.RuntimeError,
        JudgeStatus.WrongAnswer,
        JudgeStatus.PresentationError
    ]

    STATUS_MAP: dict[SandboxStatus, JudgeStatus] = {
        SandboxStatus.MemoryLimitExceeded: JudgeStatus.MemoryLimitExceeded,
        SandboxStatus.TimeLimitExceeded: JudgeStatus.TimeLimitExceeded,
        SandboxStatus.OutputLimitExceeded: JudgeStatus.OutputLimitExceeded,
        SandboxStatus.NonzeroExitStatus: JudgeStatus.RuntimeError,
        SandboxStatus.Signalled: JudgeStatus.RuntimeError
    }

    SKIP_STATUS: Set[JudgeStatus] = {
        JudgeStatus.MemoryLimitExceeded,
        JudgeStatus.TimeLimitExceeded,
        JudgeStatus.OutputLimitExceeded
    }

    def __init__(self, client: Client, submission: Submission):
        logger.debug(
            "Initialing Judger with client: %s, submission: %s",
            client, submission
        )
        self.client = client
        self.submission = submission

        self.checker = DefaultChecker(
            self.client,
            DEFAULT_CHECKER
        )
        self.result = SubmissionResult(
            sid=self.submission.sid,
            judge=JudgeStatus.Pending
        )

        self.compiled_file: Optional[PreparedFile] = None
        self.cleanup_tasks: List[asyncio.Task] = list()

        try:
            self.language = LanguageRegistry.get_config(
                self.submission.language
            )
        except ValueError as e:
            self.result.judge = JudgeStatus.SystemError
            logger.error(
                "Submission %d failed on initialization: "
                "unsupported language %s",
                self.submission.sid,
                self.submission.language
            )
        logger.debug("Submission %d initialized", self.submission.sid)

    async def compile(self) -> None:
        if self.compiled_file is not None:
            return logger.warning(
                "Submission %d already compiled",
                self.submission.sid
            )
        logger.debug("Submission %d compiling", self.submission.sid)

        try:
            cmd = SandboxCmd(
                args=self.language.compile_cmd,
                files=[
                    MemoryFile(""),
                    Collector("stdout"),
                    Collector("stderr")
                ],
                copyIn={
                    self.language.source_filename:
                        MemoryFile(self.submission.code)
                },
                copyOutCached=[
                    self.language.compiled_filename
                ]
            )
            compiled_result = (
                await self.client.run_command([cmd])
            )[0]

            if compiled_result.status != SandboxStatus.Accepted:
                self.result.judge = JudgeStatus.CompileError
                self.result.error = compiled_result.files.get("stderr", "")
                logger.debug(
                    "Submission %d ended with compile error: %s",
                    self.submission.sid, self.result.error
                )
            else:
                self.compiled_file = PreparedFile(
                    compiled_result.fileIds[self.language.compiled_filename]
                )
                logger.debug("Submission %d compiled", self.submission.sid)

        except Exception as e:
            self.result.judge = JudgeStatus.SystemError
            return logger.error(
                "Submission %d failed on compilation: %s",
                self.submission.sid, e
            )

    async def run_testcase(self, testcase: Testcase) -> TestcaseResult:
        logger.debug("Running testcase: '%s'", testcase.uuid)
        result = TestcaseResult(
            uuid=testcase.uuid,
            judge=JudgeStatus.RunningJudge
        )

        def get_runtime_dependencies() -> dict:
            if self.language.need_compile:
                return {
                    self.language.compiled_filename:
                        self.compiled_file
                }
            else:
                return {
                    self.language.source_filename:
                        MemoryFile(self.submission.code)
                }

        cmd = SandboxCmd(
            args=self.language.run_cmd,
            cpuLimit=self.submission.timeLimit * 1_000_000,
            memoryLimit=self.submission.memoryLimit * 1024,
            files=[testcase.input, Collector("stdout"), Collector("stderr")],
            copyIn=get_runtime_dependencies(),
            copyOutCached=["stdout"])
        run_result = (await self.client.run_command([cmd]))[0]

        result.time = min(run_result.time // 1_000_000,
                          self.submission.timeLimit)
        result.memory = min(run_result.memory // 1024,
                            self.submission.memoryLimit)
        output_file = PreparedFile(run_result.fileIds['stdout'])

        if run_result.status == SandboxStatus.Accepted:
            result.judge = await self.checker.check(
                testcase.input, testcase.output, output_file)
        else:
            result.judge = self.STATUS_MAP.get(
                run_result.status, JudgeStatus.SystemError)

        self.cleanup_tasks.append(asyncio.create_task(
            self.client.delete_file(output_file.fileId)))
        logger.debug("Testcase '%s' finished with judge status: '%s'",
                     testcase.uuid, result.judge)
        return result

    async def cleanup(self) -> None:
        logger.debug("Submission %d cleanup started", self.submission.sid)

        self.cleanup_tasks.append(
            asyncio.create_task(self.checker.close())
        )
        if self.compiled_file is not None:
            self.cleanup_tasks.append(
                asyncio.create_task(
                    self.client.delete_file(self.compiled_file.fileId)
                )
            )
        await asyncio.gather(*self.cleanup_tasks)
        self.cleanup_tasks.clear()

        logger.debug("Submission %d cleanup completed", self.submission.sid)

    async def run(self) -> None:
        if self.result.judge != JudgeStatus.Pending:
            return logger.warning(
                "Submission %d result already set: %s",
                self.submission.sid, self.result.judge
            )
        logger.debug("Submission %d start judging", self.submission.sid)

        if self.language.need_compile:
            await self.compile()
            if self.result.judge != JudgeStatus.Pending:
                return
            elif self.compiled_file is None:
                self.result.judge = JudgeStatus.SystemError
                return logger.error(
                    "Submission %d failed on compilation: no compiled file",
                    self.submission.sid
                )

        if len(self.submission.testcases) == 0:
            self.result.judge = JudgeStatus.SystemError
            return logger.error(
                "Submission %d failed on judging: no testcases",
                self.submission.sid
            )

        try:
            await self.checker.compile()
        except Exception as e:
            self.result.judge = JudgeStatus.SystemError
            return logger.error(
                "Submission %d failed on checker compilation: %s",
                self.submission.sid, e
            )

        skipped = False
        for testcase in self.submission.testcases:
            if skipped:
                testcase_result = TestcaseResult(
                    uuid=testcase.uuid,
                    judge=JudgeStatus.Skipped
                )
            else:
                try:
                    testcase_result = await self.run_testcase(testcase)
                except Exception as e:
                    testcase_result = TestcaseResult(
                        uuid=testcase.uuid,
                        judge=JudgeStatus.SystemError
                    )
                    logger.error(
                        "Submission %d failed on testing '%s': %s",
                        self.submission.sid, testcase.uuid, e
                    )
            self.result.testcases.append(testcase_result)

            if testcase_result.judge in self.SKIP_STATUS:
                skipped = True

        if len(self.result.testcases) == 0:
            self.result.judge = JudgeStatus.SystemError
            return logger.error(
                "Submission %d failed on judging: no testcase results",
                self.submission.sid
            )

        self.result.time = max(
            testcase.time for testcase in self.result.testcases
        )
        self.result.memory = max(
            testcase.memory for testcase in self.result.testcases
        )

        if all(
            testcase.judge == JudgeStatus.Accepted
            for testcase in self.result.testcases
        ):
            self.result.judge = JudgeStatus.Accepted
        else:
            for status in self.STATUS_PRIORITY:
                if any(
                    testcase.judge == status
                    for testcase in self.result.testcases
                ):
                    self.result.judge = status
                    break
            else:
                self.result.judge = JudgeStatus.SystemError
                return logger.error(
                    "Submission %d failed on final check: no status found",
                    self.submission.sid
                )

    async def get_result(self) -> SubmissionResult:
        if self.result.judge == JudgeStatus.Pending:
            try:
                await self.run()
            except Exception as e:
                self.result.judge = JudgeStatus.SystemError
                logger.error(
                    "Submission %d failed on judging: %s",
                    self.submission.sid, e
                )
            try:
                await self.cleanup()
            except Exception as e:
                logger.error(
                    "Submission %d failed on cleanup: %s",
                    self.submission.sid, e
                )
        logger.debug(
            "Submission %d result: %s",
            self.submission.sid, self.result
        )
        return self.result
