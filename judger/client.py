import aiohttp
from aiohttp import FormData
from dataclasses import asdict
from typing import Optional, List, Dict, Any

from .models import SandboxCmd, SandboxResult, PreparedFile


class SandboxClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint.strip('/')
        self.session = aiohttp.ClientSession()

    async def __aenter__(self) -> 'SandboxClient':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self.session.close()

    async def run_command(
        self,
        commands: List[SandboxCmd]
    ) -> List[SandboxResult]:
        url = f'{self.endpoint}/run'
        payload = {"cmd": [asdict(c) for c in commands]}
        async with self.session.post(url, json=payload) as resp:
            return [SandboxResult(**result) for result in await resp.json()]

    async def upload_file(self, content: str) -> PreparedFile:
        url = f'{self.endpoint}/file'
        data = FormData()
        data.add_field('file', content, filename='file.txt')
        async with self.session.post(url, data=data) as resp:
            return PreparedFile(await resp.json())

    async def download_file(self, file_id: str) -> Optional[str]:
        url = f'{self.endpoint}/file/{file_id}'
        async with self.session.get(url) as resp:
            return await resp.text() if resp.status == 200 else None

    async def delete_file(self, file_id: str) -> bool:
        url = f'{self.endpoint}/file/{file_id}'
        async with self.session.delete(url) as resp:
            return resp.status == 200

    async def get_version(self) -> Dict[str, Any]:
        url = f'{self.endpoint}/version'
        async with self.session.get(url) as resp:
            return await resp.json()
