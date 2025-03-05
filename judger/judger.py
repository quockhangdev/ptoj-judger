import asyncio
from pathlib import Path
from typing import List, Optional, Union

from .client import SandboxClient as Client
from .config import DEFAULT_CHECKER
from .language import LanguageRegistry
from .models import *


class DefaultChecker:

    COMPILE_ARGS = ["/usr/bin/g++", "SPJ.c", "-o", "SPJ"]
    CHECK_ARGS = ["./SPJ", "tc.in", 'tc.out', 'user.out']

    CHECKER_AC = 0
    CHECKER_WA = 1
    CHECKER_PE = 2

    def __init__(self, client: Client, code_file: Union[str, Path]):
        self.client = client
        self.code_file = code_file
        self.compiled_file: Optional[PreparedFile] = None

    async def __aenter__(self) -> 'DefaultChecker':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self.compiled_file is not None:
            await self.client.delete_file(self.compiled_file.fileId)

    async def _prepare(self) -> None:
        with open(self.code_file, 'rt') as f:
            checker_code = f.read()

        cmd = SandboxCmd(
            args=self.COMPILE_ARGS,
            files=[MemoryFile(""), Collector("stdout"), Collector("stderr")],
            copyIn={"SPJ.c": MemoryFile(checker_code)},
            copyOutCached=["SPJ"]
        )
        compiled_result = (await self.client.run_command([cmd]))[0]

        if compiled_result.status != SandboxStatus.Accepted:
            raise RuntimeError(compiled_result.files['stderr'])
        self.compiled_file = PreparedFile(compiled_result.fileIds['SPJ'])

    async def check(self, input_file: PreparedFile, output_file: PreparedFile,
                    user_file: PreparedFile) -> JudgeStatus:
        if self.compiled_file is None:
            await self._prepare()

        cmd = SandboxCmd(
            args=self.CHECK_ARGS,
            files=[MemoryFile(""), Collector("stdout"), Collector("stderr")],
            copyIn={
                "SPJ": self.compiled_file,
                "tc.in": input_file,
                "tc.out": output_file,
                "user.out": user_file
            }
        )
        checker_result = (await self.client.run_command([cmd]))[0]

        match checker_result.exitStatus:
            case self.CHECKER_AC:
                return JudgeStatus.Accepted
            case self.CHECKER_WA:
                return JudgeStatus.WrongAnswer
            case self.CHECKER_PE:
                return JudgeStatus.PresentationError
            case _:
                return JudgeStatus.SystemError


