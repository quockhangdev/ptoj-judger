import pytest
from judger import *

endpoint = 'http://localhost:5050'


@pytest.mark.asyncio
async def test_empty_testcases():
    submission = Submission(
        sid=1,
        timeLimit=1000,
        memoryLimit=32768,
        testcases=[],
        language=Language.Python,
        code='print("Hello, World!")'
    )

    async with SandboxClient(endpoint) as client:
        async with DefaultChecker(client) as checker:
            judger = Judger(client, submission, checker)
            result = await judger.get_result()
    assert result.judge == JudgeStatus.SystemError
    assert len(result.testcases) == 0
