from enum import Enum
from dataclasses import dataclass, field
from typing import Union, Dict, Optional, List

from .config import DEFAULT_TIME_LIMIT, DEFAULT_MEMORY_LIMIT, \
    DEFAULT_PROC_LIMIT, DEFAULT_CPU_RATE_LIMIT, DEFAULT_OUTPUT_LIMIT


class JudgeStatus(int, Enum):
    Pending = 0
    RunningJudge = 1
    CompileError = 2
    Accepted = 3
    RuntimeError = 4
    WrongAnswer = 5
    TimeLimitExceeded = 6
    MemoryLimitExceeded = 7
    OutputLimitExceeded = 8
    PresentationError = 9
    SystemError = 10
    RejudgePending = 11
    Skipped = 12


class SandboxStatus(str, Enum):
    Accepted = 'Accepted'
    MemoryLimitExceeded = 'Memory Limit Exceeded'
    TimeLimitExceeded = 'Time Limit Exceeded'
    OutputLimitExceeded = 'Output Limit Exceeded'
    FileError = 'File Error'
    NonzeroExitStatus = 'Nonzero Exit Status'
    Signalled = 'Signalled'
    InternalError = 'Internal Error'


class Language(Enum):
    C = 1
    CPP = 2
    Java = 3


@dataclass
class LocalFile:
    src: str


@dataclass
class MemoryFile:
    content: str


@dataclass
class PreparedFile:
    fileId: str


@dataclass
class Collector:
    name: str
    max: int = field(default=DEFAULT_OUTPUT_LIMIT)


@dataclass
class SandboxCmd:
    args: List[str]
    env: List[str] = field(default_factory=lambda: ["PATH=/usr/bin:/bin"])

    files: List[Union[LocalFile, MemoryFile, PreparedFile, Collector]] = \
        field(default_factory=list)

    cpuLimit: int = field(default=DEFAULT_TIME_LIMIT)
    clockLimit: int = field(default=DEFAULT_TIME_LIMIT*2)
    memoryLimit: int = field(default=DEFAULT_MEMORY_LIMIT)
    procLimit: int = field(default=DEFAULT_PROC_LIMIT)
    cpuRateLimit: int = field(default=DEFAULT_CPU_RATE_LIMIT)

    copyIn: Dict[str, Union[LocalFile, MemoryFile, PreparedFile]] = \
        field(default_factory=dict)

    copyOut: List[str] = field(default_factory=list)
    copyOutCached: List[str] = field(default_factory=list)
    copyOutMax: int = field(default=DEFAULT_OUTPUT_LIMIT)


@dataclass
class SandboxResult:
    status: SandboxStatus = field(default=SandboxStatus.InternalError)
    error: Optional[str] = field(default=None)
    exitStatus: int = field(default=0)

    time: int = field(default=0)
    memory: int = field(default=0)
    procPeak: Optional[int] = field(default=None)
    runTime: int = field(default=0)

    files: Optional[Dict[str, str]] = field(default=None)
    fileIds: Optional[Dict[str, str]] = field(default=None)
    fileError: Optional[List[str]] = field(default=None)

    def __post_init__(self):
        if not isinstance(self.status, SandboxStatus):
            self.status = SandboxStatus(self.status)


@dataclass
class Testcase:
    input: Union[LocalFile, MemoryFile]
    output: Union[LocalFile, MemoryFile]


@dataclass
class Submission:
    timeLimit: int
    memoryLimit: int
    testcases: List[Testcase]
    language: Language
    code: str


@dataclass
class TestcaseResult:
    time: int = field(default=0)
    memory: int = field(default=0)
    status: JudgeStatus = field(default=JudgeStatus.Pending)


@dataclass
class SubmissionResult:
    time: int = field(default=0)
    memory: int = field(default=0)
    testcases: List[TestcaseResult] = field(default_factory=list)
    status: JudgeStatus = field(default=JudgeStatus.Pending)
    error: str = field(default='')