class Judger:

    STATUS_PRIORITY = [
        JudgeStatus.SystemError,
        JudgeStatus.OutputLimitExceeded,
        JudgeStatus.MemoryLimitExceeded,
        JudgeStatus.TimeLimitExceeded,
        JudgeStatus.RuntimeError,
        JudgeStatus.WrongAnswer,
        JudgeStatus.PresentationError]

    def __init__(self, client: Client, submission: Submission):
        self.client = client
        self.submission = submission

    def _init(self) -> None:
        self.lang_conf = LanguageRegistry.get_config(self.submission.language)
        self.result = SubmissionResult(status=JudgeStatus.RunningJudge)
        self.checker = DefaultChecker(self.client, DEFAULT_CHECKER)
        self.compiled_file: Optional[PreparedFile] = None
        self.cleanup_tasks: List[asyncio.Task] = []

    async def _compile(self) -> None:
        cmd = SandboxCmd(
            args=self.lang_conf.compile_cmd,
            files=[MemoryFile(""), Collector("stdout"), Collector("stderr")],
            copyIn={self.lang_conf.source_filename:
                    MemoryFile(self.submission.code)},
            copyOutCached=[self.lang_conf.compiled_filename])
        compiled_result = (await self.client.run_command([cmd]))[0]

        if compiled_result.status != SandboxStatus.Accepted:
            raise RuntimeError(compiled_result.files['stderr'])
        self.compiled_file = PreparedFile(
            compiled_result.fileIds[self.lang_conf.compiled_filename])

    def _get_runtime_dependencies(self) -> dict:
        if self.lang_conf.need_compile:
            return {self.lang_conf.compiled_filename: self.compiled_file}
        return {self.lang_conf.source_filename: MemoryFile(self.submission.code)}

    async def _run_testcase(self, testcase: Testcase) -> TestcaseResult:

        result = TestcaseResult(status=JudgeStatus.RunningJudge)

        cmd = SandboxCmd(
            args=self.lang_conf.run_cmd,
            cpuLimit=self.submission.timeLimit * 1_000_000,
            memoryLimit=self.submission.memoryLimit * 1024,
            files=[testcase.input, Collector("stdout"), Collector("stderr")],
            copyIn=self._get_runtime_dependencies(),
            copyOutCached=["stdout"])
        run_result = (await self.client.run_command([cmd]))[0]

        result.time = run_result.time // 1_000_000
        result.memory = run_result.memory // 1024

        match run_result.status:
            case SandboxStatus.Accepted:
                pass
            case SandboxStatus.MemoryLimitExceeded:
                result.status = JudgeStatus.MemoryLimitExceeded
            case SandboxStatus.TimeLimitExceeded:
                result.status = JudgeStatus.TimeLimitExceeded
            case SandboxStatus.OutputLimitExceeded:
                result.status = JudgeStatus.OutputLimitExceeded
            case SandboxStatus.NonzeroExitStatus:
                result.status = JudgeStatus.RuntimeError
            case SandboxStatus.Signalled:
                result.status = JudgeStatus.RuntimeError
            case _:
                result.status = JudgeStatus.SystemError

        if run_result.status == SandboxStatus.Accepted:

            output_file = PreparedFile(run_result.fileIds['stdout'])
            checker_result = await self.checker.check(
                testcase.input, testcase.output, output_file)

            match checker_result:
                case JudgeStatus.Accepted:
                    result.status = JudgeStatus.Accepted
                case JudgeStatus.WrongAnswer:
                    result.status = JudgeStatus.WrongAnswer
                case JudgeStatus.PresentationError:
                    result.status = JudgeStatus.PresentationError
                case _:
                    result.status = JudgeStatus.SystemError

            self.cleanup_tasks.append(asyncio.create_task(
                self.client.delete_file(output_file.fileId)))

        return result

    async def _run(self) -> None:

        if self.lang_conf.need_compile:
            try:
                await self._compile()
            except Exception as e:
                self.result.status = JudgeStatus.CompileError
                self.result.error = str(e)
                return
            
        if len(self.submission.testcases) == 0:
            self.result.status = JudgeStatus.SystemError
            self.result.error = "No testcases provided"
            return

        try:
            await self.checker._prepare()
        except Exception as e:
            self.result.status = JudgeStatus.SystemError
            self.result.error = str(e)
            return

        skipped = False
        for testcase in self.submission.testcases:
            if skipped:
                testcase_result = TestcaseResult(status=JudgeStatus.Skipped)
            else:
                try:
                    testcase_result = await self._run_testcase(testcase)
                except Exception as e:
                    testcase_result = TestcaseResult(
                        status=JudgeStatus.SystemError)
            self.result.testcases.append(testcase_result)
            if testcase_result.status in {
                    JudgeStatus.MemoryLimitExceeded,
                    JudgeStatus.TimeLimitExceeded,
                    JudgeStatus.OutputLimitExceeded}:
                skipped = True

        self.result.time = max(testcase.time for testcase in self.result.testcases)
        self.result.memory = max(testcase.memory for testcase in self.result.testcases)

        if all(testcase.status == JudgeStatus.Accepted for testcase in self.result.testcases):
            self.result.status = JudgeStatus.Accepted
        else:
            for status in self.STATUS_PRIORITY:
                if any(testcase.status == status for testcase in self.result.testcases):
                    self.result.status = status
                    break
            else:
                self.result.status = JudgeStatus.SystemError

    async def run(self) -> SubmissionResult:
        self._init()

        try:
            await self._run()
        except Exception as e:
            JudgeStatus.SystemError
            self.result.error = str(e)
        finally:
            await self._cleanup()
        return self.result

    async def _cleanup(self) -> None:
        self.cleanup_tasks.append(asyncio.create_task(self.checker.close()))
        if self.compiled_file is not None:
            self.cleanup_tasks.append(asyncio.create_task(
                self.client.delete_file(self.compiled_file.fileId)))
        await asyncio.gather(*self.cleanup_tasks)
