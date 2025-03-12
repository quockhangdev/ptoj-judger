import pytest
from judger import *

endpoint = 'http://localhost:5050'

file_content = \
    "In the intricate dance of algorithms and the language of programming, " + \
    "the undefined variable is a transient anomaly waiting to be tamed. As " + \
    "programmers navigate the complexities of their craft, the quest for a " + \
    "well-defined codebase becomes a journey of discovery, where each " + \
    "undefined variable is a stepping stone toward mastery in the " + \
    "ever-evolving world of software development."


@pytest.mark.asyncio
async def test_client_repr():
    async with SandboxClient(endpoint) as client:
        assert endpoint in repr(client)


@pytest.mark.asyncio
async def test_get_version():
    async with SandboxClient(endpoint) as client:
        version = await client.get_version()
        assert isinstance(version, dict)
        assert 'buildVersion' in version


@pytest.mark.asyncio
async def test_file_manage():
    async with SandboxClient(endpoint) as client:

        file = await client.upload_file(file_content)
        assert isinstance(file, PreparedFile)

        file_id = file.fileId
        assert isinstance(file_id, str)

        downloaded = await client.download_file(file_id)
        assert isinstance(downloaded, str)
        assert downloaded == file_content

        assert await client.delete_file(file_id)


@pytest.mark.asyncio
async def test_download_nonexistent_file():
    async with SandboxClient(endpoint) as client:
        assert await client.download_file("nonexistent") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_file():
    async with SandboxClient(endpoint) as client:
        assert not await client.delete_file("nonexistent")
