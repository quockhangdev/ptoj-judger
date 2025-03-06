import aiohttp
import logging
from aiohttp import FormData
from dataclasses import asdict
from typing import Optional, List, Dict, Any

from .config import LOGGER_NAME
from .models import SandboxCmd, SandboxResult, PreparedFile

logger = logging.getLogger(f"{LOGGER_NAME}.client")


class SandboxClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint.strip('/')
        self.session = aiohttp.ClientSession()
        logger.debug("Sandbox client initialized with: %s", self.endpoint)

    def __repr__(self) -> str:
        return f"SandboxClient(endpoint='{self.endpoint}')"

    async def __aenter__(self) -> 'SandboxClient':
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self.session.close()
        logger.debug("Sandbox client closed")

    async def run_command(
        self, commands: List[SandboxCmd]
    ) -> List[SandboxResult]:
        url = f'{self.endpoint}/run'
        payload = {"cmd": [asdict(c) for c in commands]}
        logger.debug("Sending run command: %s", payload)

        async with self.session.post(url, json=payload) as resp:
            resp.raise_for_status()
            results = await resp.json()
            logger.debug("Received run results: %s", results)
            return [SandboxResult(**result) for result in results]

    async def upload_file(self, content: str) -> PreparedFile:
        url = f'{self.endpoint}/file'
        data = FormData()
        data.add_field('file', content, filename='file.txt')
        logger.debug("Uploading file with %d bytes", len(content))

        async with self.session.post(url, data=data) as resp:
            resp.raise_for_status()
            result = await resp.json()
            logger.debug("Received upload results: '%s'", result)
            return PreparedFile(result)

    async def download_file(self, file_id: str) -> Optional[str]:
        url = f'{self.endpoint}/file/{file_id}'
        logger.debug("Downloading file: '%s'", file_id)

        async with self.session.get(url) as resp:
            result = await resp.text()
            if resp.status == 200:
                logger.debug(
                    "Received file '%s' with %d bytes",
                    file_id, len(result)
                )
                return result
            else:
                logger.warning(
                    "Failed to download file '%s': %d %s",
                    file_id, resp.status, await resp.text()
                )
                return None

    async def delete_file(self, file_id: str) -> bool:
        url = f'{self.endpoint}/file/{file_id}'
        logger.debug("Deleting file '%s'", file_id)

        async with self.session.delete(url) as resp:
            if resp.status == 200:
                logger.debug("File '%s' deleted", file_id)
                return True
            else:
                logger.warning(
                    "Failed to delete file '%s': %d %s",
                    file_id, resp.status, await resp.text()
                )
                return False

    async def get_version(self) -> Dict[str, Any]:
        url = f'{self.endpoint}/version'
        logger.debug("Getting version")

        async with self.session.get(url) as resp:
            result = await resp.json()
            logger.debug("Received version: %s", result)
            return result
