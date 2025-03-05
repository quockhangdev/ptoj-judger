import asyncio
from rich import print

from judger import *


async def main():
    endpoint = 'http://localhost:5050'

    testcases = [
        Testcase(input=MemoryFile("1 1\n"),
                 output=MemoryFile("2\n")),
        Testcase(input=MemoryFile("1 -1\n"),
                 output=MemoryFile("0\n")),
        Testcase(input=MemoryFile("0 0\n"),
                 output=MemoryFile("0\n"))]
    code = r"""
#include <stdio.h>
int main()
{
    int a,b;
    while(scanf("%d %d",&a, &b) != EOF)
        printf("%d\n",a+b);
    return 0;
}
"""
    submission = Submission(
        timeLimit=1000, memoryLimit=32768, testcases=testcases,
        language=Language.C, code=code)
    print(submission)

    async with SandboxClient(endpoint) as client:
        judger = Judger(client, submission)
        result = await judger.run()
        print(result)

if __name__ == '__main__':
    asyncio.run(main())
