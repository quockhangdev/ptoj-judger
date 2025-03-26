import logging
from pathlib import Path
from typing import List, Optional, Union

from .client import SandboxClient
from .config import DEFAULT_CHECKER, LOGGER_NAME
from .models import (
    JudgeStatus,
    SandboxStatus,
    LocalFile,
    MemoryFile,
    PreparedFile,
    Collector,
    SandboxCmd,
)

logger = logging.getLogger(f"{LOGGER_NAME}.checker")


class TestlibChecker:

    SOURCE_FILENAME: str = "Checker.cpp"
    COMPILED_FILENAME: str = "Checker"
    COMPILE_CMD: List[str] = [
        "/usr/bin/g++-12", "Checker.cpp", "-o", "Checker",
        "-std=c++17", "-O2", "-lm", "-w", "-fmax-errors=3", "--static"
    ]
    RUN_CMD: List[str] = [
        "./Checker", "infile", "outfile", "ansfile"
    ]
    TESTLIB_PATH: Path = Path(__file__).parent / "testlib" / "testlib.h"

    def __init__(
        self,
        client: SandboxClient,
        code: str
    ) -> None:
        self.client = client
        self.code = code
        self.compiled_file: Optional[PreparedFile] = None

        logger.debug("Testlib checker initialized")

    async def __aenter__(self) -> 'TestlibChecker':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self.compiled_file is not None:
            await self.client.delete_file(self.compiled_file.fileId)
            logger.debug("Testlib checker closed")

    async def compile(self) -> None:
        if self.compiled_file is not None:
            return
        logger.debug("Compiling checker")

        if not self.TESTLIB_PATH.exists():
            raise FileNotFoundError(
                "Testlib header file not found: %s" %
                self.TESTLIB_PATH
            )
        with open(self.TESTLIB_PATH, 'rt', encoding='utf-8') as f:
            testlib_code = f.read()

        cmd = SandboxCmd(
            args=self.COMPILE_CMD,
            files=[
                MemoryFile(""),
                Collector("stdout"),
                Collector("stderr")
            ],
            copyIn={
                self.SOURCE_FILENAME:
                    MemoryFile(self.code),
                "testlib.h":
                    MemoryFile(testlib_code)
            },
            copyOutCached=[
                self.COMPILED_FILENAME
            ]
        )
        compiled_result = (
            await self.client.run_command([cmd])
        )[0]

        if compiled_result.status != SandboxStatus.Accepted:
            raise RuntimeError(
                "Failed to compile Testlib checker: \n%s" %
                compiled_result.files.get("stderr", "")
            )
        self.compiled_file = PreparedFile(
            compiled_result.fileIds[self.COMPILED_FILENAME])

    async def check(
        self,
        input_file: Union[LocalFile, MemoryFile, PreparedFile],
        answer_file: Union[LocalFile, MemoryFile, PreparedFile],
        output_file: Union[LocalFile, MemoryFile, PreparedFile]
    ) -> JudgeStatus:
        logger.debug(
            "Checking with 'infile': %s, 'outfile': %s, 'ansfile': %s",
            input_file, output_file, answer_file
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
                "infile": input_file,
                "outfile": output_file,
                "ansfile": answer_file
            }
        )
        checker_result = (
            await self.client.run_command([cmd])
        )[0]

        logger.debug("Checker result: %s", checker_result)

        if checker_result.status == SandboxStatus.Accepted:
            return JudgeStatus.Accepted
        elif checker_result.status == SandboxStatus.NonzeroExitStatus:
            return JudgeStatus.WrongAnswer
        else:
            return JudgeStatus.SystemError


class DefaultChecker(TestlibChecker):

    RUN_CMD: List[str] = [
        "./Checker", "tc.in", 'tc.out', 'user.out'
    ]

    STATUS_MAP: dict[int, JudgeStatus] = {
        0: JudgeStatus.Accepted,
        1: JudgeStatus.WrongAnswer,
        2: JudgeStatus.PresentationError
    }

    def __init__(
        self,
        client: SandboxClient,
        code_file: Union[str, Path] = DEFAULT_CHECKER
    ) -> None:
        self.client = client
        self.compiled_file: Optional[PreparedFile] = None

        try:
            with open(code_file, 'rt', encoding='utf-8') as f:
                self.code = f.read()
        except FileNotFoundError as e:
            raise FileNotFoundError(
                "Checker code file not found: %s" %
                code_file
            ) from e

        logger.debug(
            "Checker initialized with code file: '%s'",
            code_file
        )

    async def compile(self) -> None:
        if self.compiled_file is not None:
            return
        logger.debug("Compiling checker")

        cmd = SandboxCmd(
            args=self.COMPILE_CMD,
            files=[
                MemoryFile(""),
                Collector("stdout"),
                Collector("stderr")
            ],
            copyIn={
                self.SOURCE_FILENAME:
                    MemoryFile(self.code)
            },
            copyOutCached=[
                self.COMPILED_FILENAME
            ]
        )
        compiled_result = (
            await self.client.run_command([cmd])
        )[0]

        if compiled_result.status != SandboxStatus.Accepted:
            raise RuntimeError(
                "Failed to compile: \n%s" %
                compiled_result.files.get("stderr", "")
            )
        self.compiled_file = PreparedFile(
            compiled_result.fileIds[self.COMPILED_FILENAME])

    async def check(
        self,
        input_file: Union[LocalFile, MemoryFile, PreparedFile],
        output_file: Union[LocalFile, MemoryFile, PreparedFile],
        user_file: Union[LocalFile, MemoryFile, PreparedFile]
    ) -> JudgeStatus:
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
        checker_result = (
            await self.client.run_command([cmd])
        )[0]

        if checker_result.exitStatus not in self.STATUS_MAP:
            raise RuntimeError(
                "Checker failed with unexpected exit status: %d" %
                checker_result.exitStatus
            )
        return self.STATUS_MAP.get(checker_result.exitStatus)
