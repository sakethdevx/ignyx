import os
import mimetypes
from ignyx.responses import FileResponse
from ignyx.exceptions import HTTPException

class StaticFiles:
    def __init__(self, directory: str, html: bool = False):
        self.directory = os.path.abspath(directory)
        self.html = html

    def __call__(self, path: str = ""):
        full_path = os.path.normpath(os.path.join(self.directory, path.lstrip("/")))
        
        if not full_path.startswith(self.directory) or ".." in path:
            raise HTTPException(403, "Forbidden")
            
        if os.path.isdir(full_path) and self.html:
            full_path = os.path.join(full_path, "index.html")
            
        if not os.path.exists(full_path):
            raise HTTPException(404, "File not found")
            
        return FileResponse(full_path)
