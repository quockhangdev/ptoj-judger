import asyncio
import logging
from uuid import uuid4
from rich import print
from rich.logging import RichHandler
from rich.traceback import install as install_traceback

from judger import *


def setup_logger():
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)

    console_handler = RichHandler(
        log_time_format="[%X.%f]",
        rich_tracebacks=True)
    logger.addHandler(console_handler)


async def main():
    install_traceback()
    setup_logger()

    endpoint = 'http://localhost:5050'

    testcases = [
        Testcase(
            uuid=str(uuid4()),
            input=MemoryFile("1 1\n"),
            output=MemoryFile("2\n")
        ),
        Testcase(
            uuid=str(uuid4()),
            input=MemoryFile("1 -1\n"),
            output=MemoryFile("0\n")
        ),
        Testcase(
            uuid=str(uuid4()),
            input=MemoryFile("0 0\n"),
            output=MemoryFile("0\n")
        )
    ]
    code = r"""
#include <stdio.h>
int main()
{
    int a,b;
    while(scanf("%d %d",&a, &b) != EOF)
        printf("%d\n",(a+b)*2);
    return 0;
}
"""
    submission = Submission(
        sid=1,
        timeLimit=1000,
        memoryLimit=32768,
        testcases=testcases,
        language=Language.C,
        code=code
    )
    print(submission)

    async with SandboxClient(endpoint) as client:
        judger = Judger(client, submission)
        result = await judger.get_result()
        print(result)

if __name__ == '__main__':
    asyncio.run(main())
