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


async def judge_code(
    code: str,
    language: Language
) -> SubmissionResult:
    submission = Submission(
        sid=1,
        timeLimit=1000,
        memoryLimit=32768,
        testcases=testcases,
        language=language,
        code=code
    )

    async with SandboxClient(endpoint) as client:
        async with DefaultChecker(client) as checker:
            judger = Judger(client, submission, checker)
            result = await judger.get_result()
    return result


@pytest.mark.asyncio
async def test_language_c():

    result = await judge_code(r"""
#include <stdio.h>
int main()
{
    int a,b;
    while(scanf("%d %d",&a, &b) != EOF)
        printf("%d\n",a+b);
    return 0;
}
""", Language.C)

    assert result.judge == JudgeStatus.Accepted
    for testcase in result.testcases:
        assert testcase.judge == JudgeStatus.Accepted


@pytest.mark.asyncio
async def test_language_cpp():

    result = await judge_code(r"""
#include <iostream>
using namespace std;
int main()
{
    int a,b;
    while(cin >> a >> b)
        cout << a+b << endl;
}
""", Language.CPP)

    assert result.judge == JudgeStatus.Accepted
    for testcase in result.testcases:
        assert testcase.judge == JudgeStatus.Accepted


@pytest.mark.asyncio
async def test_language_java():

    result = await judge_code(r"""
import java.util.Scanner;
public class Main {
	public static void main(String[] args) {
		Scanner in = new Scanner(System.in);
		while (in.hasNextInt()) {
			int a = in.nextInt();
			int b = in.nextInt();
			System.out.println(a + b);
		}
	}
}
""", Language.Java)


@pytest.mark.asyncio
async def test_language_python():

    result = await judge_code(r"""
import sys
for line in sys.stdin:
    a, b = map(int, line.split())
    print(a + b)
""", Language.Python)

    assert result.judge == JudgeStatus.Accepted
    for testcase in result.testcases:
        assert testcase.judge == JudgeStatus.Accepted


@pytest.mark.asyncio
async def test_time_limit_exceeded():

    result = await judge_code(
        "while True:\n\tpass",
        Language.Python
    )
    assert result.judge == JudgeStatus.TimeLimitExceeded
    assert result.testcases[0].judge == JudgeStatus.TimeLimitExceeded
    for testcase in result.testcases[1:]:
        assert testcase.judge == JudgeStatus.Skipped


@pytest.mark.asyncio
async def test_runtime_error():

    result = await judge_code(
        "print(1/0)",
        Language.Python
    )
    assert result.judge == JudgeStatus.RuntimeError
    for testcase in result.testcases:
        assert testcase.judge == JudgeStatus.RuntimeError


@pytest.mark.asyncio
async def test_compile_error():

    result = await judge_code(
        "int main() { return 0; }",
        Language.Python
    )
    assert result.judge == JudgeStatus.CompileError
    assert len(result.testcases) == 0
    assert "SyntaxError" in result.error
