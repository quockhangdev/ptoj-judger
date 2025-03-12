import pytest
from judger.language import *


def test_duplicate_register_language():
    with pytest.raises(ValueError):
        LanguageRegistry.register(
            Language.C,
            LanguageConfig(
                source_filename="Main.c",
                compiled_filename="Main",
                need_compile=True,
                compile_cmd=[],
                run_cmd=[]
            )
        )


def test_get_unregistered_language():
    with pytest.raises(ValueError):
        LanguageRegistry.get_config(-1)
