from dataclasses import dataclass, field
from typing import List, Dict

from .models import Language


@dataclass
class LanguageConfig:
    source_filename: str
    compiled_filename: str
    need_compile: bool
    compile_cmd: List[str]
    run_cmd: List[str]
    time_factor: int = field(default=1)
    memory_factor: int = field(default=1)


class LanguageRegistry:
    _mapping: Dict[Language, LanguageConfig] = {}

    @classmethod
    def register(cls, lang: Language, config: LanguageConfig) -> None:
        if lang in cls._mapping:
            raise ValueError("Language %s is already registered" % lang)
        cls._mapping[lang] = config

    @classmethod
    def get_config(cls, lang: Language) -> LanguageConfig:
        if lang not in cls._mapping:
            raise ValueError("Language %s is not registered" % lang)
        return cls._mapping[lang]


LanguageRegistry.register(
    Language.C,
    LanguageConfig(
        source_filename="Main.c",
        compiled_filename="Main",
        need_compile=True,
        compile_cmd=[
            "/usr/bin/gcc", "Main.c", "-o", "Main",
            "-std=c11", "-Wall", "-lm", "--static",
            "-fmax-errors=3", "-DONLINE_JUDGE", "-w"
        ],
        run_cmd=["./Main"]
    )
)

LanguageRegistry.register(
    Language.CPP,
    LanguageConfig(
        source_filename="Main.cpp",
        compiled_filename="Main",
        need_compile=True,
        compile_cmd=[
            "/usr/bin/g++", "Main.cpp", "-o", "Main",
            "-std=c++11", "-Wall", "-lm", "--static",
            "-fmax-errors=3", "-DONLINE_JUDGE", "-w"
        ],
        run_cmd=["./Main"]
    )
)
