import pytest
from judger.models import *


def test_judge_status_repr():
    assert "Accepted" in repr(JudgeStatus.Accepted)


def test_sandbox_status_repr():
    assert "Accepted" in repr(SandboxStatus.Accepted)


def test_language_repr():
    assert "Python" in repr(Language.Python)


def test_testcase_file_prase_local():
    testcase = Testcase(
        uuid='c5f8bfda-700c-4ae4-8dae-d1a16e719b5c',
        input={"src": "input"},
        output={"src": "output"}
    )
    assert isinstance(testcase.input, LocalFile)
    assert isinstance(testcase.output, LocalFile)


def test_testcase_file_prase_prepared():
    testcase = Testcase(
        uuid='51510612-d1ed-43a1-ab1d-cf9137e4d085',
        input={"fileId": "input"},
        output={"fileId": "output"}
    )
    assert isinstance(testcase.input, PreparedFile)
    assert isinstance(testcase.output, PreparedFile)


def test_testcase_file_prase_memory():
    testcase = Testcase(
        uuid='7c8762b1-f14b-4414-9099-3a4a16d90b4e',
        input={"content": "input"},
        output={"content": "output"}
    )
    assert isinstance(testcase.input, MemoryFile)
    assert isinstance(testcase.output, MemoryFile)


def test_testcase_file_prase_invalid():
    with pytest.raises(ValueError):
        Testcase(
            uuid='3a095dfc-edc3-47d6-a734-422413eeda48',
            input={"invalid": "input"},
            output={"invalid": "output"}
        )


def test_submission_post_init():
    submission = Submission(
        sid=1,
        timeLimit=1000,
        memoryLimit=32768,
        testcases=[
            {
                "uuid": '3de595cb-48f7-46e4-bc49-902ccb6937b2',
                "input": {"content": ""},
                "output": {"content": "Hello, World!"}
            }
        ],
        language=Language.Python.value,
        code="print('Hello, World!')"
    )
    assert isinstance(submission.language, Language)
    assert isinstance(submission.testcases[0], Testcase)
