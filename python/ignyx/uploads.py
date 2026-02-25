class UploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data
        self.size = len(data)

    async def read(self) -> bytes:
        return self._data

    def read_sync(self) -> bytes:
        return self._data

    def __repr__(self):
        return f"UploadFile(filename={self.filename!r}, size={self.size})"
