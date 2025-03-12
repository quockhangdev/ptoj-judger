import pytest
from judger import *

endpoint = 'http://localhost:5050'

testcases = [
    Testcase(
        uuid='fdc3a68e-21d2-4ec1-baf6-36611f45f685',
        input=MemoryFile("1 1\n"),
        output=MemoryFile("2\n")
    ),
    Testcase(
        uuid='f34bbc92-1461-422e-8f61-26e6790a36a8',
        input=MemoryFile("1 -1\n"),
        output=MemoryFile("0\n")
    ),
    Testcase(
        uuid='ae005ba0-8c29-446d-82c0-219fef264fba',
        input=MemoryFile("0 0\n"),
        output=MemoryFile("0\n")
    )
]


async def judge_code(code: str) -> SubmissionResult:
    submission = Submission(
        sid=1,
        timeLimit=1000,
        memoryLimit=32768,
        testcases=testcases,
        language=Language.C,
        code=code
    )

    async with SandboxClient(endpoint) as client:
        async with DefaultChecker(client) as checker:
            judger = Judger(client, submission, checker)
            result = await judger.get_result()
    return result


@pytest.mark.asyncio
async def test_accept():

    code = r"""
#include <stdio.h>
int main()
{
    int a,b;
    while(scanf("%d %d",&a, &b) != EOF)
        printf("%d\n", a+b);
    return 0;
}
"""
    result = await judge_code(code)

    assert result.judge == JudgeStatus.Accepted
    for testcase in result.testcases:
        assert testcase.judge == JudgeStatus.Accepted
