import asyncio
from pathlib import Path
from typing import IO, Any


class UploadFile:
    def __init__(self, filename: str, content_type: str, file_path: str) -> None:
        self.filename = filename
        self.content_type = content_type
        self.path = Path(file_path)
        self.size = self.path.stat().st_size if self.path.exists() else 0

    async def read(self) -> bytes:
        return await asyncio.to_thread(self.path.read_bytes)

    def read_sync(self) -> bytes:
        return self.path.read_bytes()

    def open(self, mode: str = "rb") -> IO[Any]:
        return self.path.open(mode)

    def __repr__(self) -> str:
        return f"UploadFile(filename={self.filename!r}, size={self.size})"
